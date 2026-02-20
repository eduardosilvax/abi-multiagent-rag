# Estado do pipeline LangGraph (TypedDict pro checkpointing funcionar).

from __future__ import annotations

from typing import TypedDict


class Document(TypedDict, total=False):
    content: str
    source: str
    page: int | None
    score: float


class AssistantState(TypedDict, total=False):
    """Estado completo compartilhado entre todos os nós do LangGraph.

    Cada agente lê/escreve só os campos que precisa, mas o state inteiro
    fica disponível pra roteamento condicional e debug.
    """

    question: str
    compliance_approved: bool
    compliance_reason: str
    route: str
    needs_rag: bool
    documents: list[Document]
    answer: str
    steps_taken: list[str]
    sources_cited: list[str]
    validation_passed: bool
    validation_notes: str
