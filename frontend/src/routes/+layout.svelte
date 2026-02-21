<!--
  Root layout – importa CSS global + Header.
-->
<script lang="ts">
  import '../app.css';
  interface Props { children: import('svelte').Snippet; }
  let { children }: Props = $props();
</script>

<div class="shell">
  {@render children()}
</div>

<style>
  .shell {
    display: flex;
    flex-direction: column;
    min-height: 100dvh;
    background: var(--surface-1);
  }
</style>
