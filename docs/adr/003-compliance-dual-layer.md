# ADR-003: Compliance Dual-Layer (Regex + LLM Semântico)

| Campo | Valor |
|-------|-------|
| **Status** | Aceito |
| **Data** | 2025-01 |

## Contexto

O case exige um **gatekeeper de compliance** que bloqueie tópicos sensíveis
(política, religião, conteúdo inadequado) e proteja contra prompt injection,
sem sacrificar a usabilidade bloqueando perguntas legítimas.

**O grande desafio:** distinguir "qual é a política de sustentabilidade da
empresa?" (permitido) de "qual é a melhor política partidária?" (bloqueado).
Um simples blocklist de palavras-chave (`"política"`) geraria falsos positivos
inaceitáveis.

**Alternativas consideradas:**

| Estratégia | Prós | Contras |
|-----------|------|---------|
| **Só regex / blocklist** | Latência zero, custo zero de API | Não distingue contexto semântico; altíssima taxa de falso positivo |
| **Só LLM** | Entende nuance semântica, poucos falsos positivos | Custo de API em TODAS as perguntas, inclusive injection óbvio; latência |
| **Dual-layer (regex → LLM)** | Regex pega injection barato e rápido; LLM resolve ambiguidade semântica | Duas camadas para manter, prompt de classificação precisa de tuning |
| **Guardrails / NeMo** | Framework pronto | Dependência pesada, menos controle sobre regras customizadas |

## Decisão

Optei por uma **arquitetura dual-layer** no `ComplianceAgent`:

### Layer 1 — Regex (rápido, custo zero)

12 padrões compilados (`re.Pattern`) que detectam prompt injection óbvio:
- `"ignore todas as instruções"` / `"ignore all instructions"`
- `"system prompt"`, `"jailbreak"`, `"bypass"`
- Variações em português e inglês

**Quando aciona:** resposta imediata de bloqueio (`prompt_injection`), sem
chamar LLM. Custo: 0 tokens. Latência: < 1ms.

### Layer 2 — LLM Semântico (nuance, custo controlado)

Se o regex não barrou, a pergunta vai para o LLM com uma taxonomia de
classificação:

| Categoria | Exemplos |
|-----------|----------|
| `politics` | Partidos, candidatos, eleições, legislação partidária |
| `religion` | Doutrinas, rituais, conversão, superioridade religiosa |
| `discrimination` | Conteúdo racista, sexista, homofóbico |
| `drugs_alcohol` | Incentivo ao uso, receitas, cultivo |
| `violence` | Instruções de violência, armas, ameaças |
| `sexuality` | Conteúdo sexual explícito |
| `safe` | Qualquer pergunta fora das categorias acima |

O prompt instrui o LLM a retornar JSON estruturado:
`{"classification": "...", "confidence": 0.0-1.0}`.

**Regra crítica:** Na dúvida, classifica como `safe`. O sistema prefere
falsos negativos (deixar passar algo borderline) a falsos positivos
(bloquear pergunta legítima do usuário).

## Justificativa

1. **Economia na maioria dos casos**: Injection patterns cobrem ~100% dos
   ataques comuns. Regex custa zero — economiza ~15% das chamadas LLM.
2. **Precisão semântica**: "política de sustentabilidade da empresa" vs
   "melhor partido político" exige compreensão de contexto. Só LLM resolve.
3. **Latência otimizada**: Injection é barrado em <1ms. Perguntas legítimas
   passam pelo LLM em ~200ms (tier cheap). O happy path não é penalizado.
4. **Follow-ups não bloqueados**: Perguntas como "pode me explicar melhor?"
   ou "não concordo" não são falsamente classificadas como injection —
   o LLM entende contexto conversacional.
5. **Bias de permissão**: O prompt de compliance é explícito: "na dúvida,
   permita". Isso reduz drasticamente falsos positivos e mantém a experiência
   do usuário fluida.

## Trade-offs

| Aspecto | Positivo | Negativo |
|---------|----------|----------|
| **Custo** | Regex evita LLM em injection | Chamada LLM obrigatória para perguntas normais |
| **Precisão** | LLM distingue nuance semântica | Prompt de classificação pode precisar de tuning periódico |
| **Latência** | Injection barrado em <1ms | Perguntas normais têm +200ms de classificação |
| **Manutenção** | Regex e LLM são independentes | Duas camadas para testar e manter |
| **Falsos positivos** | Bias de permissão reduz bloqueios indevidos | Risco (aceito) de deixar algo borderline passar |

## Cobertura de Testes

A estratégia dual-layer é validada em 3 camadas:

- **23 testes unitários** (`tests/test_compliance.py`) — regex patterns, classificação LLM, edge cases
- **15 evals** (`evals/evaluate.py`) — cenários de compliance + injection com score de aprovação
- **13 cenários live** (`tests/test_compliance_live.py`) — validação de falsos positivos com LLM real

## Consequências

- **Positivas**: Alta precisão com baixo custo. UX limpa — o sistema só bloqueia
  quando tem certeza. Testável em isolamento (regex puro não precisa de API key).
- **Negativas**: Dois subsistemas para manter. Prompt de classificação é
  sensível à formulação.
- **Evolução**: Se o volume crescer, o Layer 2 pode ser substituído por um
  classificador fine-tuned (ex: modelo distilado) eliminando a dependência
  do LLM para classificação.
