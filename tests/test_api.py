# Testes da API REST (TestClient, tudo mockado).

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture(autouse=True)
def _mock_pipeline():
    mock_result = {
        "answer": "A política de sustentabilidade foca em redução de carbono.",
        "compliance_approved": True,
        "compliance_reason": "Pergunta permitida.",
        "validation_passed": True,
        "validation_notes": "Resposta validada.",
        "sources_cited": ["politica.md"],
        "steps_taken": [
            "compliance_check",
            "router",
            "rag_retrieval",
            "rag_generation",
            "validator",
        ],
    }

    mock_graph = MagicMock()
    mock_graph.invoke = MagicMock(return_value=mock_result)

    with (
        patch("src.api._graph", mock_graph),
        patch("src.api._factory", MagicMock()),
        patch("src.api._vectors", MagicMock()),
    ):
        yield mock_graph


@pytest.fixture()
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client: TestClient):
        resp = client.get("/api/v1/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "abi-smart-assistant"


class TestChatEndpoint:
    def test_chat_returns_answer(self, client: TestClient):
        resp = client.post(
            "/api/v1/chat",
            json={"question": "Qual é a política de sustentabilidade?"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "sustentabilidade" in data["answer"].lower()
        assert data["compliance_approved"] is True
        assert data["thread_id"]  # deve ter UUID
        assert len(data["steps_taken"]) > 0

    def test_chat_with_thread_id(self, client: TestClient):
        resp = client.post(
            "/api/v1/chat",
            json={
                "question": "Me conta mais sobre isso",
                "thread_id": "abc-123",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["thread_id"] == "abc-123"

    def test_chat_rejects_empty_question(self, client: TestClient):
        resp = client.post("/api/v1/chat", json={"question": ""})

        assert resp.status_code == 422  # validação Pydantic

    def test_chat_rejects_missing_body(self, client: TestClient):
        resp = client.post("/api/v1/chat")

        assert resp.status_code == 422


class TestMetricsEndpoint:
    def test_metrics_returns_json(self, client: TestClient):
        resp = client.get("/api/v1/metrics")

        assert resp.status_code == 200
        data = resp.json()
        # metrics retorna dict com as chaves do LLMFactory
        assert isinstance(data, dict)

    def test_observability_headers_present(self, client: TestClient):
        resp = client.get("/api/v1/health")

        assert "X-Request-Id" in resp.headers
        assert "X-Request-Duration-Ms" in resp.headers
