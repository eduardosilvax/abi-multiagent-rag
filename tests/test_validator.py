# Testes do Validator (anti-alucinação).

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.validator import ValidatorAgent


@pytest.fixture()
def mock_factory():
    factory = MagicMock()
    factory.invoke_structured = MagicMock(
        return_value={
            "grounded": True,
            "confidence": 0.95,
            "issues": [],
            "suggestion": "",
        }
    )
    return factory


@pytest.fixture()
def agent(mock_factory):
    return ValidatorAgent(mock_factory)


class TestValidatorSkipsDirect:
    def test_skips_when_no_docs(self, agent):
        state = {
            "question": "Bom dia!",
            "answer": "Olá, como posso ajudar?",
            "documents": [],
            "steps_taken": [],
        }

        result = agent.run(state)

        assert result["validation_passed"] is True
        assert "validator_skipped" in result["steps_taken"]
        # resposta deve permanecer intacta
        assert result["answer"] == "Olá, como posso ajudar?"


class TestValidatorPasses:
    def test_grounded_answer_passes(self, agent):
        state = {
            "question": "Qual a meta de carbono?",
            "answer": "A meta é reduzir 25% até 2025.",
            "documents": [{"content": "A meta é reduzir 25% até 2025.", "source": "politica.md"}],
            "steps_taken": ["rag_retrieval", "rag_generation"],
        }

        result = agent.run(state)

        assert result["validation_passed"] is True
        assert "validator" in result["steps_taken"]
        # resposta deve permanecer intacta
        assert result["answer"] == "A meta é reduzir 25% até 2025."


class TestValidatorRejection:
    def test_hallucinated_answer_replaced(self, agent, mock_factory):
        mock_factory.invoke_structured.return_value = {
            "grounded": False,
            "confidence": 0.2,
            "issues": ["Dados de receita não aparecem no contexto."],
            "suggestion": "Os documentos não contêm informações sobre receita.",
        }

        state = {
            "question": "Qual a receita anual?",
            "answer": "A receita é de R$ 50 bilhões.",
            "documents": [{"content": "Política de sustentabilidade.", "source": "politica.md"}],
            "steps_taken": ["rag_retrieval", "rag_generation"],
            "sources_cited": ["politica.md"],
        }

        result = agent.run(state)

        assert result["validation_passed"] is False
        assert "Dados de receita" in result["validation_notes"]
        # resposta deve ser a versão corrigida, não a alucinada
        assert "receita" in result["answer"].lower()

    def test_low_confidence_without_suggestion(self, agent, mock_factory):
        """Se grounded mas confiança baixa, deve falhar mesmo assim."""
        mock_factory.invoke_structured.return_value = {
            "grounded": True,
            "confidence": 0.3,
            "issues": ["Resposta parcialmente fundamentada."],
            "suggestion": "",
        }

        state = {
            "question": "Qual o prazo?",
            "answer": "O prazo é amanhã.",
            "documents": [{"content": "O prazo depende da aprovação.", "source": "guia.md"}],
            "steps_taken": [],
        }

        result = agent.run(state)

        assert result["validation_passed"] is False
