# Gerenciador do Qdrant: ingestão, chunking, embedding e busca.
# Cada chunk armazena metadados de lineage (arquivo, página, timestamp).

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.config import (
    AZURE_DEPLOYMENT_EMBEDDING,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    GEMINI_EMBEDDING_MODEL,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    QDRANT_PORT,
    TOP_K_RESULTS,
)

logger = logging.getLogger("abi_assistant.vector_store")

# dimensão varia por provider (OpenAI/Azure=1536, Google=3072)
_EMBEDDING_DIMS: dict[str, int] = {
    "openai": 1536,
    "azure": 1536,
    "google": 3072,
}


class VectorManager:
    """Gestão de ingestão, embedding e busca semântica via Qdrant.

    Cada chunk armazena metadados de lineage (arquivo, página, timestamp, hash).
    Suporta três providers de embedding: OpenAI, Azure e Google.
    """

    def __init__(self) -> None:
        self._client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        provider = LLM_PROVIDER.lower()
        self._embedding_dim = _EMBEDDING_DIMS.get(provider, 1536)

        if provider == "azure":
            self._embeddings = AzureOpenAIEmbeddings(
                azure_deployment=AZURE_DEPLOYMENT_EMBEDDING,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
            )
        elif provider == "google":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=GEMINI_EMBEDDING_MODEL,
                google_api_key=GOOGLE_API_KEY,
            )
        else:
            self._embeddings = OpenAIEmbeddings(
                model=EMBEDDING_MODEL,
                api_key=OPENAI_API_KEY,
            )

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._ensure_collection()
        logger.info(
            "VectorManager ready – Qdrant=%s:%s  collection=%s",
            QDRANT_HOST,
            QDRANT_PORT,
            QDRANT_COLLECTION,
        )

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if QDRANT_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=self._embedding_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'.", QDRANT_COLLECTION)
        else:
            logger.info("Qdrant collection '%s' already exists.", QDRANT_COLLECTION)

    @staticmethod
    def _loader_for(path: Path):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return PyPDFLoader(str(path))
        if suffix == ".md":
            return TextLoader(str(path), encoding="utf-8")
        if suffix in {".txt", ".text"}:
            return TextLoader(str(path), encoding="utf-8")
        raise ValueError(f"Unsupported file type: {suffix}")

    def ingest_file(self, path: Path) -> int:
        """Carrega, chunkeia, embeda e armazena um arquivo no Qdrant."""
        logger.info("Ingesting '%s'…", path.name)
        loader = self._loader_for(path)
        raw_docs = loader.load()

        chunks = self._splitter.split_documents(raw_docs)
        if not chunks:
            logger.warning("No chunks produced from '%s'.", path.name)
            return 0

        texts = [c.page_content for c in chunks]
        vectors = self._embeddings.embed_documents(texts)

        points: list[PointStruct] = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            # metadados de lineage
            metadata: dict[str, Any] = {
                "source_file": path.name,
                "file_path": str(path),
                "page": chunk.metadata.get("page", None),
                "chunk_index": idx,
                "chunk_total": len(chunks),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": hashlib.md5(chunk.page_content.encode()).hexdigest(),
            }

            # ID determinístico via MD5 (não usa hash() do Python, que é randomizado)
            raw_id = f"{path.name}:{idx}:{metadata['content_hash']}"
            point_id = int(hashlib.md5(raw_id.encode()).hexdigest(), 16) % (2**63)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={**metadata, "text": chunk.page_content},
                )
            )

        self._client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        logger.info("Stored %d chunks from '%s' (lineage tracked).", len(points), path.name)
        return len(points)

    def ingest_directory(self, directory: Path) -> int:
        """Ingere todos os arquivos suportados de um diretório.

        Continua em caso de falha individual (loga warning).
        """
        total = 0
        supported = {".pdf", ".md", ".txt", ".text"}
        files = sorted(f for f in directory.iterdir() if f.suffix.lower() in supported)
        if not files:
            logger.warning("No supported files found in '%s'.", directory)
            return 0

        failed: list[str] = []
        for file_path in files:
            try:
                total += self.ingest_file(file_path)
            except Exception:
                logger.exception("Failed to ingest '%s' – skipping.", file_path.name)
                failed.append(file_path.name)

        if failed:
            logger.warning(
                "Ingestion finished with %d error(s): %s",
                len(failed),
                ", ".join(failed),
            )
        logger.info(
            "Directory ingestion complete – %d total chunks from %d/%d files.",
            total,
            len(files) - len(failed),
            len(files),
        )
        return total

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Busca semântica no Qdrant. Retorna top-k resultados com dedup por hash."""
        k = top_k or TOP_K_RESULTS
        query_vector = self._embeddings.embed_query(query)

        # busca com margem extra pra compensar dedup
        hits = self._client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=k * 3,
            with_payload=True,
        ).points

        results: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        for hit in hits:
            payload = hit.payload or {}
            # dedup por content_hash (evita duplicatas de re-ingestão)
            content_hash = payload.get("content_hash", "")
            if content_hash and content_hash in seen_hashes:
                continue
            if content_hash:
                seen_hashes.add(content_hash)
            results.append(
                {
                    "content": payload.get("text", ""),
                    "source": payload.get("source_file", "unknown"),
                    "page": payload.get("page"),
                    "score": hit.score,
                }
            )
            if len(results) >= k:
                break

        logger.info(
            "Search for '%s' returned %d results (top score=%.3f).",
            query[:60],
            len(results),
            results[0]["score"] if results else 0.0,
        )
        return results
