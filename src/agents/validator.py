# Validador anti-alucinação: verifica se a resposta é fundamentada nos docs.
# Só roda no path RAG (respostas diretas não têm docs pra comparar).

from __future__ import annotations

import logging
from typing import Any

from src.core.llm_factory import LLMFactory
from src.schemas.state import AssistantState

logger = logging.getLogger("abi_assistant.validator")

_VALIDATION_PROMPT = """\
Você é um auditor de qualidade da AB InBev.  Sua tarefa é verificar se a
RESPOSTA gerada é fiel ao CONTEXTO dos documentos internos.

## Regras de Validação:
1. A resposta deve ser derivável EXCLUSIVAMENTE do contexto.
2. Informações que NÃO aparecem no contexto são consideradas alucinação.
3. Pequenas paráfrases ou sínteses são aceitáveis — desde que o sentido
   seja preservado.
4. Citação de fontes corretas é um bom sinal.
5. Se a resposta menciona dados, números ou datas, eles DEVEM aparecer
   no contexto.

## Formato de resposta (JSON estrito):
```json
{{
  "grounded": true | false,
  "confidence": 0.0 a 1.0,
  "issues": ["lista de problemas encontrados (vazia se nenhum)"],
  "suggestion": "versão corrigida da resposta (somente se grounded=false)"
}}
```

Responda APENAS com o JSON.

---

## Contexto dos Documentos:
{context}

## Resposta Gerada:
{answer}

## Pergunta Original:
{question}
"""

_FALLBACK_MSG = (
    "Não foi possível confirmar a resposta com base nos documentos internos. "
    "Por favor, consulte diretamente as fontes ou entre em contato com o time "
    "responsável para obter informações verificadas."
)


class ValidatorAgent:
    """Guarda anti-alucinação: confere se a resposta é fundamentada nos docs.

    Só roda no path RAG (respostas diretas não têm docs pra cruzar).
    Retorna score de confiança (0.0–1.0) e sugere correção se precisar.
    """

    def __init__(self, llm_factory: LLMFactory) -> None:
        self._llm = llm_factory

    def _build_doc_context(self, docs: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for i, doc in enumerate(docs, 1):
            source = doc.get("source", "desconhecido")
            parts.append(f"[Doc {i} – {source}]\n{doc.get('content', '')}")
        return "\n\n---\n\n".join(parts) if parts else "(nenhum documento)"

    def run(self, state: AssistantState) -> AssistantState:
        """Nó LangGraph: valida grounding da resposta contra os documentos.

        Threshold de confiança: 0.6. Abaixo disso, substitui a resposta.
        """
        steps = list(state.get("steps_taken", []))
        docs = state.get("documents", [])
        answer = state.get("answer", "")

        # respostas diretas pulam validação (nada pra cruzar)
        if not docs:
            logger.info("Validator skipped (direct-answer path, no docs).")
            steps.append("validator_skipped")
            return {
                **state,
                "validation_passed": True,
                "validation_notes": "Validação não aplicável (resposta direta).",
                "steps_taken": steps,
            }

        steps.append("validator")
        context = self._build_doc_context(docs)

        prompt = _VALIDATION_PROMPT.format(
            context=context,
            answer=answer,
            question=state.get("question", ""),
        )

        logger.info("Running anti-hallucination validation…")
        result = self._llm.invoke_structured(prompt)

        grounded = result.get("grounded", False)
        confidence = result.get("confidence", 0.0)
        issues = result.get("issues", [])
        suggestion = result.get("suggestion", "")

        logger.info(
            "Validation: grounded=%s  confidence=%.2f  issues=%d",
            grounded,
            confidence,
            len(issues),
        )

        if grounded and confidence >= 0.6:
            # resposta passou — mantém como está
            return {
                **state,
                "validation_passed": True,
                "validation_notes": "Resposta validada com sucesso.",
                "steps_taken": steps,
            }

        # resposta com problemas — usa versão corrigida se disponível
        logger.warning("Validation FAILED. Issues: %s", issues)
        corrected = suggestion if suggestion else _FALLBACK_MSG

        # preserva citações originais se existiam
        original_sources = state.get("sources_cited", [])
        if original_sources and suggestion:
            corrected += "\n\n---\n**Fontes consultadas:**\n" + "\n".join(original_sources)

        notes = "; ".join(issues) if issues else "Confiança insuficiente."

        return {
            **state,
            "answer": corrected,
            "validation_passed": False,
            "validation_notes": notes,
            "steps_taken": steps,
        }
