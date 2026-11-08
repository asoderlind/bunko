<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { Loader2, Plus } from "lucide-svelte";
  import { DropdownMenu } from "bits-ui";
  import { api, ApiError } from "$lib/api";
  import { createNoteStore, notes, sidebarNotes, tags } from "$lib/stores.svelte";
  import { tagStyle } from "$lib/tag-colors";
  import TagPill from "$lib/TagPill.svelte";
  import NoteActions from "$lib/NoteActions.svelte";
  import { header } from "$lib/header.svelte";

  const id = $derived($page.params.id!);
  const store = createNoteStore();

  let body = $state("");
  let dirty = $state(false);
  let focused = $state(false);
  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let addError = $state<string | null>(null);

  onMount(() => {
    if (!tags.loaded) void tags.load();
    return () => store.dispose();
  });

  // onMount fires once, so clicking another note in the sidebar changed the
  // URL without refetching. Track the route id instead.
  $effect(() => {
    const current = id;
    if (current) void store.load(current);
  });

  // Put this note's title in the shell's top bar.
  $effect(() => {
    const n = store.note;
    header.set(n ? n.title || "(untitled)" : "");
    return () => header.clear();
  });

  // Reset the editor when the route changes to a different note.
  let lastId: string | null = null;
  $effect(() => {
    if (store.note && store.note.id !== lastId) {
      lastId = store.note.id;
      body = store.note.body_md;
      dirty = false;
    }
  });

  const status = $derived(store.tagsState?.tag_status ?? store.note?.tag_status ?? "pending");
  const errorText = $derived(store.tagsState?.tag_error ?? store.note?.tag_error ?? "");
  const chips = $derived(store.tagsState?.tags ?? store.note?.tags ?? []);
  const tagging = $derived(status === "pending" || status === "processing");
  const known = $derived(new Set(chips.map((c) => c.slug)));
  const available = $derived(tags.items.filter((t) => !known.has(t.slug)));

  /** Save the body if it changed. Never touches the title. */
  async function maybeSave() {
    const current = store.note;
    if (!current || !dirty || !body.trim()) return;
    saving = true;
    saveError = null;
    try {
      const updated = await api.updateNote(current.id, { body_md: body });
      store.setNote(updated);
      store.setTags({
        tag_status: updated.tag_status,
        tag_error: updated.tag_error,
        tags: updated.tags,
      });
      notes.patch(updated.id, () => updated);
      sidebarNotes.patch(updated.id, () => updated);
      dirty = false;
      void store.load(updated.id);
    } catch {
      saveError = "Could not save.";
    } finally {
      saving = false;
    }
  }

  async function addTag(slug: string) {
    if (!store.note) return;
    addError = null;
    try {
      const r = await api.addNoteTag(store.note.id, slug);
      store.setTags(r);
      void tags.load();
    } catch (e) {
      addError = e instanceof ApiError && e.status === 400 ? "That tag does not exist." : "Could not add tag.";
    }
  }

  async function removeTag(tagId: string) {
    if (!store.note) return;
    const r = await api.removeNoteTag(store.note.id, tagId);
    store.setTags(r);
    void tags.load();
  }
</script>

{#if store.loading && !store.note}
  <div class="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
    <Loader2 class="h-4 w-4 animate-spin" /> Loading…
  </div>
{:else if !store.note}
  <div class="mx-auto max-w-3xl p-5 text-sm text-red-400">
    {store.error ?? "Note not found."}
  </div>
{:else}
  {@const n = store.note}
  <div class="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 pb-4 pt-3">
    <!-- Top row: actions menu on the right. -->
    <div class="mb-3 flex items-start justify-between gap-2">
      <div class="flex flex-wrap items-center gap-1.5">
        {#if tagging}
          <span class="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            <Loader2 class="h-3 w-3 animate-spin" /> tagging…
          </span>
        {:else if status === "failed"}
          <span class="rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-300" title={errorText}>
            tagging failed
          </span>
        {/if}

        {#each chips as t (t.id)}
          <TagPill name={t.name} color={t.color} class="gap-0.5 py-0.5 pl-2.5 pr-1">
            <button
              class="ml-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full opacity-60 hover:opacity-100"
              aria-label={`Remove ${t.name}`}
              onclick={() => void removeTag(t.tag_id)}
            >
              ×
            </button>
          </TagPill>
        {/each}

        {#if !tagging && available.length > 0}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger
              class="inline-flex h-7 items-center gap-1 rounded-full border border-dashed border-muted-foreground/40 px-2.5 text-xs text-muted-foreground transition-colors hover:border-muted-foreground/70 hover:text-foreground"
              aria-label="Add tag"
            >
              <Plus class="h-3 w-3" /> tag
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="start"
                sideOffset={4}
                class="z-50 min-w-40 overflow-hidden rounded-md border bg-card p-1 shadow-md animate-in fade-in-0"
              >
                {#each available as t (t.id)}
                  <DropdownMenu.Item
                    class="flex min-h-9 cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent"
                    onSelect={() => void addTag(t.slug)}
                  >
                    <span class={`h-2 w-2 shrink-0 rounded-full ${tagStyle(t.color).dot}`}></span>
                    {t.name}
                  </DropdownMenu.Item>
                {/each}
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        {/if}
      </div>

      <!-- Note view: download only. Title, folder and delete live in the sidebar. -->
      <div class="flex shrink-0 items-center gap-1">
        <NoteActions note={n} align="end" compact />
      </div>
    </div>

    {#if addError}
      <p class="mb-2 text-sm text-red-400">{addError}</p>
    {/if}
    {#if status === "failed" && errorText}
      <p class="mb-2 text-sm text-muted-foreground">{errorText}</p>
    {/if}

    <textarea
      bind:value={body}
      oninput={() => (dirty = true)}
      onfocus={() => (focused = true)}
      onblur={() => void maybeSave()}
      spellcheck="false"
      aria-label="Note body"
      placeholder="Write something…"
      class="min-h-40 w-full flex-1 resize-none border-0 bg-transparent p-0 text-[16px] leading-relaxed outline-none placeholder:text-muted-foreground/50"
    ></textarea>

    <div class="flex min-h-11 items-center gap-3 border-t pt-2 text-sm text-muted-foreground">
      {#if saving}
        Saving…
      {:else if saveError}
        <span class="text-red-400">{saveError}</span>
      {:else if dirty}
        Edited — saving when you leave the field
      {:else}
        Saved
      {/if}
      <span class="ml-auto text-xs">Editing re-tags the note</span>
    </div>
  </div>

{/if}
