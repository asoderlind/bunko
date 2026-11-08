<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { Loader2, Plus } from "lucide-svelte";
  import { DropdownMenu } from "bits-ui";
  import { api, ApiError } from "$lib/api";
  import { createNoteStore, notes, sidebarNotes, tags } from "$lib/stores.svelte";
  import { tagStyle } from "$lib/tag-colors";
  import TagPill from "$lib/TagPill.svelte";
  import NoteActions from "$lib/NoteActions.svelte";
  import RenameDialog from "$lib/RenameDialog.svelte";

  const id = $derived($page.params.id!);
  const store = createNoteStore();

  let editing = $state(false);
  let body = $state("");
  let title = $state("");
  let saving = $state(false);
  let addError = $state<string | null>(null);
  let renameOpen = $state(false);

  onMount(() => {
    void store.load(id);
    if (!tags.loaded) void tags.load();
    return () => store.dispose();
  });

  // Reset the editor when the route changes to a different note.
  let lastId: string | null = null;
  $effect(() => {
    if (store.note && store.note.id !== lastId) {
      lastId = store.note.id;
      body = store.note.body_md;
      title = store.note.title;
      editing = false;
    }
  });

  const status = $derived(store.tagsState?.tag_status ?? store.note?.tag_status ?? "pending");
  const errorText = $derived(store.tagsState?.tag_error ?? store.note?.tag_error ?? "");
  const chips = $derived(store.tagsState?.tags ?? store.note?.tags ?? []);
  const tagging = $derived(status === "pending" || status === "processing");
  const known = $derived(new Set(chips.map((c) => c.slug)));
  const available = $derived(tags.items.filter((t) => !known.has(t.slug)));

  async function save() {
    const current = store.note;
    if (!current || !body.trim()) return;
    saving = true;
    try {
      const patch: Record<string, string> = { body_md: body };
      if (title.trim() !== current.title) patch.title = title.trim();
      const updated = await api.updateNote(current.id, patch as never);
      store.setNote(updated);
      store.setTags({ tag_status: updated.tag_status, tag_error: updated.tag_error, tags: updated.tags });
      notes.patch(updated.id, () => updated);
      sidebarNotes.patch(updated.id, () => updated);
      editing = false;
      void store.load(updated.id);
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
  <div class="mx-auto w-full max-w-3xl px-4 py-4">
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

      <NoteActions
        note={n}
        align="end"
        class="shrink-0"
        onRename={() => (renameOpen = true)}
        onDeleted={() => {
          void sidebarNotes.query();
          void goto("/");
        }}
      />
    </div>

    {#if addError}
      <p class="mb-2 text-sm text-red-400">{addError}</p>
    {/if}
    {#if status === "failed" && errorText}
      <p class="mb-2 text-sm text-muted-foreground">{errorText}</p>
    {/if}

    {#if editing}
      <div class="space-y-3">
        <div>
          <input
            bind:value={title}
            placeholder="Title"
            aria-label="Title"
            maxlength={200}
            class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <p class="mt-1 text-xs text-muted-foreground">
            {n.title_source === "user"
              ? "Your title is kept when the note is re-tagged."
              : "Leave empty to let the title be generated from the note."}
          </p>
        </div>
        <textarea
          bind:value={body}
          class="min-h-[45vh] w-full resize-y rounded-md border border-input bg-background px-3 py-3 text-[16px] leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        ></textarea>
        <div class="flex items-center gap-2">
          <button
            onclick={() => void save()}
            disabled={saving || !body.trim()}
            class="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            onclick={() => {
              body = n.body_md;
              title = n.title;
              editing = false;
            }}
            class="inline-flex h-11 items-center rounded-md px-4 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            Cancel
          </button>
          <span class="text-sm text-muted-foreground">Editing re-tags the note</span>
        </div>
      </div>
    {:else}
      <button
        type="button"
        class="mb-1 block w-full cursor-text border-0 bg-transparent p-0 text-left text-lg font-semibold tracking-tight"
        onclick={() => (editing = true)}
        aria-label="Edit note"
      >
        {n.title || "(untitled)"}
      </button>
      <button
        type="button"
        class="block w-full cursor-text border-0 bg-transparent p-0 text-left"
        onclick={() => (editing = true)}
        aria-label="Edit note body"
      >
        <pre
          class="whitespace-pre-wrap break-words pb-10 pt-1 font-[inherit] text-[16px] leading-relaxed"
        >{n.body_md}</pre>
      </button>
    {/if}
  </div>

  <RenameDialog
    note={n}
    bind:open={renameOpen}
    onSaved={(updated) => store.setNote(updated)}
  />
{/if}
