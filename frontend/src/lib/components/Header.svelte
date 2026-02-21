<!--
  Header – barra minimalista com blur backdrop + indicador de saúde da API.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { checkHealth } from '$lib/api';

  interface Props {
    onNewChat: () => void;
    hasMessages: boolean;
  }
  let { onNewChat, hasMessages }: Props = $props();

  let status: 'checking' | 'online' | 'offline' = $state('checking');

  onMount(async () => {
    try { await checkHealth(); status = 'online'; }
    catch { status = 'offline'; }
  });
</script>

<header>
  <div class="inner">
    <!-- Brand -->
    <div class="brand">
      <div class="logo">
        <span class="logo-text">AB</span>
      </div>
      <div class="brand-info">
        <span class="brand-name">Smart Assistant</span>
        <span class="brand-tag">AB InBev</span>
      </div>
    </div>

    <!-- Actions -->
    <div class="actions">
      <!-- Status pill -->
      <div
        class="status-pill"
        class:online={status === 'online'}
        class:offline={status === 'offline'}
      >
        <span class="dot"></span>
        <span class="label">
          {status === 'checking' ? 'Conectando' : status === 'online' ? 'Online' : 'Offline'}
        </span>
      </div>

      <!-- New chat -->
      {#if hasMessages}
        <button class="btn-new" onclick={onNewChat} title="Nova conversa">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20h9"/><path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z"/>
          </svg>
          Nova conversa
        </button>
      {/if}
    </div>
  </div>
</header>

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(16px) saturate(1.5);
    -webkit-backdrop-filter: blur(16px) saturate(1.5);
    background: rgba(255,255,255,0.72);
    border-bottom: 1px solid var(--border-1);
  }

  .inner {
    max-width: 880px;
    margin: 0 auto;
    padding: 0 1.5rem;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  /* Brand */
  .brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .logo {
    width: 32px;
    height: 32px;
    background: var(--surface-dark);
    border-radius: var(--r-sm);
    display: grid;
    place-items: center;
    box-shadow: var(--shadow-sm);
  }

  .logo-text {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    color: var(--brand);
  }

  .brand-info {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .brand-name {
    font-size: 0.88rem;
    font-weight: 650;
    color: var(--text-1);
  }

  .brand-tag {
    font-size: 0.68rem;
    color: var(--text-4);
    font-weight: 500;
    letter-spacing: 0.02em;
  }

  /* Right actions */
  .actions {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  /* Status pill */
  .status-pill {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.65rem;
    border-radius: var(--r-full);
    background: var(--surface-2);
    border: 1px solid var(--border-1);
    font-size: 0.7rem;
    font-weight: 500;
    color: var(--text-4);
    transition: all 200ms var(--ease);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--text-4);
    transition: background 200ms;
  }

  .status-pill.online { color: var(--green); border-color: rgba(34,197,94,0.2); background: rgba(34,197,94,0.06); }
  .status-pill.online .dot { background: var(--green); box-shadow: 0 0 6px rgba(34,197,94,0.4); }

  .status-pill.offline { color: var(--red); border-color: rgba(239,68,68,0.2); background: rgba(239,68,68,0.06); }
  .status-pill.offline .dot { background: var(--red); }

  /* New chat button */
  .btn-new {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: var(--r-sm);
    font-size: 0.78rem;
    font-weight: 560;
    color: var(--text-2);
    background: var(--surface-0);
    border: 1px solid var(--border-1);
    box-shadow: var(--shadow-xs);
    transition: all 150ms var(--ease);
  }
  .btn-new:hover {
    background: var(--surface-2);
    border-color: var(--border-2);
    box-shadow: var(--shadow-sm);
  }
  .btn-new:active { transform: scale(0.97); }

  @media (max-width: 640px) {
    .inner { padding: 0 1rem; }
    .brand-tag { display: none; }
    .label { display: none; }
  }
</style>
