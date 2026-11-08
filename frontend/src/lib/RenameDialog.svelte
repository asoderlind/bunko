<script lang="ts">
  import { Dialog } from "bits-ui";
  import { Loader2 } from "lucide-svelte";
  import type { Note } from "$lib/api";
  import { api } from "$lib/api";
  import { notes, sidebarNotes } from "$lib/stores.svelte";

  let {
    note,
    open = $bindable(false),
    onSaved,
  }: {
    note: Note | null;
    open?: boolean;
    onSaved?: (n: Note) => void;
  } = $props();

  let title = $state("");
  let saving = $state(false);

  // Reset the field whenever a different note is opened.
  $effect(() => {
    if (open && note) title = note.title;
  });

  async function save() {
    if (!note) return;
    saving = true;
    try {
      const updated = await api.updateNote(note.id, { title: title.trim() });
      notes.patch(note.id, () => updated);
      sidebarNotes.patch(note.id, () => updated);
      onSaved?.(updated);
      open = false;
    } finally {
      saving = false;
    }
  }
</script>

<Dialog.Root bind:open>
  <Dialog.Portal>
    <Dialog.Overlay
      class="fixed inset-0 z-50 bg-black/70 animate-in fade-in-0"
    />
    <Dialog.Content
      class="fixed bottom-0 left-0 right-0 z-50 grid gap-4 rounded-t-2xl border bg-card p-5 shadow-lg animate-in slide-in-from-bottom-4 sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:slide-in-from-bottom-0"
    >
      <div class="flex flex-col space-y-1.5">
        <Dialog.Title class="text-lg font-semibold leading-none tracking-tight">
          Change title
        </Dialog.Title>
        <Dialog.Description class="text-sm text-muted-foreground">
          A title you set is kept when the note is re-tagged.
        </Dialog.Description>
      </div>

      <input
        bind:value={title}
        onkeydown={(e) => e.key === "Enter" && void save()}
        placeholder="Title"
        aria-label="Title"
        maxlength={200}
        class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />

      <div class="flex gap-2">
        <button
          onclick={() => void save()}
          disabled={saving}
          class="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {#if saving}<Loader2 class="h-4 w-4 animate-spin" />{/if}
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onclick={() => (open = false)}
          class="inline-flex h-11 items-center rounded-md px-4 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          Cancel
        </button>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
