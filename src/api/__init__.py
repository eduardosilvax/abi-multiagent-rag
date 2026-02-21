# API REST do assistente (FastAPI).
# POST /api/v1/chat, GET /api/v1/health, GET /api/v1/metrics

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import API_KEY
from src.core.graph import build_graph
from src.core.llm_factory import LLMFactory
from src.utils.vector_store import VectorManager

logger = logging.getLogger("abi_assistant.api")


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        json_schema_extra={"examples": ["Qual é a política de sustentabilidade da AB InBev?"]},
    )
    thread_id: str | None = Field(default=None)


class ChatResponse(BaseModel):
    answer: str
    thread_id: str
    compliance_approved: bool
    compliance_reason: str = ""
    route: str = ""
    validation_passed: bool | None = None
    validation_notes: str = ""
    sources_cited: list[str] = []
    steps_taken: list[str] = []


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "abi-smart-assistant"
    version: str = "1.0.0"


# singleton do grafo (inicializado no lifespan)
_graph = None
_factory = None
_vectors = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos pesados uma vez no startup."""
    global _graph, _factory, _vectors  # noqa: PLW0603

    logger.info("Initialising shared dependencies…")
    _factory = LLMFactory()
    _vectors = VectorManager()
    _graph = build_graph(llm_factory=_factory, vector_manager=_vectors)
    logger.info("API ready.")

    yield  # — app rodando —

    logger.info("Shutting down…")


app = FastAPI(
    title="ABI Smart Assistant API",
    version="1.0.0",
    description="API multi-agente RAG para base de conhecimento AB InBev.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Request-Duration-Ms"],
)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["infra"])
async def health():
    return HealthResponse()


@app.get("/api/v1/metrics", tags=["infra"])
async def metrics():
    if _factory is None:
        raise HTTPException(status_code=503, detail="Service not ready yet.")
    return _factory.metrics


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Loga duração, adiciona headers de tracing e valida API key."""
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    # auth check (pula health, docs, openapi e OPTIONS)
    public_paths = {"/api/v1/health", "/docs", "/redoc", "/openapi.json"}
    if (
        API_KEY
        and request.url.path not in public_paths
        and request.method != "OPTIONS"
        and request.headers.get("X-API-Key") != API_KEY
    ):
        from starlette.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key.", "request_id": request_id},
            headers={"X-Request-Id": request_id},
        )

    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Request-Duration-Ms"] = f"{elapsed_ms:.1f}"
    logger.info(
        "HTTP %s %s → %d (%.0f ms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(body: ChatRequest):
    """Processa pergunta pelo pipeline: Compliance → Router → (RAG|Direct) → Validator."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Service not ready yet.")

    thread_id = body.thread_id or str(uuid.uuid4())

    initial_state = {
        "question": body.question,
        "compliance_approved": False,
        "compliance_reason": "",
        "route": "",
        "needs_rag": False,
        "documents": [],
        "answer": "",
        "steps_taken": [],
        "sources_cited": [],
        "validation_passed": None,
        "validation_notes": "",
    }

    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    logger.info("API request: thread=%s  question='%s'", thread_id, body.question[:80])

    try:
        result = _graph.invoke(initial_state, config=config)
    except Exception:
        logger.exception("Pipeline error for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Erro interno do pipeline.")

    return ChatResponse(
        answer=result.get("answer", ""),
        thread_id=thread_id,
        compliance_approved=result.get("compliance_approved", False),
        compliance_reason=result.get("compliance_reason", ""),
        route=result.get("route", ""),
        validation_passed=result.get("validation_passed"),
        validation_notes=result.get("validation_notes", ""),
        sources_cited=result.get("sources_cited", []),
        steps_taken=result.get("steps_taken", []),
    )
