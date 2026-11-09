<script lang="ts">
  import { CircleAlert, Info, X } from "lucide-svelte";
  import { dismissToast, toasts } from "$lib/toast.svelte";
</script>

<div
  class="pointer-events-none fixed right-4 top-4 z-[100] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
  aria-live="polite"
  aria-atomic="false"
>
  {#each toasts as t (t.id)}
    <div
      class="pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-card p-3 text-sm shadow-lg shadow-black/20 animate-in fade-in-0 slide-in-from-top-2"
    >
      {#if t.kind === "error"}
        <CircleAlert class="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      {:else}
        <Info class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      {/if}
      <p class="min-w-0 flex-1 text-foreground/90">{t.message}</p>
      <button
        class="-mr-1 -mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-label="Dismiss notification"
        onclick={() => dismissToast(t.id)}
      >
        <X class="h-3.5 w-3.5" />
      </button>
    </div>
  {/each}
</div>
