<!--
  ChatMessage – bolha de mensagem com avatar, markdown rendering e fontes.
-->
<script lang="ts">
  import type { ChatMessage } from '$lib/types';
  import TechDetails from './TechDetails.svelte';

  interface Props { message: ChatMessage; }
  let { message }: Props = $props();

  const isUser = $derived(message.role === 'user');
  const sources = $derived(message.meta?.sources_cited ?? []);
  const hasMeta = $derived(!!message.meta && (message.meta.route || message.meta.steps_taken.length > 0));

  /** Strip inline source citations from the answer when structured sources exist */
  const displayContent = $derived(
    sources.length > 0
      ? stripInlineSources(message.content)
      : message.content
  );

  function ts(d: Date) {
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="msg" class:user={isUser} class:bot={!isUser}>
  <!-- Avatar -->
  <div class="avatar" class:avatar-user={isUser} class:avatar-bot={!isUser}>
    {#if isUser}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
      </svg>
    {:else}
      <span class="avatar-logo">AB</span>
    {/if}
  </div>

  <!-- Bubble -->
  <div class="bubble">
    <!-- Sender label -->
    <div class="sender">
      <span class="name">{isUser ? 'Você' : 'ABI Assistant'}</span>
      <span class="time">{ts(message.timestamp)}</span>
    </div>

    <!-- Content -->
    <div class="content">
      {#if message.content === '__THINKING__'}
        <div class="typing">
          <div class="dot"></div>
          <div class="dot"></div>
          <div class="dot"></div>
        </div>
      {:else}
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        {@html renderMarkdown(displayContent)}
      {/if}
    </div>

    <!-- Sources -->
    {#if sources.length > 0}
      <div class="sources">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>
        </svg>
        {#each sources as src}
          <span class="source-tag">{src}</span>
        {/each}
      </div>
    {/if}

    <!-- Tech details -->
    {#if hasMeta && message.meta}
      <TechDetails meta={message.meta} />
    {/if}
  </div>
</div>

<script lang="ts" module>
  /**
   * Remove trailing inline source citations from the LLM answer.
   * Matches patterns like:
   *   "Fonte: Arquivo.md, páginas 0.59."
   *   "**Fontes consultadas:**\nFonte: Arquivo.md"
   *   "Fontes:\n- Arquivo.md"
   */
  function stripInlineSources(text: string): string {
    return text
      // Block: "Fontes consultadas:" / "Fontes:" header followed by lines starting with "Fonte:" or "- "
      .replace(/\n*\*{0,2}Fontes?\s*(consultadas)?\s*:?\*{0,2}\s*\n((\s*[-•]?\s*Fonte?:?\s*.+\n?)+)/gi, '')
      // Standalone trailing "Fonte: …" line(s) at the end
      .replace(/(\n\s*Fonte:\s*.+)+\s*$/gi, '')
      .trimEnd();
  }

  function renderMarkdown(text: string): string {
    return text
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code class="inline">$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
      .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^---$/gm, '<hr/>')
      .replace(/^\d+\.\s+(.+)$/gm, '<li class="ol">$1</li>')
      .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
      .replace(/((?:<li[^>]*>.*<\/li>\s*)+)/g, '<ul>$1</ul>')
      .replace(/\n/g, '<br/>');
  }
</script>

<style>
  .msg {
    display: flex;
    gap: 0.75rem;
    max-width: 85%;
    animation: fade-up 280ms var(--ease) both;
  }
  .msg.user  { align-self: flex-end; flex-direction: row-reverse; }
  .msg.bot   { align-self: flex-start; }

  /* Avatars */
  .avatar {
    width: 30px;
    height: 30px;
    border-radius: var(--r-sm);
    display: grid;
    place-items: center;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .avatar-user {
    background: var(--surface-dark);
    color: var(--brand);
  }
  .avatar-bot {
    background: var(--brand);
    color: var(--surface-dark);
  }
  .avatar-logo {
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.04em;
  }

  /* Bubble */
  .bubble {
    flex: 1;
    min-width: 0;
  }

  .sender {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
  }
  .name { font-size: 0.78rem; font-weight: 600; color: var(--text-1); }
  .time { font-size: 0.66rem; color: var(--text-4); }

  .msg.user .sender { flex-direction: row-reverse; }
  .msg.user .name { color: var(--text-2); }

  /* Content */
  .content {
    padding: 0.8rem 1rem;
    border-radius: var(--r-md);
    font-size: 0.9rem;
    line-height: 1.65;
    color: var(--text-1);
  }

  .msg.bot .content {
    background: var(--surface-0);
    border: 1px solid var(--border-1);
    border-top-left-radius: 3px;
    box-shadow: var(--shadow-xs);
  }

  .msg.user .content {
    background: var(--surface-dark);
    color: var(--text-inv);
    border-top-right-radius: 3px;
  }

  /* Markdown rich text */
  .content :global(code.inline) {
    background: rgba(0,0,0,0.05);
    padding: 0.12em 0.4em;
    border-radius: 4px;
    font-size: 0.85em;
  }
  .msg.user .content :global(code.inline) { background: rgba(255,255,255,0.12); }

  .content :global(pre) {
    background: #1a1a2e;
    color: #e4e4e7;
    padding: 0.85rem 1rem;
    border-radius: var(--r-sm);
    overflow-x: auto;
    margin: 0.5rem 0;
    font-size: 0.82rem;
    line-height: 1.55;
  }
  .content :global(pre code) { background: none; padding: 0; color: inherit; }

  .content :global(ul) {
    margin: 0.3rem 0;
    padding-left: 1.15rem;
    list-style-type: none;
  }
  .content :global(li) { position: relative; padding-left: 0.15rem; margin-bottom: 0.15rem; }
  .content :global(li)::before { content: '•'; position: absolute; left: -0.85rem; color: var(--text-4); }
  .content :global(li.ol)::before { content: counter(li-counter, decimal) '.'; counter-increment: li-counter; }

  .content :global(strong) { font-weight: 650; }
  .content :global(h2), .content :global(h3), .content :global(h4) {
    font-weight: 650; margin: 0.6rem 0 0.2rem; font-size: 0.95rem;
  }
  .content :global(hr) { border: none; border-top: 1px solid var(--border-1); margin: 0.7rem 0; }

  /* Sources */
  .sources {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    margin-top: 0.55rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--border-1);
    color: var(--text-4);
  }
  .source-tag {
    font-size: 0.68rem;
    font-weight: 550;
    padding: 0.15rem 0.5rem;
    background: var(--surface-2);
    border-radius: var(--r-full);
    color: var(--text-3);
  }

  /* Typing dots */
  .typing {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 0.35rem 0;
  }
  .typing .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-4);
    animation: typing-bounce 1.2s ease-in-out infinite;
  }
  .typing .dot:nth-child(2) { animation-delay: 0.15s; }
  .typing .dot:nth-child(3) { animation-delay: 0.3s; }

  @keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30% { transform: translateY(-7px); opacity: 1; }
  }

  @media (max-width: 640px) {
    .msg { max-width: 92%; }
    .avatar { width: 26px; height: 26px; }
    .content { padding: 0.65rem 0.85rem; font-size: 0.87rem; }
  }
</style>
