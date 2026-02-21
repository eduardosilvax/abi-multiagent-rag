# Testes do RAGAgent: build_context, extract_sources e run (tudo mockado).

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.rag_agent import RAGAgent


@pytest.fixture()
def mock_factory():
    factory = MagicMock()
    factory.invoke_with_fallback = MagicMock(return_value="A meta é reduzir 25% até 2025.")
    return factory


@pytest.fixture()
def mock_vector_manager():
    vm = MagicMock()
    vm.search = MagicMock(
        return_value=[
            {
                "content": "A meta é reduzir 25% as emissões até 2025.",
                "source": "Politica_Sustentabilidade.md",
                "page": 1,
                "score": 0.89,
            },
            {
                "content": "Nosso programa de energia renovável cobre 78% das operações.",
                "source": "Politica_Sustentabilidade.md",
                "page": 2,
                "score": 0.74,
            },
        ]
    )
    return vm


@pytest.fixture()
def agent(mock_factory, mock_vector_manager):
    return RAGAgent(mock_factory, mock_vector_manager)


class TestRAGBuildContext:
    def test_builds_context_with_multiple_docs(self, agent):
        docs = [
            {"content": "Texto A", "source": "doc1.md", "page": 1, "score": 0.9},
            {"content": "Texto B", "source": "doc2.txt", "page": None, "score": 0.7},
        ]

        ctx = agent._build_context(docs)

        assert "Documento 1" in ctx
        assert "Documento 2" in ctx
        assert "doc1.md" in ctx
        assert "Texto A" in ctx
        assert "Texto B" in ctx
        # Docs are separated
        assert "---" in ctx

    def test_single_doc_no_separator(self, agent):
        docs = [{"content": "Único", "source": "a.txt", "page": None, "score": 0.5}]

        ctx = agent._build_context(docs)

        assert "Único" in ctx
        assert ctx.count("---") == 0

    def test_empty_docs_returns_empty(self, agent):
        ctx = agent._build_context([])

        assert ctx == ""


class TestRAGExtractSources:
    def test_deduplicates_by_source_file(self, agent):
        docs = [
            {"content": "A", "source": "politica.md", "page": 1, "score": 0.9},
            {"content": "B", "source": "politica.md", "page": 1, "score": 0.8},
            {"content": "C", "source": "politica.md", "page": 2, "score": 0.7},
        ]

        citations = agent._extract_sources(docs)

        # Same source file → single citation (file-level dedup)
        assert len(citations) == 1
        assert citations[0] == "politica.md"

    def test_returns_source_filename(self, agent):
        docs = [{"content": "X", "source": "guia.md", "page": 3, "score": 0.8}]

        citations = agent._extract_sources(docs)

        assert len(citations) == 1
        assert citations[0] == "guia.md"

    def test_no_page_omits_page_info(self, agent):
        docs = [{"content": "X", "source": "readme.txt", "page": None, "score": 0.6}]

        citations = agent._extract_sources(docs)

        assert len(citations) == 1
        assert "página" not in citations[0]
        assert "readme.txt" in citations[0]


class TestRAGRun:
    def test_returns_answer_with_sources(self, agent, mock_vector_manager, mock_factory):
        state = {"question": "Qual a meta de carbono?", "steps_taken": []}

        result = agent.run(state)

        # busca vetorial foi chamada (cross-language: PT original + EN traduzido)
        assert mock_vector_manager.search.call_count >= 1
        # LLM chamada pra tradução + geração
        assert mock_factory.invoke_with_fallback.call_count >= 2
        # pelo menos uma chamada deve conter a pergunta no prompt
        prompts = [str(c) for c in mock_factory.invoke_with_fallback.call_args_list]
        assert any("Qual a meta de carbono?" in p for p in prompts)

        # estado do resultado
        assert result["answer"]
        assert len(result["documents"]) > 0
        assert len(result["sources_cited"]) > 0
        assert "rag_retrieval" in result["steps_taken"]
        assert "rag_generation" in result["steps_taken"]

    def test_no_docs_returns_fallback(self, mock_factory):
        empty_vector = MagicMock()
        empty_vector.search = MagicMock(return_value=[])
        agent = RAGAgent(mock_factory, empty_vector)

        state = {"question": "Algo inexistente?", "steps_taken": []}
        result = agent.run(state)

        assert "Não encontrei informações" in result["answer"]
        assert result["documents"] == []
        assert result["sources_cited"] == []
        # tradução roda, mas geração NÃO (sem docs)
        assert "rag_generation" not in result["steps_taken"]
        assert "rag_retrieval" in result["steps_taken"]

    def test_steps_tracked_correctly(self, agent):
        state = {"question": "Teste", "steps_taken": ["compliance_check", "router"]}

        result = agent.run(state)

        assert result["steps_taken"] == [
            "compliance_check",
            "router",
            "rag_retrieval",
            "rag_generation",
        ]

    def test_original_state_preserved(self, agent):
        """Campos de nós anteriores devem fluir pelo state."""
        state = {
            "question": "Teste",
            "steps_taken": [],
            "compliance_approved": True,
            "compliance_reason": "OK",
        }

        result = agent.run(state)

        assert result["compliance_approved"] is True
        assert result["compliance_reason"] == "OK"
