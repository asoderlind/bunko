<script lang="ts">
  import { LockKeyhole, Loader2 } from "lucide-svelte";
  import { auth } from "$lib/stores.svelte";

  let password = $state("");
  let input = $state<HTMLInputElement | null>(null);

  $effect(() => {
    input?.focus();
  });

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    if (!password) return;
    await auth.login(password);
  }
</script>

<div class="flex min-h-dvh items-center justify-center p-6">
  <form
    onsubmit={submit}
    class="w-full max-w-sm space-y-5 rounded-xl border bg-card p-6 shadow-sm"
  >
    <div class="space-y-1">
      <div class="flex items-center gap-2">
        <LockKeyhole class="h-5 w-5 text-muted-foreground" />
        <h1 class="text-lg font-semibold tracking-tight">easy-notes</h1>
      </div>
      <p class="text-sm text-muted-foreground">Enter your password to continue.</p>
    </div>

    <input
      type="password"
      class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      autocomplete="current-password"
      placeholder="Password"
      aria-label="Password"
      bind:value={password}
      bind:this={input}
    />

    {#if auth.error}
      <p role="alert" class="text-sm text-red-400">{auth.error}</p>
    {/if}

    <button
      type="submit"
      class="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
      disabled={!password || auth.pending}
    >
      {#if auth.pending}
        <Loader2 class="h-4 w-4 animate-spin" /> Signing in…
      {:else}
        Sign in
      {/if}
    </button>
  </form>
</div>
