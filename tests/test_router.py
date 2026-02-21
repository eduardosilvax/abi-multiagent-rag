# Testes do Router, DirectAnswer e ClarifyAgent.

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.router import ClarifyAgent, DirectAnswerAgent, RouterAgent


@pytest.fixture()
def mock_factory():
    factory = MagicMock()
    factory.invoke_structured = MagicMock(
        return_value={"route": "rag", "reasoning": "Pergunta sobre política interna."}
    )
    factory.invoke_with_fallback = MagicMock(return_value="Olá! Como posso ajudar?")
    return factory


class TestRouterAgent:
    def test_routes_to_rag(self, mock_factory):
        agent = RouterAgent(mock_factory)
        state = {"question": "Qual a política de sustentabilidade?", "steps_taken": []}

        result = agent.run(state)

        assert result["needs_rag"] is True
        assert "router" in result["steps_taken"]

    def test_routes_to_direct(self, mock_factory):
        mock_factory.invoke_structured.return_value = {
            "route": "direct",
            "reasoning": "Saudação simples.",
        }
        agent = RouterAgent(mock_factory)
        state = {"question": "Bom dia!", "steps_taken": []}

        result = agent.run(state)

        assert result["needs_rag"] is False

    def test_defaults_to_rag_on_unknown(self, mock_factory):
        """Se a LLM retornar lixo, default é RAG (mais seguro)."""
        mock_factory.invoke_structured.return_value = {"route": "???", "reasoning": ""}
        agent = RouterAgent(mock_factory)
        state = {"question": "Teste", "steps_taken": []}

        result = agent.run(state)

        # rota desconhecida deve virar "rag"
        assert result["route"] == "rag"
        assert result["needs_rag"] is True

    def test_routes_to_clarify(self, mock_factory):
        """Perguntas ambíguas devem acionar a rota clarify."""
        mock_factory.invoke_structured.return_value = {
            "route": "clarify",
            "reasoning": "Pergunta vaga sem contexto.",
        }
        agent = RouterAgent(mock_factory)
        state = {"question": "Me fala daquilo", "steps_taken": []}

        result = agent.run(state)

        assert result["route"] == "clarify"
        assert result["needs_rag"] is False
        assert "router" in result["steps_taken"]


class TestDirectAnswerAgent:
    def test_produces_answer(self, mock_factory):
        agent = DirectAnswerAgent(mock_factory)
        state = {"question": "Bom dia!", "steps_taken": []}

        result = agent.run(state)

        assert result["answer"] == "Olá! Como posso ajudar?"
        assert result["documents"] == []
        assert "direct_answer" in result["steps_taken"]


class TestClarifyAgent:
    def test_produces_clarification(self, mock_factory):
        mock_factory.invoke_with_fallback.return_value = (
            "Poderia reformular sua pergunta? Posso ajudar com políticas, onboarding ou conduta."
        )
        agent = ClarifyAgent(mock_factory)
        state = {"question": "Me fala daquilo", "steps_taken": []}

        result = agent.run(state)

        assert "reformular" in result["answer"].lower() or "posso ajudar" in result["answer"].lower()
        assert result["documents"] == []
        assert "clarify" in result["steps_taken"]

    def test_clarify_does_not_invent_answer(self, mock_factory):
        """O agente clarify deve pedir reformulação, não responder a pergunta."""
        mock_factory.invoke_with_fallback.return_value = "Sua pergunta está um pouco vaga. Poderia dar mais detalhes?"
        agent = ClarifyAgent(mock_factory)
        state = {"question": "O que vocês acham?", "steps_taken": []}

        result = agent.run(state)

        assert result["sources_cited"] == []
        assert "clarify" in result["steps_taken"]
