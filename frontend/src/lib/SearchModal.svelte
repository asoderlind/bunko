<script lang="ts">
  import { Dialog } from "bits-ui";
  import { goto } from "$app/navigation";
  import { Loader2, Search as SearchIcon, X } from "lucide-svelte";
  import { api, type Note } from "$lib/api";
  import TagPill from "$lib/TagPill.svelte";
  import { search } from "$lib/search.svelte";

  /**
   * Search modal, in the shape of Open WebUI's: opened from a sidebar item,
   * centred overlay, live results as you type, click to open.
   */
  let q = $state("");
  let results = $state<Note[]>([]);
  let loading = $state(false);
  let active = $state(0);
  let input = $state<HTMLInputElement | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;

  let open = $derived(search.visible);

  $effect(() => {
    if (open) {
      q = "";
      results = [];
      active = 0;
      setTimeout(() => input?.focus(), 0);
    }
  });

  async function run(term: string) {
    if (!term.trim()) {
      results = [];
      loading = false;
      return;
    }
    loading = true;
    try {
      const page = await api.listNotes({ q: term.trim(), limit: 20 });
      results = page.results;
      active = 0;
    } catch {
      results = [];
    } finally {
      loading = false;
    }
  }

  let lastTerm = $state("");
  $effect(() => {
    const term = q;
    if (term === lastTerm) return;
    lastTerm = term;
    if (timer) clearTimeout(timer);
    loading = !!term.trim();
    timer = setTimeout(() => void run(term), 150);
  });

  function choose(note: Note) {
    search.hide();
    void goto(`/notes/${note.id}`);
  }

  function onkeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      search.hide();
      return;
    }
    // Results are empty before typing, so guard on length or the index runs off
    // the end and Enter finds nothing.
    if (!results.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      active = (active + 1) % results.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      active = (active - 1 + results.length) % results.length;
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = results[active] ?? results[0];
      if (target) choose(target);
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/60 animate-in fade-in-0" />
    <Dialog.Content
      class="fixed left-1/2 top-[12vh] z-50 w-[min(92vw,40rem)] -translate-x-1/2 overflow-hidden rounded-xl border bg-card shadow-2xl animate-in fade-in-0 zoom-in-95"
      onkeydown={onkeydown}
    >
      <Dialog.Title class="sr-only">Search notes</Dialog.Title>

      <div class="flex items-center gap-2 border-b px-3">
        <SearchIcon class="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          bind:this={input}
          bind:value={q}
          placeholder="Search notes…"
          aria-label="Search notes"
          class="h-12 flex-1 border-0 bg-transparent text-base outline-none placeholder:text-muted-foreground"
          onkeydown={onkeydown}
        />
        {#if loading}
          <Loader2 class="h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
        {/if}
        <button
          class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          onclick={() => search.hide()}
          aria-label="Close search"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="max-h-[60vh] overflow-y-auto scrollbar-thin p-1">
        {#if !q.trim()}
          <p class="px-3 py-6 text-center text-sm text-muted-foreground">
            Type to search titles and note text.
          </p>
        {:else if loading && results.length === 0}
          <p class="px-3 py-6 text-center text-sm text-muted-foreground">Searching…</p>
        {:else if results.length === 0}
          <p class="px-3 py-6 text-center text-sm text-muted-foreground">
            No notes match “{q}”.
          </p>
        {:else}
          <ul>
            {#each results as n, i (n.id)}
              <li>
                <button
                  class="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm transition-colors"
                  class:bg-accent={i === active}
                  onmouseenter={() => (active = i)}
                  onclick={() => choose(n)}
                >
                  <span class="min-w-0 flex-1 truncate">{n.title || "(untitled)"}</span>
                  <span class="flex shrink-0 items-center gap-1">
                    {#each n.tags.slice(0, 2) as t (t.id)}
                      <TagPill name={t.name} color={t.color} class="px-1.5 py-0 text-[10px]" />
                    {/each}
                  </span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="flex items-center gap-3 border-t px-3 py-1.5 text-[11px] text-muted-foreground">
        <span>↑↓ navigate</span>
        <span>↵ open</span>
        <span>esc close</span>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
