<script lang="ts">
  import { DropdownMenu } from "bits-ui";
  import { Download, MoreHorizontal, Pencil, Trash2 } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import type { Note } from "$lib/api";
  import { api } from "$lib/api";
  import { downloadNote } from "$lib/download";

  let {
    note,
    onDeleted,
    onRename,
    onNavigateAway,
    align = "end",
    class: className,
  }: {
    note: Note;
    onDeleted?: () => void;
    onRename?: (note: Note) => void;
    onNavigateAway?: () => void;
    align?: "start" | "end";
    class?: string;
  } = $props();

  let open = $state(false);

  async function remove() {
    if (!confirm(`Delete “${note.title || "this note"}”?`)) return;
    await api.deleteNote(note.id);
    onDeleted?.();
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
        class="flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground"
        onSelect={() => {
          downloadNote(note);
          onNavigateAway?.();
        }}
      >
        <Download class="h-4 w-4" /> Download
      </DropdownMenu.Item>

      <DropdownMenu.Item
        class="flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground"
        onSelect={() => onRename?.(note)}
      >
        <Pencil class="h-4 w-4" /> Change title
      </DropdownMenu.Item>

      <DropdownMenu.Separator class="-mx-1 my-1 h-px bg-border" />

      <DropdownMenu.Item
        class="flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-400 outline-none data-[highlighted]:bg-red-500/15 data-[highlighted]:text-red-300"
        onSelect={() => void remove()}
      >
        <Trash2 class="h-4 w-4" /> Delete
      </DropdownMenu.Item>
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
</DropdownMenu.Root>
