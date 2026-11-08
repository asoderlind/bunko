<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api, type Note } from "$lib/api";
  import { header } from "$lib/header.svelte";
  import { tree } from "$lib/stores.svelte";

  /**
   * New-note composer. Same editing surface as the note view: a borderless
   * full-height textarea, autosaved. The note is created on the first keystroke
   * (so it appears in the sidebar) and then patched as you type, which means
   * tagging starts early and finishes sooner.
   */
  let body = $state("");
  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let textarea = $state<HTMLTextAreaElement | null>(null);

  // The note we have already created in this session, if any.
  let created: Note | null = null;
  let pending = $state(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    header.set(created ? created.title || "(untitled)" : "New note");
    return () => header.clear();
  });

  onMount(() => {
    textarea?.focus();
  });

  // The newest text seen, so a save that finishes mid-typing can follow up
  // with whatever arrived meanwhile instead of dropping those keystrokes.
  let latest = "";

  /** Create on first content, then patch. Debounced so typing stays smooth. */
  async function persist(value: string) {
    latest = value;
    if (!value.trim()) return;
    if (pending) return;

    pending = true;
    saving = true;
    saveError = null;
    try {
      // Loop until no newer text arrived while we were saving.
      let target = value;
      while (target.trim()) {
        if (!created) {
          created = await api.createNote(target);
          // The sidebar renders the tree, so refresh it: the note appears
          // immediately, while the editor keeps focus.
          void tree.query();
          // Swap the URL to the real note without remounting this editor.
          history.replaceState({}, "", `/notes/${created.id}`);
        } else {
          created = await api.updateNote(created.id, { body_md: target });
          tree.patch(created.id, () => created!);
        }
        if (latest === target) break;
        target = latest;
      }
    } catch {
      saveError = "Could not save.";
    } finally {
      pending = false;
      saving = false;
    }
  }

  function oninput() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void persist(body), 800);
  }

  function onblur() {
    if (timer) clearTimeout(timer);
    void persist(body);
  }

  function onkeydown(e: KeyboardEvent) {
    // ⌘/Ctrl+S saves immediately (creating the note if needed) and leaves the
    // editor open, so writing can continue without a page change.
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      if (timer) clearTimeout(timer);
      void persist(body);
    }
  }

  async function finish() {
    if (!body.trim()) return;
    if (!created) await persist(body);
    if (created) await goto(`/notes/${created.id}`, { replaceState: true });
  }
</script>

<div class="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 pb-4 pt-3">
  <textarea
    bind:this={textarea}
    bind:value={body}
    {oninput}
    {onblur}
    {onkeydown}
    spellcheck="false"
    aria-label="New note body"
    placeholder="Write something…"
    class="min-h-40 w-full flex-1 resize-none border-0 bg-transparent p-0 text-[16px] leading-relaxed outline-none placeholder:text-muted-foreground/50"
  ></textarea>

  <div class="flex min-h-11 items-center gap-3 border-t pt-2 text-sm text-muted-foreground">
    {#if saving}
      Saving…
    {:else if saveError}
      <span class="text-red-400">{saveError}</span>
    {:else if body.trim()}
      Saved
    {:else}
      Nothing to save yet
    {/if}
    {#if body.trim()}
      <button
        class="ml-auto text-xs text-muted-foreground hover:text-foreground"
        onclick={() => void finish()}
      >
        Open note
      </button>
    {:else}
      <span class="ml-auto text-xs">⌘/Ctrl + S</span>
    {/if}
  </div>
</div>
