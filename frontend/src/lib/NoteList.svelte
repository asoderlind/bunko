<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { Loader2 } from "lucide-svelte";
  import { folders, notes, sidebarNotes, tags } from "$lib/stores.svelte";
  import TagPill from "$lib/TagPill.svelte";
  import NoteActions from "$lib/NoteActions.svelte";
  import RenameDialog from "$lib/RenameDialog.svelte";
  import type { Note } from "$lib/api";

  let { inbox = false }: { inbox?: boolean } = $props();

  let renaming = $state<Note | null>(null);
  let renameOpen = $state(false);

  const q = $derived($page.url.searchParams.get("q") ?? "");
  // Tag filtering lives in the sidebar; keep URL tags working for deep links.
  const tagFilter = $derived($page.url.searchParams.getAll("tag"));
  const folderFilter = $derived($page.url.searchParams.get("folder") ?? "");

  onMount(() => {
    void tags.load();
  });

  // Refetch whenever the filters change.
  // Reactive on the URL params, so toggling filters feels instant: only the
  // list refetches, the shell and sidebar stay mounted.
  $effect(() => {
    const filter = {
      q: q || undefined,
      tag: tagFilter.length ? tagFilter : undefined,
      tag_status: inbox ? "done" : undefined,
      folder: folderFilter || undefined,
    };
    void notes.query(filter);
  });

  const shown = $derived(
    inbox ? notes.items.filter((n) => n.tags.length === 0) : notes.items
  );
  const folderName = $derived(
    folderFilter ? (folders.items.find((f) => f.id === folderFilter)?.name ?? "") : ""
  );
  const heading = $derived(
    inbox
      ? "Needs tags"
      : q
        ? `Search: ${q}`
        : folderName
          ? folderName
          : folderFilter === "unfiled"
            ? "Unfiled"
            : "All notes"
  );
</script>

<div class="mx-auto w-full max-w-3xl px-4 py-5">
  <div class="mb-4 flex items-center justify-between gap-3">
    <h1 class="text-xl font-semibold tracking-tight">{heading}</h1>
    {#if tagFilter.length}
      <span class="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
        {tagFilter.join(" + ")}
      </span>
    {/if}
  </div>

  {#if notes.loading}
    <div class="flex items-center gap-2 py-6 text-sm text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" /> Loading…
    </div>
  {:else if notes.error}
    <p class="py-6 text-sm text-red-400">{notes.error}</p>
  {:else if shown.length === 0}
    <p class="py-6 text-sm text-muted-foreground">
      {inbox ? "Nothing waiting for tags." : q ? "No matches." : "No notes yet."}
    </p>
  {:else}
    <ul class="divide-y">
      {#each shown as n (n.id)}
        <li class="group/row flex items-center gap-2">
          <a
            href={`/notes/${n.id}`}
            class="block min-w-0 flex-1 py-3.5 transition-colors hover:bg-accent/40"
          >
            <span class="block truncate">{n.title || "(untitled)"}</span>
            <span class="mt-1.5 flex flex-wrap items-center gap-1.5">
              {#if n.tag_status === "pending" || n.tag_status === "processing"}
                <span class="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">tagging…</span>
              {:else if n.tag_status === "failed"}
                <span class="rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-300">failed</span>
              {/if}
              {#each n.tags as t (t.id)}
                <TagPill name={t.name} color={t.color} />
              {/each}
              <span class="text-xs text-muted-foreground/70">
                {new Date(n.updated_at).toLocaleDateString()}
              </span>
            </span>
          </a>
          <NoteActions
            note={n}
            onDeleted={() => void notes.query({ q: q || undefined, tag: tagFilter.length ? tagFilter : undefined, tag_status: inbox ? "done" : undefined })}
            onRename={(note) => {
              renaming = note;
              renameOpen = true;
            }}
            class="opacity-0 group-hover/row:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
          />
        </li>
      {/each}
    </ul>
  {/if}
</div>

<RenameDialog note={renaming} bind:open={renameOpen} />
