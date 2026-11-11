<script lang="ts">
  import { Dialog, DropdownMenu } from "bits-ui";
  import {
    ChevronRight,
    Download,
    FolderInput,
    Loader2,
    Lock,
    MoreHorizontal,
    Pencil,
    RefreshCw,
    Trash2,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import type { Note } from "$lib/api";
  import { api } from "$lib/api";
  import { downloadNote } from "$lib/download";
  import { showToast } from "$lib/toast.svelte";
  import { folders, notes, providers, sidebarNotes, tags, tree } from "$lib/stores.svelte";

  let {
    note,
    onDeleted,
    onRename,
    onNavigateAway,
    onUpdated,
    align = "end",
    class: className,
    /** Note view uses the compact menu: download only. */
    compact = false,
  }: {
    note: Note;
    onDeleted?: () => void;
    onRename?: (note: Note) => void;
    onNavigateAway?: () => void;
    onUpdated?: (note: Note) => void;
    align?: "start" | "end";
    class?: string;
    compact?: boolean;
  } = $props();

  let open = $state(false);
  let deleteOpen = $state(false);
  let deleting = $state(false);
  let deleteError = $state<string | null>(null);
  let privacyChanging = $state(false);
  let retagging = $state(false);
  let generatingTitle = $state(false);
  const configuredProvider = $derived(providers.selected);
  const selectedProvider = $derived(providers.forNote(note.local_only));
  const canRetag = $derived(
    !!selectedProvider && (!note.local_only || selectedProvider.is_local)
  );

  const itemClass =
    "flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground";

  async function remove() {
    if (deleting) return;
    deleting = true;
    deleteError = null;
    try {
      await api.deleteNote(note.id);
      deleteOpen = false;
      onDeleted?.();
    } catch {
      deleteError = "Could not delete this note. Please try again.";
    } finally {
      deleting = false;
    }
  }

  async function moveTo(folderId: string | null) {
    const updated = await api.updateNote(note.id, { folder_id: folderId });
    // Keep every note list in sync immediately. The sidebar is rendered from
    // the tree store, while full-page lists use the other two stores.
    patchNote(updated);
    await folders.load();
  }

  function patchNote(updated: Note) {
    notes.patch(updated.id, () => updated);
    tree.patch(updated.id, () => updated);
    sidebarNotes.patch(updated.id, () => updated);
    onUpdated?.(updated);
  }

  async function waitForTagging(updated: Note) {
    let current = updated;
    while (current.tag_status === "pending" || current.tag_status === "processing") {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      try {
        const result = await api.getNoteTags(current.id);
        current = {
          ...current,
          ...(result.title !== undefined && result.title !== null
            ? { title: result.title }
            : {}),
          tags: result.tags,
          tag_status: result.tag_status,
          tag_error: result.tag_error,
        };
        patchNote(current);
      } catch {
        return;
      }
    }
    void tags.load();
  }

  async function retag() {
    if (!canRetag || retagging || generatingTitle) return;
    retagging = true;
    try {
      const updated = await api.retagNote(note.id);
      patchNote(updated);
      void providers.load();
      await waitForTagging(updated);
    } finally {
      retagging = false;
    }
  }

  async function togglePrivate() {
    if (privacyChanging) return;
    privacyChanging = true;
    try {
      const updated = await api.updateNote(note.id, { local_only: !note.local_only });
      patchNote(updated);
    } catch {
      showToast("Could not change privacy.", "error");
    } finally {
      privacyChanging = false;
    }
  }

  async function generateTitle() {
    if (!canRetag || retagging || generatingTitle) return;
    generatingTitle = true;
    try {
      const updated = await api.generateTitle(note.id);
      patchNote(updated);
      await waitForTagging(updated);
    } finally {
      generatingTitle = false;
    }
  }
</script>

<DropdownMenu.Root bind:open>
  <DropdownMenu.Trigger
    class={cn(
      "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
      className
    )}
    aria-label={`Actions for ${note.title || "note"}`}
  >
    <MoreHorizontal class="h-4 w-4" />
  </DropdownMenu.Trigger>

  <DropdownMenu.Portal>
    <DropdownMenu.Content
      {align}
      sideOffset={4}
      class="z-50 min-w-44 overflow-hidden rounded-md border bg-card p-1 text-card-foreground shadow-md animate-in fade-in-0 data-[state=open]:zoom-in-95"
    >
      <DropdownMenu.Item
        class={itemClass}
        onSelect={() => {
          downloadNote(note);
          onNavigateAway?.();
        }}
      >
        <Download class="h-4 w-4" /> Download
      </DropdownMenu.Item>

      {#if !compact}
        <DropdownMenu.Item class={itemClass} onSelect={() => onRename?.(note)}>
          <Pencil class="h-4 w-4" /> Change title
        </DropdownMenu.Item>

        <DropdownMenu.Item
          class={cn(itemClass, "disabled:pointer-events-none disabled:opacity-50")}
          onSelect={() => void togglePrivate()}
          disabled={privacyChanging}
        >
          <Lock class="h-4 w-4" />
          {privacyChanging ? "Updating privacy…" : note.local_only ? "Make non-private" : "Make private"}
        </DropdownMenu.Item>

        <DropdownMenu.Item
          class={cn(itemClass, "disabled:pointer-events-none disabled:opacity-50")}
          onSelect={() => void generateTitle()}
          disabled={!canRetag || retagging || generatingTitle}
        >
          <Pencil class={cn("h-4 w-4", generatingTitle && "animate-pulse")} />
          {#if generatingTitle}
            Generating title…
          {:else if !configuredProvider}
            Generate title (configure a provider first)
          {:else if !canRetag}
            Generate title (local provider required)
          {:else}
            Generate title with {selectedProvider?.label ?? "provider"}
          {/if}
        </DropdownMenu.Item>

        <DropdownMenu.Sub>
          <DropdownMenu.SubTrigger class={cn(itemClass, "justify-between")}>
            <span class="flex items-center gap-2">
              <FolderInput class="h-4 w-4" /> Move to
            </span>
            <ChevronRight class="h-3.5 w-3.5 opacity-60" />
          </DropdownMenu.SubTrigger>
          <DropdownMenu.Portal>
            <DropdownMenu.SubContent
              sideOffset={4}
              class="z-50 min-w-44 overflow-hidden rounded-md border bg-card p-1 text-card-foreground shadow-md animate-in fade-in-0"
            >
              <DropdownMenu.Item
                class={itemClass}
                onSelect={() => void moveTo(null)}
                disabled={!note.folder_id}
              >
                <span class="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/40"></span>
                No folder
              </DropdownMenu.Item>

              {#if folders.items.length === 0}
                <p class="px-2 py-1.5 text-xs text-muted-foreground">No folders yet.</p>
              {/if}

              {#each folders.rootFolders as f (f.id)}
                <DropdownMenu.Item
                  class={itemClass}
                  onSelect={() => void moveTo(f.id)}
                  disabled={note.folder_id === f.id}
                >
                  <span class="h-2 w-2 shrink-0 rounded-full bg-muted-foreground/40"></span>
                  <span class="truncate">{f.name}</span>
                </DropdownMenu.Item>
              {/each}
            </DropdownMenu.SubContent>
          </DropdownMenu.Portal>
        </DropdownMenu.Sub>

        <DropdownMenu.Separator class="-mx-1 my-1 h-px bg-border" />

        <DropdownMenu.Item
          class={cn(itemClass, "disabled:pointer-events-none disabled:opacity-50")}
          onSelect={() => void retag()}
          disabled={!canRetag || retagging}
        >
          <RefreshCw class={cn("h-4 w-4", retagging && "animate-spin")} />
          {#if retagging}
            Re-tagging…
          {:else if !configuredProvider}
            Re-tag (configure a provider first)
          {:else if !canRetag}
            Re-tag (local provider required)
          {:else}
            Re-tag with {selectedProvider?.label ?? "provider"}
          {/if}
        </DropdownMenu.Item>

        <DropdownMenu.Separator class="-mx-1 my-1 h-px bg-border" />

        <DropdownMenu.Item
          class="flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-400 outline-none data-[highlighted]:bg-red-500/15 data-[highlighted]:text-red-300"
          onSelect={() => {
            deleteError = null;
            deleteOpen = true;
          }}
        >
          <Trash2 class="h-4 w-4" /> Delete
        </DropdownMenu.Item>
      {/if}
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>

<Dialog.Root bind:open={deleteOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/70 backdrop-blur-[2px] animate-in fade-in-0" />
    <Dialog.Content
      class="fixed bottom-0 left-0 right-0 z-50 overflow-hidden rounded-t-2xl border bg-card p-5 shadow-2xl animate-in slide-in-from-bottom-4 sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:slide-in-from-bottom-0"
    >
      <div class="flex gap-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/15 text-red-400">
          <Trash2 class="h-5 w-5" />
        </div>
        <div class="min-w-0 space-y-1">
          <Dialog.Title class="text-lg font-semibold tracking-tight">
            Delete note?
          </Dialog.Title>
          <Dialog.Description class="text-sm leading-6 text-muted-foreground">
            This permanently deletes
            <span class="font-medium text-foreground">“{note.title || "Untitled note"}”</span>.
            This action cannot be undone.
          </Dialog.Description>
        </div>
      </div>

      {#if deleteError}
        <p class="mt-4 rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300">{deleteError}</p>
      {/if}

      <div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onclick={() => (deleteOpen = false)}
          disabled={deleting}
          class="inline-flex h-10 items-center justify-center rounded-md px-4 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={() => void remove()}
          disabled={deleting}
          class="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-red-600 px-4 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {#if deleting}<Loader2 class="h-4 w-4 animate-spin" />{/if}
          {deleting ? "Deleting…" : "Delete note"}
        </button>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
