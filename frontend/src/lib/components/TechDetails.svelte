<!--
  Detalhes técnicos – accordion minimalista com ícone animado.
-->
<script lang="ts">
  import type { ResponseMeta } from '$lib/types';

  interface Props { meta: ResponseMeta; }
  let { meta }: Props = $props();

  let open = $state(false);

  const routeMap: Record<string,string> = {
    rag: 'RAG',
    direct: 'LLM Direto',
    clarify: 'Esclarecimento',
  };
</script>

<div class="details-wrap">
  <button class="toggle" onclick={() => open = !open} aria-expanded={open}>
    <svg class="chevron" class:open width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
    <span>Detalhes do processamento</span>
  </button>

  {#if open}
    <div class="body" style="animation: fade-up 200ms var(--ease) forwards;">
      {#if meta.route}
        <div class="row">
          <span class="label">Rota</span>
          <span class="chip">{routeMap[meta.route] ?? meta.route}</span>
        </div>
      {/if}
      {#if meta.steps_taken.length > 0}
        <div class="row">
          <span class="label">Steps</span>
          <span class="steps">{meta.steps_taken.join(' → ')}</span>
        </div>
      {/if}
      {#if meta.compliance_reason}
        <div class="row">
          <span class="label">Compliance</span>
          <span class={meta.compliance_approved ? 'pass' : 'fail'}>
            {meta.compliance_approved ? '✓' : '✗'} {meta.compliance_reason}
          </span>
        </div>
      {/if}
      {#if meta.validation_notes && meta.validation_notes !== 'Validacao nao aplicavel (resposta direta).'}
        <div class="row">
          <span class="label">Validação</span>
          <span class={meta.validation_passed ? 'pass' : 'fail'}>
            {meta.validation_passed ? '✓' : '✗'} {meta.validation_notes}
          </span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .details-wrap {
    margin-top: 0.6rem;
    padding-top: 0.6rem;
    border-top: 1px solid var(--border-1);
  }

  .toggle {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.72rem;
    font-weight: 550;
    color: var(--text-4);
    padding: 0.15rem 0;
    transition: color 150ms;
  }
  .toggle:hover { color: var(--text-2); }

  .chevron {
    transition: transform 200ms var(--ease);
  }
  .chevron.open { transform: rotate(90deg); }

  .body {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-top: 0.45rem;
    padding-left: 0.25rem;
  }

  .row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    font-size: 0.72rem;
    line-height: 1.5;
  }

  .label {
    color: var(--text-4);
    font-weight: 550;
    min-width: 70px;
    flex-shrink: 0;
  }

  .chip {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    background: var(--surface-2);
    border-radius: var(--r-full);
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-2);
  }

  .steps { color: var(--text-3); font-family: var(--mono); font-size: 0.68rem; }
  .pass  { color: var(--green); }
  .fail  { color: var(--red); }
</style>
