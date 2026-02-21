# Testes do schema de estado.

from __future__ import annotations

from src.schemas.state import AssistantState, Document


class TestDocumentSchema:
    def test_creates_document(self):
        doc: Document = {
            "content": "Algo importante.",
            "source": "politica.md",
            "page": 1,
            "score": 0.92,
        }

        assert doc["content"] == "Algo importante."
        assert doc["score"] == 0.92

    def test_document_optional_fields(self):
        """page é opcional (total=False)."""
        doc: Document = {"content": "Texto", "source": "guia.md", "score": 0.5}

        assert "page" not in doc


class TestAssistantState:
    def test_full_state(self):
        state: AssistantState = {
            "question": "Qual a política?",
            "compliance_approved": True,
            "compliance_reason": "OK",
            "needs_rag": True,
            "documents": [],
            "answer": "Resposta aqui.",
            "steps_taken": ["compliance_check", "router", "rag_retrieval"],
            "sources_cited": ["politica.md"],
            "validation_passed": True,
            "validation_notes": "",
        }

        assert state["compliance_approved"] is True
        assert state["validation_passed"] is True
        assert len(state["steps_taken"]) == 3

    def test_partial_state(self):
        """TypedDict(total=False) permite criação parcial."""
        state: AssistantState = {"question": "Oi"}

        assert state["question"] == "Oi"
