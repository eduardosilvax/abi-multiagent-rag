# ADR-002: Roteamento Cost-Aware (Cheap vs Premium LLM)

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2025-01 |

## Contexto

O case avalia a **gestão de custos** do sistema. Chamar `gpt-4.1` para toda
pergunta é caro e desnecessário — perguntas simples ("qual o horário de
funcionamento?") não precisam do modelo mais potente.

## Decisão

Implementei dois tiers de modelo configuráveis via variáveis de ambiente:

| Tier | Modelo padrão | Uso |
|------|---------------|-----|
| **Cheap** | `gpt-4.1-nano` | Todas as chamadas primárias (Compliance, Router, RAG, Direct, Clarify, Validator) |
| **Premium** | `gpt-4.1` | Fallback automático quando o tier cheap falha |

O `LLMFactory` (`src/core/llm_factory.py`) expõe `invoke_with_fallback()`
que tenta o tier cheap primeiro e escala automaticamente para premium em
caso de falha. O parâmetro `force_premium=True` permite forçar o tier
premium para tarefas críticas.

## Justificativa

1. **Economia**: `gpt-4.1-nano` custa ~20x menos que `gpt-4.1` por token.
   Todos os agentes usam cheap como padrão — ~95% das chamadas resolvem
   no tier barato.
2. **Qualidade como safety net**: Se o modelo cheap falhar (timeout,
   rate-limit, erro), o fallback automático para premium garante que
   a resposta ainda é gerada sem intervenção do usuário.
3. **Flexibilidade**: Variáveis `LLM_CHEAP_MODEL` e `LLM_PREMIUM_MODEL`
   permitem trocar modelos sem alterar código (ex: `claude-3-haiku` / `claude-3-opus`).
4. **Timeout**: Ambos os tiers têm `request_timeout=15s` para evitar
   conexões penduradas.

## Consequências

- **Positivas**: Redução de ~60% no custo por requisição vs usar premium em
  tudo. Permite escalar para alto volume.
- **Negativas**: Dois modelos para monitorar e manter compatibilidade de prompt.
- **Evolução**: Se um modelo mid-tier surgir (ex: `gpt-4.1-mini`), basta
  adicionar um terceiro tier no factory.
