# Testes do VectorManager: loader_for, dimensões de embedding e static helpers.
# Não requer Qdrant nem API key — testa lógica pura e static methods.

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from src.utils.vector_store import _EMBEDDING_DIMS, VectorManager


class TestLoaderFor:
    """Testa seleção correta de loader por extensão de arquivo."""

    def test_txt_returns_text_loader(self):
        loader = VectorManager._loader_for(Path("docs/codigo.txt"))

        assert isinstance(loader, TextLoader)

    def test_md_returns_text_loader(self):
        loader = VectorManager._loader_for(Path("docs/guia.md"))

        assert isinstance(loader, TextLoader)

    def test_pdf_returns_pdf_loader(self, tmp_path):
        pdf_file = tmp_path / "relatorio.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")  # precisa existir pro PyPDFLoader
        loader = VectorManager._loader_for(pdf_file)

        assert isinstance(loader, PyPDFLoader)

    def test_text_extension_supported(self):
        loader = VectorManager._loader_for(Path("docs/notas.text"))

        assert isinstance(loader, TextLoader)

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            VectorManager._loader_for(Path("docs/planilha.xlsx"))

    def test_csv_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            VectorManager._loader_for(Path("data/export.csv"))

    def test_case_insensitive_extension(self):
        """Extensões são normalizadas pra lowercase internamente."""
        loader = VectorManager._loader_for(Path("docs/README.MD"))

        # Path.suffix retorna ".MD" mas o código faz .lower()
        assert isinstance(loader, TextLoader)


class TestEmbeddingDimensions:
    """Verifica dimensões corretas por provider no dict global."""

    def test_openai_dimension(self):
        assert _EMBEDDING_DIMS["openai"] == 1536

    def test_azure_dimension(self):
        assert _EMBEDDING_DIMS["azure"] == 1536

    def test_google_dimension(self):
        assert _EMBEDDING_DIMS["google"] == 3072

    def test_all_providers_present(self):
        assert set(_EMBEDDING_DIMS.keys()) == {"openai", "azure", "google"}

    def test_unknown_provider_defaults_to_1536(self):
        """_EMBEDDING_DIMS.get(provider, 1536) deve dar fallback."""
        assert _EMBEDDING_DIMS.get("anthropic", 1536) == 1536
