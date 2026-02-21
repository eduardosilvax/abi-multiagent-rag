# Orquestrador LangGraph — monta o grafo de agentes e compila o pipeline.
# Fluxo: Compliance → Router → (RAG | Direct | Clarify) → Validator → END

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agents.compliance import ComplianceAgent
from src.agents.rag_agent import RAGAgent
from src.agents.router import ClarifyAgent, DirectAnswerAgent, RouterAgent
from src.agents.validator import ValidatorAgent
from src.core.llm_factory import LLMFactory
from src.schemas.state import AssistantState
from src.utils.vector_store import VectorManager

logger = logging.getLogger("abi_assistant.graph")


def _compliance_gate(state: AssistantState) -> str:
    """Edge condicional: se compliance aprovou, segue pro Router; senão, END."""
    if state.get("compliance_approved", False):
        return "router"
    return END


def _rag_or_direct(state: AssistantState) -> str:
    """Edge condicional: roteia pra RAG, Direct ou Clarify conforme o Router decidiu."""
    route = state.get("route", "")
    if route == "clarify":
        return "clarify"
    if state.get("needs_rag", True):
        return "rag_agent"
    return "direct_answer"


def build_graph(
    llm_factory: LLMFactory | None = None,
    vector_manager: VectorManager | None = None,
) -> StateGraph:
    """Monta e compila o pipeline multi-agente LangGraph.

    Fluxo: START → compliance → router → (rag|direct|clarify) → validator → END
    """
    factory = llm_factory or LLMFactory()
    vectors = vector_manager or VectorManager()

    compliance = ComplianceAgent(factory)
    router = RouterAgent(factory)
    rag = RAGAgent(factory, vectors)
    direct = DirectAnswerAgent(factory)
    clarify = ClarifyAgent(factory)
    validator = ValidatorAgent(factory)

    graph = StateGraph(AssistantState)

    graph.add_node("compliance", compliance.run)
    graph.add_node("router", router.run)
    graph.add_node("rag_agent", rag.run)
    graph.add_node("direct_answer", direct.run)
    graph.add_node("clarify", clarify.run)
    graph.add_node("validator", validator.run)

    graph.set_entry_point("compliance")

    graph.add_conditional_edges(
        "compliance",
        _compliance_gate,
        {
            "router": "router",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "router",
        _rag_or_direct,
        {
            "rag_agent": "rag_agent",
            "direct_answer": "direct_answer",
            "clarify": "clarify",
        },
    )

    graph.add_edge("rag_agent", "validator")
    graph.add_edge("direct_answer", "validator")
    graph.add_edge("clarify", END)
    graph.add_edge("validator", END)

    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)

    logger.info("LangGraph pipeline compiled successfully.")
    return compiled
