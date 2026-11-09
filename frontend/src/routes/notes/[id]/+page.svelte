<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { Eye, ImagePlus, Loader2, PenLine, Plus } from "lucide-svelte";
  import { DropdownMenu } from "bits-ui";
  import { api, ApiError, type Note, type TagsResponse } from "$lib/api";
  import { createNoteStore, notes, sidebarNotes, tags, tree } from "$lib/stores.svelte";
  import { showToast } from "$lib/toast.svelte";
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";
  import TagPill from "$lib/TagPill.svelte";
  import NoteActions from "$lib/NoteActions.svelte";
  import MarkdownEditor from "$lib/MarkdownEditor.svelte";
  import MarkdownPreview from "$lib/MarkdownPreview.svelte";

  const id = $derived($page.params.id!);
  const store = createNoteStore();

  let body = $state("");
  let dirty = $state(false);
  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let addError = $state<string | null>(null);

  let previewOpen = $state(false);
  let editor = $state<{ insert: (text: string) => void } | null>(null);
  let fileInput = $state<HTMLInputElement | null>(null);

  // The title/tag header floats over the editor. Measure it so the editor's
  // first line clears the overlay even when tags wrap onto more rows. Keep a
  // minimum fade band on desktop, where the header is a single short row.
  let headerHeight = $state(0);
  const fadeStart = $derived(Math.max(headerHeight, 64));
  const fadeEnd = $derived(fadeStart + 48);

  onMount(() => {
    if (!tags.loaded) void tags.load();
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    previewOpen = desktop && localStorage.getItem("bunko.preview-open") !== "0";
    return () => store.dispose();
  });

  // onMount fires once, so clicking another note in the sidebar changed the
  // URL without refetching. Track the route id instead.
  $effect(() => {
    const current = id;
    if (current) void store.load(current);
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

  // A tagging failure is transient UI feedback, not note content. Toast once
  // per note visit instead of pinning the provider error under the tags. The
  // small "tagging failed" chip and its title remain for reference.
  let toastedFailureFor: string | null = null;
  $effect(() => {
    const note = store.note;
    if (!note) {
      toastedFailureFor = null;
      return;
    }
    if (status === "failed" && toastedFailureFor !== note.id) {
      toastedFailureFor = note.id;
      showToast(errorText || "Tagging failed.", "error");
    } else if (status !== "failed") {
      toastedFailureFor = null;
    }
  });

  /** Mirror a tag response into the note view and every cached copy of it. */
  function applyTags(r: TagsResponse) {
    store.setTags(r);
    const note = store.note;
    if (!note) return;

    const withTags = (n: Note): Note => ({
      ...n,
      tags: r.tags,
      tag_status: r.tag_status,
      tag_error: r.tag_error,
    });

    store.setNote(withTags(note));
    notes.patch(note.id, withTags);
    sidebarNotes.patch(note.id, withTags);
    tree.patch(note.id, withTags);
    void tags.load();
  }

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
      tree.patch(updated.id, () => updated);
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
      applyTags(r);
    } catch (e) {
      addError = e instanceof ApiError && e.status === 400 ? "That tag does not exist." : "Could not add tag.";
    }
  }

  async function removeTag(tagId: string) {
    if (!store.note) return;
    const r = await api.removeNoteTag(store.note.id, tagId);
    applyTags(r);
  }

  function togglePreview() {
    previewOpen = !previewOpen;
    localStorage.setItem("bunko.preview-open", previewOpen ? "1" : "0");
  }

  async function uploadImage(file: File): Promise<string> {
    const result = await api.uploadMedia(file);
    return result.markdown;
  }

  function openFilePicker() {
    fileInput?.click();
  }

  async function onFilePicked(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;

    const targetEditor = editor;
    const targetNoteId = store.note?.id;
    try {
      const markdown = await uploadImage(file);
      if (store.note?.id !== targetNoteId) return;
      targetEditor?.insert(markdown);
      if (previewOpen && window.matchMedia("(max-width: 1023px)").matches) {
        togglePreview();
      }
    } catch {
      showToast("Image upload failed.", "error");
    }
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
  <div
    class="relative flex min-h-0 w-full flex-1 flex-col"
    style="background-color: hsl(var(--note-bg))"
  >
    <!--
      Title, tags and actions float over the editor like OpenWebUI's chat
      navbar. A solid-to-transparent gradient sits under them so scrolled note
      text fades out before it can overlap the title.
    -->
    <div bind:clientHeight={headerHeight} class="pointer-events-none absolute inset-x-0 top-0 z-20">
      <!-- Opaque under the title, then a short fade into the note text. -->
      <div
        class="pointer-events-none absolute inset-x-0 top-0"
        style="height: {fadeEnd}px; background: linear-gradient(to bottom, hsl(var(--note-bg)) 0px, hsl(var(--note-bg)) {fadeStart}px, transparent {fadeEnd}px)"
      ></div>

      <div class="pointer-events-auto relative pl-14 pr-4 pt-3 md:px-8">
        <div class="flex items-start gap-2 pb-2">
          <div class="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1.5">
            <h1 class="min-w-0 max-w-[55%] shrink truncate text-base font-normal tracking-tight text-foreground/90">
              {n.title || "(untitled)"}
            </h1>

            <div class="flex min-w-0 flex-wrap items-center gap-1.5">
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
          </div>

          <div class="flex shrink-0 items-center gap-1">
            <button
              type="button"
              class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              onclick={openFilePicker}
              aria-label="Insert image"
              title="Insert image"
            >
              <ImagePlus class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              onclick={togglePreview}
              aria-label={previewOpen ? "Show editor" : "Show preview"}
              title={previewOpen ? "Show editor" : "Show preview"}
            >
              {#if previewOpen}
                <PenLine class="h-4 w-4" />
                <span class="hidden sm:inline">Hide preview</span>
                <span class="sm:hidden">Write</span>
              {:else}
                <Eye class="h-4 w-4" />
                <span>Preview</span>
              {/if}
            </button>
            <NoteActions
              note={n}
              align="end"
              onDeleted={() => goto("/")}
              class="-mr-1.5 shrink-0"
            />
          </div>
        </div>

        {#if addError}
          <p class="pb-2 text-sm text-red-400">{addError}</p>
        {/if}
      </div>
    </div>

    <div class="relative flex min-h-0 flex-1">
      <div class={cn("relative flex min-h-0 flex-1 flex-col", previewOpen && "hidden lg:flex")}>
        {#key n.id}
          <MarkdownEditor
            bind:this={editor}
            value={body}
            onchange={(value) => {
              body = value;
              dirty = true;
            }}
            onblur={() => void maybeSave()}
            onsave={() => void maybeSave()}
            onupload={uploadImage}
            padTop={fadeEnd + 8}
            padBottom={64}
            placeholder="Write something…"
            ariaLabel="Note body"
          />
        {/key}
      </div>

      {#if previewOpen}
        <div
          class="relative flex min-h-0 flex-1 overflow-hidden lg:w-[42%] lg:max-w-[42%] lg:flex-none lg:border-l lg:border-border/60"
        >
          <div
            class="scrollbar-thin h-full w-full overflow-y-auto overscroll-contain"
            style="padding-top: {fadeEnd + 8}px; padding-bottom: 64px"
          >
            <div class="px-4 md:px-8">
              <MarkdownPreview source={body} />
            </div>
          </div>
        </div>
      {/if}

      <!-- Match the top fade at the bottom, above the status bar. -->
      <div
        class="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-12"
        style="background: linear-gradient(to top, hsl(var(--note-bg)) 0px, hsl(var(--note-bg) / 0.8) 50%, transparent 100%)"
      ></div>
    </div>

    <input
      bind:this={fileInput}
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp"
      class="hidden"
      onchange={onFilePicked}
    />

    <div class="flex min-h-11 items-center gap-3 px-4 md:px-8 pt-2 pb-6 text-sm text-muted-foreground">
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
