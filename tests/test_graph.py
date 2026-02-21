# Testes do grafo LangGraph: funções de gate e routing.
# Testa _compliance_gate e _rag_or_direct isoladamente (funções puras).

from __future__ import annotations

from langgraph.graph import END

from src.core.graph import _compliance_gate, _rag_or_direct


class TestComplianceGate:
    """Testa bifurcação pós-compliance."""

    def test_approved_routes_to_router(self):
        state = {"compliance_approved": True}

        assert _compliance_gate(state) == "router"

    def test_blocked_routes_to_end(self):
        state = {"compliance_approved": False}

        assert _compliance_gate(state) == END

    def test_missing_key_defaults_to_end(self):
        """Se compliance_approved não existir, assume bloqueio (seguro)."""
        state = {}

        assert _compliance_gate(state) == END


class TestRagOrDirect:
    """Testa routing pós-router (RAG vs DirectAnswer vs Clarify)."""

    def test_needs_rag_routes_to_rag(self):
        state = {"needs_rag": True, "route": "rag"}

        assert _rag_or_direct(state) == "rag_agent"

    def test_direct_routes_to_direct_answer(self):
        state = {"needs_rag": False, "route": "direct"}

        assert _rag_or_direct(state) == "direct_answer"

    def test_clarify_routes_to_clarify(self):
        state = {"route": "clarify", "needs_rag": False}

        assert _rag_or_direct(state) == "clarify"

    def test_clarify_takes_priority_over_needs_rag(self):
        """Se route=clarify, vai pra clarify mesmo com needs_rag=True."""
        state = {"route": "clarify", "needs_rag": True}

        assert _rag_or_direct(state) == "clarify"

    def test_default_needs_rag_true_routes_to_rag(self):
        """Se needs_rag não estiver setado, default é True → rag_agent."""
        state = {"route": ""}

        assert _rag_or_direct(state) == "rag_agent"

    def test_empty_route_with_needs_rag_false(self):
        state = {"route": "", "needs_rag": False}

        assert _rag_or_direct(state) == "direct_answer"
