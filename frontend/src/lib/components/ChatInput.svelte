<!--
  ChatInput – barra de input flutuante com efeito de foco premium.
  Enter envia, Shift+Enter nova linha.
-->
<script lang="ts">
  interface Props {
    disabled?: boolean;
    onSend: (text: string) => void;
  }
  let { disabled = false, onSend }: Props = $props();

  let value = $state('');
  let el: HTMLTextAreaElement | undefined = $state();
  let focused = $state(false);

  function submit() {
    const t = value.trim();
    if (!t || disabled) return;
    onSend(t);
    value = '';
    if (el) { el.style.height = 'auto'; }
  }

  function keydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  }

  function autoResize() {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }
</script>

<div class="input-bar" class:focused class:disabled>
  <div class="input-inner">
    <textarea
      bind:this={el}
      bind:value
      onkeydown={keydown}
      oninput={autoResize}
      onfocus={() => focused = true}
      onblur={() => focused = false}
      placeholder="Digite sua pergunta aqui…"
      rows="1"
      {disabled}
    ></textarea>

    <button
      class="send"
      onclick={submit}
      disabled={disabled || !value.trim()}
      aria-label="Enviar"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>
      </svg>
    </button>
  </div>

  <p class="hint">
    <kbd>Enter</kbd> para enviar · <kbd>Shift + Enter</kbd> nova linha
  </p>
</div>

<style>
  .input-bar {
    padding: 0 1.5rem 1rem;
    animation: fade-up 300ms var(--ease) both;
    animation-delay: 150ms;
  }

  .input-inner {
    display: flex;
    align-items: flex-end;
    gap: 0;
    background: var(--surface-0);
    border: 1.5px solid var(--border-1);
    border-radius: var(--r-lg);
    box-shadow: var(--shadow-sm);
    transition: all 200ms var(--ease);
    overflow: hidden;
  }

  .focused .input-inner {
    border-color: var(--brand);
    box-shadow: var(--shadow-md), 0 0 0 3px var(--brand-muted);
  }

  .disabled .input-inner { opacity: 0.6; }

  textarea {
    flex: 1;
    resize: none;
    border: none;
    outline: none;
    background: transparent;
    padding: 0.85rem 0 0.85rem 1.1rem;
    font-family: var(--font);
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text-1);
    min-height: 44px;
    max-height: 160px;
  }

  textarea::placeholder { color: var(--text-4); }
  textarea:disabled { cursor: not-allowed; }

  .send {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    margin: 3px;
    border-radius: var(--r-md);
    background: var(--surface-dark);
    color: var(--brand);
    transition: all 150ms var(--ease);
    flex-shrink: 0;
  }

  .send:hover:not(:disabled) {
    background: var(--brand);
    color: var(--surface-dark);
    box-shadow: var(--shadow-sm);
  }

  .send:active:not(:disabled) { transform: scale(0.92); }

  .send:disabled {
    background: var(--surface-2);
    color: var(--text-4);
    cursor: not-allowed;
  }

  .hint {
    text-align: center;
    font-size: 0.65rem;
    color: var(--text-4);
    margin-top: 0.45rem;
  }

  kbd {
    font-family: var(--font);
    font-size: 0.62rem;
    font-weight: 550;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    background: var(--surface-2);
    border: 1px solid var(--border-1);
    color: var(--text-3);
  }

  @media (max-width: 640px) {
    .input-bar { padding: 0 0.75rem 0.75rem; }
    .hint { display: none; }
  }
</style>
