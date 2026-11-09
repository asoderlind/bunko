<script lang="ts">
  import { DropdownMenu } from "bits-ui";
  import { MoreHorizontal, Pencil, Trash2 } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import type { Folder } from "$lib/api";

  let {
    folder,
    onRename,
    onDelete,
    class: className,
  }: {
    folder: Folder;
    onRename: (folder: Folder) => void;
    onDelete: (folder: Folder) => void;
    class?: string;
  } = $props();

  let open = $state(false);

  const itemClass =
    "flex min-h-9 cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground";

  async function remove() {
    if (!confirm(`Delete folder "${folder.name}"? Notes inside will become unfiled.`)) return;
    await onDelete(folder);
  }
</script>

<DropdownMenu.Root bind:open>
  <DropdownMenu.Trigger
    class={cn(
      "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
      className
    )}
    aria-label={`Actions for ${folder.name}`}
  >
    <MoreHorizontal class="h-4 w-4" />
  </DropdownMenu.Trigger>

  <DropdownMenu.Portal>
    <DropdownMenu.Content
      align="end"
      sideOffset={4}
      class="z-50 min-w-44 overflow-hidden rounded-md border bg-card p-1 text-card-foreground shadow-md animate-in fade-in-0 data-[state=open]:zoom-in-95"
    >
      <DropdownMenu.Item class={itemClass} onSelect={() => onRename(folder)}>
        <Pencil class="h-4 w-4" /> Rename
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
