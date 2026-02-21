# Agente RAG: busca documentos no Qdrant e gera resposta citando fontes.

from __future__ import annotations

import logging
from typing import Any

from src.core.llm_factory import LLMFactory
from src.schemas.state import AssistantState
from src.utils.vector_store import VectorManager

logger = logging.getLogger("abi_assistant.rag_agent")

_RAG_PROMPT_TEMPLATE = """\
Você é o Assistente Inteligente da AB InBev.  Responda à pergunta do usuário
usando EXCLUSIVAMENTE o contexto fornecido abaixo.

## Regras obrigatórias:
1. NUNCA invente informações.  Se o contexto for insuficiente, diga:
   "Não encontrei informações suficientes nos documentos internos para responder."
2. NÃO cite fontes nem nomes de arquivos na resposta — as fontes são exibidas
   automaticamente pela interface.
3. Seja claro, objetivo e em português corporativo.
4. Quando múltiplos documentos concordam, sintetize em uma resposta coesa.
5. Se houver conflito entre fontes, aponte as divergências.

## Contexto dos Documentos Internos:
{context}

## Pergunta do Usuário:
{question}

## Resposta:
"""


class RAGAgent:
    """Busca no Qdrant e gera resposta fundamentada nos documentos.

    Faz retrieval bilíngue (PT + EN) pra achar docs independente do idioma da query.
    """

    def __init__(
        self,
        llm_factory: LLMFactory,
        vector_manager: VectorManager,
    ) -> None:
        self._llm = llm_factory
        self._vector = vector_manager

    def _translate_query(self, question: str) -> str | None:
        """Traduz a pergunta pra inglês (busca cross-language)."""
        prompt = (
            f"Translate the following question to English. Return ONLY the translated text, nothing else.\n\n{question}"
        )
        try:
            return self._llm.invoke_with_fallback(prompt, use_cache=True).strip()
        except Exception:
            logger.warning("Failed to translate query for cross-language search.")
            return None

    def _multilingual_search(self, question: str) -> list[dict[str, Any]]:
        """Busca PT + EN, merge por melhor score, dedup por prefixo do conteúdo."""
        # busca primária (idioma original)
        docs_primary = self._vector.search(question)

        # traduz e busca em inglês
        en_query = self._translate_query(question)
        if en_query and en_query.lower().strip() != question.lower().strip():
            logger.info("Cross-language search: '%s'", en_query[:80])
            docs_en = self._vector.search(en_query)
        else:
            docs_en = []

        # merge: mantém melhor score por chunk
        seen_content: dict[str, dict[str, Any]] = {}
        for doc in docs_primary + docs_en:
            key = doc["content"][:200]  # primeiros 200 chars como chave de dedup
            if key not in seen_content or doc["score"] > seen_content[key]["score"]:
                seen_content[key] = doc

        merged = sorted(seen_content.values(), key=lambda d: d["score"], reverse=True)
        return merged

    def _build_context(self, docs: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("source", "desconhecido")
            page = doc.get("page")
            score = doc.get("score", 0.0)
            page_info = f", página {page}" if page is not None else ""
            parts.append(f"[Documento {i}] (fonte: {source}{page_info} | relevância: {score:.2f})\n{doc['content']}")
        return "\n\n---\n\n".join(parts)

    def _extract_sources(self, docs: list[dict[str, Any]]) -> list[str]:
        """Nomes de arquivo-fonte sem duplicatas."""
        seen: set[str] = set()
        citations: list[str] = []
        for doc in docs:
            source = doc.get("source", "desconhecido")
            if source not in seen:
                seen.add(source)
                citations.append(source)
        return citations

    def run(self, state: AssistantState) -> AssistantState:
        """Nó LangGraph: retrieval → contexto → geração → citação de fontes."""
        question = state.get("question", "")
        steps = list(state.get("steps_taken", []))
        steps.append("rag_retrieval")

        # 1. retrieval bilíngue (PT + EN)
        logger.info("RAG search for: '%s'", question[:80])
        docs = self._multilingual_search(question)

        if not docs:
            logger.warning("No documents found for query.")
            return {
                **state,
                "documents": [],
                "answer": ("Não encontrei informações nos documentos internos para responder à sua pergunta."),
                "sources_cited": [],
                "steps_taken": steps,
            }

        # 2. monta contexto e prompt
        context = self._build_context(docs)
        prompt = _RAG_PROMPT_TEMPLATE.format(context=context, question=question)

        # 3. gera resposta (tier barato primeiro)
        steps.append("rag_generation")
        logger.info("Generating RAG answer…")
        answer = self._llm.invoke_with_fallback(prompt)

        # 4. anexa citações (estruturadas, a UI exibe)
        citations = self._extract_sources(docs)

        return {
            **state,
            "documents": docs,
            "answer": answer,
            "sources_cited": citations,
            "steps_taken": steps,
        }
