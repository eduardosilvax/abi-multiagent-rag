<!--
  EmptyState – Hero visual com gradient, sugestões e animações.
  Exibido quando não há mensagens no chat.
-->
<script lang="ts">
  interface Props {
    onSuggestion: (text: string) => void;
  }
  let { onSuggestion }: Props = $props();

  const suggestions = [
    { label: 'Sustentabilidade', q: 'Qual é a política de sustentabilidade da AB InBev?' },
    { label: 'Código de Conduta', q: 'Resuma o código de conduta para novos funcionários.' },
    { label: 'Onboarding', q: 'Quais são os passos do processo de onboarding?' },
  ];
</script>

<div class="empty">
  <!-- Gradient orb (decorative) -->
  <div class="orb"></div>

  <!-- Logo mark -->
  <div class="mark">
    <span>AB</span>
  </div>

  <h1>
    <span class="greeting">Olá!</span> Como posso ajudar?
  </h1>

  <p class="sub">
    Pergunte sobre políticas, guias e documentos internos da AB InBev. Estou aqui para facilitar sua busca.
  </p>

  <!-- Suggestion cards -->
  <div class="cards">
    {#each suggestions as s, i}
      <button
        class="card"
        style="animation-delay: {300 + i * 80}ms"
        onclick={() => onSuggestion(s.q)}
      >
        <span class="card-label">{s.label}</span>
        <svg class="card-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
        </svg>
      </button>
    {/each}
  </div>

  <p class="powered">
    Multi-Agent RAG · LangGraph · Qdrant
  </p>
</div>

<style>
  .empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem 1.5rem;
    position: relative;
    overflow: hidden;
  }

  /* Decorative gradient orb */
  .orb {
    position: absolute;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(
      circle,
      rgba(252, 227, 0, 0.10) 0%,
      rgba(252, 227, 0, 0.03) 40%,
      transparent 70%
    );
    top: -50px;
    pointer-events: none;
    animation: float 8s ease-in-out infinite;
  }

  /* Logo mark */
  .mark {
    width: 56px;
    height: 56px;
    border-radius: var(--r-md);
    background: var(--surface-dark);
    display: grid;
    place-items: center;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow-md), 0 0 48px rgba(252,227,0,0.12);
    animation: scale-in 400ms var(--ease) both;
    position: relative;
  }
  .mark span {
    font-size: 1rem;
    font-weight: 800;
    color: var(--brand);
    letter-spacing: 0.04em;
  }

  h1 {
    font-size: clamp(1.5rem, 4vw, 2rem);
    font-weight: 720;
    color: var(--text-1);
    line-height: 1.2;
    margin-bottom: 0.6rem;
    animation: fade-up 400ms var(--ease) both;
    animation-delay: 100ms;
    letter-spacing: -0.025em;
  }

  .greeting {
    background: linear-gradient(135deg, var(--brand) 0%, #f59e0b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .sub {
    max-width: 400px;
    font-size: 0.92rem;
    color: var(--text-3);
    line-height: 1.55;
    margin-bottom: 2rem;
    animation: fade-up 400ms var(--ease) both;
    animation-delay: 180ms;
  }

  /* Suggestion cards */
  .cards {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    justify-content: center;
    margin-bottom: 2rem;
  }

  .card {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.65rem 1rem;
    background: var(--surface-0);
    border: 1px solid var(--border-1);
    border-radius: var(--r-md);
    box-shadow: var(--shadow-xs);
    font-size: 0.82rem;
    font-weight: 530;
    color: var(--text-2);
    transition: all 180ms var(--ease);
    animation: fade-up 350ms var(--ease) both;
    position: relative;
  }

  .card:hover {
    border-color: var(--brand);
    box-shadow: var(--shadow-md), 0 0 0 3px var(--brand-muted);
    transform: translateY(-2px);
    color: var(--text-1);
  }

  .card:active { transform: translateY(0) scale(0.98); }

  .card-arrow {
    color: var(--text-4);
    transition: all 180ms var(--ease);
    opacity: 0;
    transform: translateX(-4px);
  }
  .card:hover .card-arrow { opacity: 1; transform: translateX(0); color: var(--brand-hover); }

  .powered {
    font-size: 0.68rem;
    color: var(--text-4);
    animation: fade-in 400ms var(--ease) both;
    animation-delay: 500ms;
    letter-spacing: 0.02em;
  }

  @media (max-width: 640px) {
    .cards { flex-direction: column; align-items: center; }
    .card { width: 100%; max-width: 280px; justify-content: center; }
    .orb { width: 320px; height: 320px; }
  }
</style>
