<script lang="ts">
  import { DropdownMenu } from "bits-ui";
  import {
    ChevronRight,
    Download,
    FolderInput,
    MoreHorizontal,
    Pencil,
    Trash2,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import type { Note } from "$lib/api";
  import { api } from "$lib/api";
  import { downloadNote } from "$lib/download";
  import { folders, sidebarNotes, tree } from "$lib/stores.svelte";

  let {
    note,
    onDeleted,
    onRename,
    onNavigateAway,
    align = "end",
    class: className,
    /** Note view uses the compact menu: download only. */
    compact = false,
  }: {
    note: Note;
    onDeleted?: () => void;
    onRename?: (note: Note) => void;
    onNavigateAway?: () => void;
    align?: "start" | "end";
    class?: string;
    compact?: boolean;
  } = $props();

  let open = $state(false);

  const itemClass =
    "flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground";

  async function remove() {
    if (!confirm(`Delete “${note.title || "this note"}”?`)) return;
    await api.deleteNote(note.id);
    onDeleted?.();
  }

  async function moveTo(folderId: string | null) {
    const updated = await api.updateNote(note.id, { folder_id: folderId });
    // Keep every note list in sync immediately. The sidebar is rendered from
    // the tree store, while full-page lists use the other two stores.
    tree.patch(note.id, () => updated);
    sidebarNotes.patch(note.id, () => updated);
    await folders.load();
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
          class="flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-400 outline-none data-[highlighted]:bg-red-500/15 data-[highlighted]:text-red-300"
          onSelect={() => void remove()}
        >
          <Trash2 class="h-4 w-4" /> Delete
        </DropdownMenu.Item>
      {/if}
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>
