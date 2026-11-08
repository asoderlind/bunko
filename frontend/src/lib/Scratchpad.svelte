<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { sidebarNotes } from "$lib/stores.svelte";

  const DRAFT_KEY = "easy-notes.draft";

  let body = $state("");
  let saving = $state(false);
  let error = $state<string | null>(null);
  let textarea: HTMLTextAreaElement;

  onMount(() => {
    body = localStorage.getItem(DRAFT_KEY) || "";
    textarea?.focus();
  });

  $effect(() => {
    if (body) localStorage.setItem(DRAFT_KEY, body);
    else localStorage.removeItem(DRAFT_KEY);
  });

  async function save() {
    if (saving || !body.trim()) return;
    saving = true;
    error = null;
    try {
      const note = await api.createNote(body);
      localStorage.removeItem(DRAFT_KEY);
      body = "";
      void sidebarNotes.query();
      await goto(`/notes/${note.id}`);
    } catch {
      error = "Could not save. Your text is kept in this browser.";
    } finally {
      saving = false;
    }
  }

  function onkeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void save();
    }
  }
</script>

<div class="flex flex-1 flex-col">
  <textarea
    bind:this={textarea}
    bind:value={body}
    {onkeydown}
    placeholder="Write something…"
    spellcheck="false"
    aria-label="New note"
    class="min-h-0 flex-1 resize-none bg-transparent px-4 py-5 text-[17px] leading-relaxed outline-none placeholder:text-muted-foreground/60"
  ></textarea>

  {#if error}
    <p role="alert" class="px-4 pb-2 text-sm text-red-400">{error}</p>
  {/if}

  {#if body.trim()}
    <div class="sticky bottom-0 flex items-center gap-3 border-t bg-background px-4 py-2.5">
      <button
        onclick={() => void save()}
        disabled={saving}
        class="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <span class="text-sm text-muted-foreground">⌘/Ctrl + Enter</span>
    </div>
  {/if}
</div>
