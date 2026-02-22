# ADR-001: LangGraph como Orquestrador Multi-Agente

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2025-01 |

## Contexto

O case exige um sistema **multi-agente** com pelo menos 3 agentes especializados,
pipeline configurável e capacidade de depuração passo-a-passo.

**Alternativas consideradas:**

| Framework | Prós | Contras |
|-----------|------|---------|
| **LangGraph** | StateGraph tipado, checkpointing nativo, conditional edges, integração LangChain | API mais verbosa |
| CrewAI | Sintaxe declarativa, role-based | Menos controle sobre o grafo, overhead de abstração |
| AutoGen | Bom para chat multiagente | Voltado para agentes autônomos conversacionais, menos fit para pipeline |
| Código puro | Zero dependências extras | Reinventar state management, checkpointing, retries |

## Decisão

Escolhi **LangGraph** (`StateGraph` + `MemorySaver`) como orquestrador.

## Justificativa

1. **Grafo explícito**: `add_node()` + `add_conditional_edges()` tornam o pipeline
   visível e testável — cada agente é um nó isolado.
2. **Tipagem de estado**: `TypedDict` (`AssistantState`) garante que cada nó
   receba e devolva exatamente os campos esperados.
3. **Checkpointing**: `MemorySaver` permite `thread_id` para memória de
   conversação sem código extra.
4. **Conditional edges**: Roteamento dinâmico (rag/direct/clarify) é nativo,
   sem if/else espalhado.
5. **Ecossistema LangChain**: Reutilizo `ChatOpenAI`, `AzureChatOpenAI`,
   embeddings, text splitters — tudo plugável.

## Consequências

- **Positivas**: Pipeline testável nó a nó, fácil adicionar agentes, state visível em logs.
- **Negativas**: Dependência do LangGraph (lock-in leve), curva de aprendizado para novos devs.
- **Riscos mitigados**: Cada agente é uma classe Python pura — migrar para outro
  orquestrador exigiria apenas reescrever `graph.py`.
