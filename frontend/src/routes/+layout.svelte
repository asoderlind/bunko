<script lang="ts">
  import "../index.css";
  import { onMount } from "svelte";
  import { auth } from "$lib/stores.svelte";
  import Login from "$lib/Login.svelte";
  import Shell from "$lib/Shell.svelte";
  import { Loader2 } from "lucide-svelte";
  import { watchDeploy } from "$lib/deploy-check";

  let { children } = $props();

  onMount(() => {
    void auth.load();
    watchDeploy();
  });
</script>

{#if !auth.loaded}
  <div class="flex min-h-dvh items-center justify-center">
    <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
  </div>
{:else if !auth.user}
  <Login />
{:else}
  <Shell>
    {@render children?.()}
  </Shell>
{/if}
