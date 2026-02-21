# Router: decide se pergunta vai pra RAG, resposta direta ou clarificação.

from __future__ import annotations

import logging

from src.core.llm_factory import LLMFactory
from src.schemas.state import AssistantState

logger = logging.getLogger("abi_assistant.router")

_ROUTER_PROMPT = """\
Você é o Router de um assistente empresarial da AB InBev.

Analise a pergunta abaixo e decida como o sistema deve agir.

## Regras:
- Perguntas sobre políticas internas, procedimentos, dados da empresa,
  documentos, relatórios, metas, KPIs → "rag"
- Perguntas genéricas, saudações, piadas, definições simples, conhecimento
  geral → "direct"
- Perguntas vagas, ambíguas, incompletas, sem contexto suficiente para
  entender a intenção (ex: "me fala daquilo", "o que vocês acham?",
  "pode me ajudar com o processo?", pronomes sem referente claro) → "clarify"
- Na dúvida entre "rag" e "direct", escolha "rag".
- Na dúvida se é ambígua, prefira "clarify" (melhor pedir esclarecimento
  do que inventar uma resposta irrelevante).

## Formato de resposta (JSON estrito):
```json
{{
  "route": "rag" | "direct" | "clarify",
  "reasoning": "<explicação curta>"
}}
```

Responda APENAS com o JSON.

### Pergunta:
{question}
"""

_DIRECT_ANSWER_PROMPT = """\
Você é o Assistente Inteligente da AB InBev.  Responda de forma clara,
objetiva e em português corporativo.

## Regras:
1. Seja útil e profissional.
2. Se não souber a resposta, diga honestamente.
3. Não invente dados ou políticas da empresa.
4. Mantenha respostas concisas (2-5 parágrafos no máximo).

### Pergunta:
{question}

### Resposta:
"""


class RouterAgent:
    """Classifica a intenção da pergunta e roteia pra RAG, Direct ou Clarify.

    Na dúvida entre RAG e Direct, vai de RAG (mais seguro).
    Na dúvida se é ambígua, pede esclarecimento.
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory

    def run(self, state: AssistantState) -> AssistantState:
        """Nó LangGraph: classifica a pergunta e define a rota."""
        question = state.get("question", "")
        steps = list(state.get("steps_taken", []))
        steps.append("router")

        prompt = _ROUTER_PROMPT.format(question=question)
        result = self._llm.invoke_structured(prompt)

        route = result.get("route", "rag")  # default pra RAG na dúvida
        if route not in ("rag", "direct", "clarify"):
            route = "rag"  # fallback pra saída inesperada da LLM
        reasoning = result.get("reasoning", "")

        logger.info(
            "Router decision: route=%s  reason='%s'",
            route,
            reasoning,
        )

        return {
            **state,
            "route": route,
            "needs_rag": route == "rag",
            "steps_taken": steps,
        }


class DirectAnswerAgent:
    """Responde sem consultar documentos internos.

    Usado pra perguntas genéricas, saudações e conhecimento geral.
    Não usa vector store, não cita fontes.
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory

    def run(self, state: AssistantState) -> AssistantState:
        question = state.get("question", "")
        steps = list(state.get("steps_taken", []))
        steps.append("direct_answer")

        prompt = _DIRECT_ANSWER_PROMPT.format(question=question)
        answer = self._llm.invoke_with_fallback(prompt)

        return {
            **state,
            "documents": [],
            "answer": answer,
            "sources_cited": [],
            "steps_taken": steps,
        }


_CLARIFY_PROMPT = """\
Você é o Assistente Inteligente da AB InBev.  A pergunta do usuário
não ficou clara o suficiente para você decidir como responder.

Escreva uma resposta educada e profissional pedindo que o usuário
reformule a pergunta.  Inclua 2-3 sugestões de temas que o assistente
pode ajudar (políticas internas, onboarding, sustentabilidade, código
de conduta).

Seja conciso (máximo 3 parágrafos).

### Pergunta original:
{question}

### Resposta:
"""


class ClarifyAgent:
    """Pede reformulação quando a pergunta é vaga ou ambígua.

    Sugere temas relevantes e pula o Validator (não tem docs pra validar).
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory

    def run(self, state: AssistantState) -> AssistantState:
        question = state.get("question", "")
        steps = list(state.get("steps_taken", []))
        steps.append("clarify")

        prompt = _CLARIFY_PROMPT.format(question=question)
        answer = self._llm.invoke_with_fallback(prompt)

        return {
            **state,
            "documents": [],
            "answer": answer,
            "sources_cited": [],
            "steps_taken": steps,
        }
