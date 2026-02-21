<!--
  Chat page — orquestra Header, EmptyState, mensagens e input.

  Fluxo:
    1. Msg do user aparece imediatamente
    2. Bolha "typing" como feedback (<100ms)
    3. API responde → substitui typing pela resposta real
    4. Auto-scroll suave
-->
<script lang="ts">
  import { tick } from 'svelte';
  import Header from '$lib/components/Header.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import ChatMessage from '$lib/components/ChatMessage.svelte';
  import ChatInput from '$lib/components/ChatInput.svelte';
  import { sendMessage } from '$lib/api';
  import type { ChatMessage as Msg, ResponseMeta } from '$lib/types';

  let messages: Msg[] = $state([]);
  let threadId: string | null = $state(null);
  let loading = $state(false);
  let scrollEl: HTMLDivElement | undefined = $state();

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  async function scrollBottom() {
    await tick();
    scrollEl?.scrollTo({ top: scrollEl.scrollHeight, behavior: 'smooth' });
  }

  function newChat() { messages = []; threadId = null; }

  async function send(text: string) {
    if (loading) return;

    // 1. User message
    messages = [...messages, { id: uid(), role: 'user', content: text, timestamp: new Date() }];

    // 2. Thinking indicator
    const tid = uid();
    messages = [...messages, { id: tid, role: 'assistant', content: '__THINKING__', timestamp: new Date() }];
    loading = true;
    await scrollBottom();

    try {
      const data = await sendMessage(text, threadId);
      threadId = data.thread_id;

      const meta: ResponseMeta = {
        compliance_approved: data.compliance_approved,
        compliance_reason: data.compliance_reason,
        route: data.route,
        validation_passed: data.validation_passed,
        validation_notes: data.validation_notes,
        sources_cited: data.sources_cited,
        steps_taken: data.steps_taken,
      };

      messages = messages.map(m =>
        m.id === tid
          ? { id: tid, role: 'assistant' as const, content: data.answer || 'Sem resposta.', timestamp: new Date(), meta }
          : m
      );
    } catch (err) {
      messages = messages.map(m =>
        m.id === tid
          ? { id: tid, role: 'assistant' as const, content: `Desculpe, tive um problema ao buscar a resposta. Tente novamente em instantes. ${err instanceof Error ? err.message : ''}`.trim(), timestamp: new Date() }
          : m
      );
    } finally {
      loading = false;
      await scrollBottom();
    }
  }
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
</svelte:head>

<Header onNewChat={newChat} hasMessages={messages.length > 0} />

<main class="chat-area">
  <div class="messages" bind:this={scrollEl}>
    {#if messages.length === 0}
      <EmptyState onSuggestion={send} />
    {:else}
      <div class="messages-inner">
        {#each messages as msg (msg.id)}
          <ChatMessage message={msg} />
        {/each}
      </div>
    {/if}
  </div>

  <ChatInput onSend={send} disabled={loading} />
</main>

<style>
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    max-width: 880px;
    width: 100%;
    margin: 0 auto;
    min-height: 0;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  .messages-inner {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1.5rem 1.5rem 1rem;
  }

  @media (max-width: 640px) {
    .messages-inner { padding: 1rem 0.75rem 0.75rem; gap: 1rem; }
  }
</style>
