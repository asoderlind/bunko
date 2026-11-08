<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import {
    ChevronDown,
    ChevronRight,
    Filter,
    Folder as FolderIcon,
    FolderPlus,
    Inbox,
    Layers,
    Loader2,
    LogOut,
    NotebookPen,
    Search,
    Tag as TagIcon,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";
  import { api, type Note } from "$lib/api";
  import { auth, folders, tags, tree } from "$lib/stores.svelte";
  import { search } from "$lib/search.svelte";
  import TagPill from "./TagPill.svelte";
  import NoteActions from "./NoteActions.svelte";

  let { onNavigate }: { onNavigate?: () => void } = $props();

  let filterOpen = $state(false);
  let creatingFolder = $state(false);
  let newFolderName = $state("");
  let folderBusy = $state(false);

  // Which folders are expanded, by id. Unfiled uses the empty string.
  let expanded = $state<Set<string>>(new Set());

  const NAV = [
    { href: "/", label: "New note", icon: NotebookPen },
    { href: "/inbox", label: "Needs tags", icon: Inbox },
    { href: "/tags", label: "Tags", icon: TagIcon },
  ];

  // Sidebar filter state is local: it narrows the note list *in the sidebar*
  // rather than navigating to a separate view.
  // Filters apply across every folder, so they live above the folder list.
  let selectedTags = $state<string[]>([]);

  const hasFilters = $derived(selectedTags.length > 0);

  /** Re-query the tree from the current filter state. */
  function refreshTree() {
    void tree.query({ tag: selectedTags.length ? selectedTags : undefined });
  }

  function toggleTag(slug: string) {
    selectedTags = selectedTags.includes(slug)
      ? selectedTags.filter((s) => s !== slug)
      : [...selectedTags, slug];
    refreshTree();
  }

  function clearFilters() {
    selectedTags = [];
    refreshTree();
  }

  /** Toggle a folder open/closed. The chevron and the name both do this. */
  function toggleExpanded(id: string) {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expanded = next;
  }

  async function createFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    folderBusy = true;
    try {
      await api.createFolder({ name });
      newFolderName = "";
      creatingFolder = false;
      await folders.load();
    } finally {
      folderBusy = false;
    }
  }

  async function toggleCollapse(id: string, collapsed: boolean) {
    await api.updateFolder(id, { collapsed: !collapsed });
    await folders.load();
  }

  function isActive(href: string) {
    const p = $page.url.pathname;
    return href === "/" ? p === "/" : p.startsWith(href);
  }

  onMount(() => {
    if (!tree.loaded) void tree.query();
    if (!tags.loaded) void tags.load();
    if (!folders.loaded) void folders.load();
  });
</script>

{#snippet noteRow(n: Note)}
  <li class="group/row flex items-center rounded-md transition-colors hover:bg-accent/50">
    <a
      href={`/notes/${n.id}`}
      onclick={onNavigate}
      title={n.title}
      class={cn(
        "flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-2 pr-1 text-sm transition-colors",
        $page.url.pathname === `/notes/${n.id}`
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground group-hover/row:text-foreground"
      )}
    >
      <span class="min-w-0 flex-1 truncate">{n.title || "(untitled)"}</span>
      <span class="flex shrink-0 items-center gap-1">
        {#each n.tags.slice(0, 2) as t (t.id)}
          <TagPill name={t.name} color={t.color} class="max-w-16 px-1.5 py-0 text-[10px]" />
        {/each}
        {#if n.tags.length > 2}
          <span class="text-[10px] text-muted-foreground/70">+{n.tags.length - 2}</span>
        {/if}
      </span>
    </a>
    <NoteActions
      note={n}
      onDeleted={() => refreshTree()}
      class="mr-0.5 opacity-0 group-hover/row:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
    />
  </li>
{/snippet}

<!--
  Bounded column: fixed header, ONE scrollable region (nav + folders + filter +
  notes), pinned footer. The filter lives inside the scroller so expanding it
  adds scrollable content instead of squeezing the note list away.
-->
<div class="flex h-full flex-col">
  <!-- Same height as the shell's bar so the two line up. -->
  <div class="flex h-14 shrink-0 items-center gap-1 border-b pl-4 pr-2">
    <div class="text-sm font-semibold tracking-tight text-muted-foreground">easy-notes</div>
    <button
      class="ml-auto inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      aria-label="Search"
      onclick={() => search.show()}
    >
      <Search class="h-4 w-4" />
    </button>
  </div>

  <div class="scrollbar-thin min-h-0 flex-1 overflow-y-auto overscroll-contain">
    <nav class="space-y-1 p-3 pt-2">
      {#each NAV as item (item.href)}
        <a
          href={item.href}
          onclick={onNavigate}
          class={cn(
            "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors",
            isActive(item.href)
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          )}
        >
          <item.icon class="h-4 w-4 shrink-0" />
          {item.label}
        </a>
      {/each}

      <!--
        Filter sits above the folder list because it narrows notes inside
        every folder, not just one.
      -->
      <div class="px-1 pt-1">
        <button
          class="flex min-h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          aria-expanded={filterOpen}
          onclick={() => (filterOpen = !filterOpen)}
        >
          <ChevronDown
            class={cn(
              "h-4 w-4 shrink-0 transition-transform duration-200",
              !filterOpen && "-rotate-90"
            )}
          />
          <Filter class="h-4 w-4 shrink-0" />
          <span>Filter</span>
          {#if selectedTags.length > 0}
            <span class="rounded-full bg-primary/20 px-1.5 text-xs text-primary">
              {selectedTags.length}
            </span>
          {/if}
        </button>

        {#if filterOpen}
          <div class="mt-1 space-y-0.5 pl-1 animate-in fade-in-0 slide-in-from-top-1">
            {#if tags.items.length === 0}
              <p class="px-2 py-1 text-xs text-muted-foreground">No tags yet.</p>
            {/if}
            {#each tags.items as t (t.id)}
              {@const checked = selectedTags.includes(t.slug)}
              <label
                class="flex min-h-9 cursor-pointer items-center gap-2 rounded-md px-2 text-sm hover:bg-accent/50"
              >
                <input type="checkbox" class="sr-only" {checked} onchange={() => toggleTag(t.slug)} />
                <!-- Filled in the tag's colour when on; a plain outline when off. -->
                <span
                  class={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border-2 transition-colors",
                    checked ? tagStyle(t.color).box : "border-muted-foreground/50 bg-transparent"
                  )}
                  aria-hidden="true"
                >
                  {#if checked}
                    <svg viewBox="0 0 24 24" class="h-3 w-3 text-white" fill="none">
                      <path
                        d="M20 6L9 17l-5-5"
                        stroke="currentColor"
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                  {/if}
                </span>
                <span class="truncate">{t.name}</span>
                <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">{t.note_count}</span>
              </label>
            {/each}
            {#if selectedTags.length > 0}
              <button
                onclick={clearFilters}
                class="mt-1 min-h-9 w-full rounded-md px-2 text-left text-xs text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              >
                Clear filters
              </button>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Folders: each expands to show its own notes as children. -->
      <div class="pt-2">
        <div class="flex items-center justify-between px-2 pb-1">
          <span class="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
            Folders
          </span>
          <button
            class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="New folder"
            onclick={() => (creatingFolder = !creatingFolder)}
          >
            <FolderPlus class="h-3.5 w-3.5" />
          </button>
        </div>

        {#if creatingFolder}
          <form
            class="mb-1 px-1"
            onsubmit={(e) => {
              e.preventDefault();
              void createFolder();
            }}
          >
            <input
              bind:value={newFolderName}
              placeholder="Folder name"
              aria-label="Folder name"
              class="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled={folderBusy}
            />
          </form>
        {/if}

        {#each folders.rootFolders as folder (folder.id)}
          {@const isOpen = expanded.has(folder.id)}
          {@const children = tree.inFolder(folder.id)}
          <div>
            <div class="flex items-center gap-0.5">
              <button
                class="inline-flex h-8 w-6 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
                aria-label={isOpen ? `Collapse ${folder.name}` : `Expand ${folder.name}`}
                aria-expanded={isOpen}
                onclick={() => toggleExpanded(folder.id)}
              >
                <ChevronRight
                  class={cn(
                    "h-3.5 w-3.5 transition-transform duration-200",
                    isOpen && "rotate-90"
                  )}
                />
              </button>
              <button
                class="flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
                onclick={() => toggleExpanded(folder.id)}
              >
                <FolderIcon class="h-4 w-4 shrink-0" />
                <span class="truncate">{folder.name}</span>
                <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">
                  {folder.note_count}
                </span>
              </button>
            </div>

            <!-- Animated height reveal, same technique as the filter. -->
            {#if isOpen}
              <div class="ms-3 animate-in fade-in-0 slide-in-from-top-1 border-s border-border/60 ps-1">
                {#each children as n (n.id)}
                  {@render noteRow(n)}
                {:else}
                  <p class="px-2 py-1 text-xs text-muted-foreground">Empty</p>
                {/each}
              </div>
            {/if}
          </div>
        {/each}

        {#if folders.items.length === 0 && !creatingFolder}
          <p class="px-2 py-1 text-xs text-muted-foreground">No folders yet.</p>
        {/if}
      </div>
    </nav>

    <!-- Unfiled notes: everything not in a folder. -->
    <div class="border-t px-3 pb-2 pt-2">
      <div class="flex items-center justify-between px-2 pb-1">
        <span class="truncate text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          {#if selectedTags.length}
            Filtered
          {:else}
            Recent notes
          {/if}
        </span>
        {#if selectedTags.length}
          <button onclick={clearFilters} class="text-xs text-muted-foreground hover:text-foreground">
            Clear
          </button>
        {/if}
      </div>

      {#if tree.loading && !tree.loaded}
        <p class="px-2 py-1 text-xs text-muted-foreground">Loading…</p>
      {:else}
        {@const loose = tree.inFolder(null)}
        {#if loose.length === 0}
          <p class="px-2 py-1 text-xs text-muted-foreground">
            {selectedTags.length ? "No notes match these filters." : "No notes yet."}
          </p>
        {:else}
          <ul class="space-y-px">
            {#each loose as n (n.id)}
              {@render noteRow(n)}
            {/each}
          </ul>
        {/if}
      {/if}
    </div>
  </div>

  <div class="shrink-0 border-t p-3">
    <button
      class="inline-flex min-h-11 w-full items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      onclick={() => auth.logout()}
    >
      <LogOut class="h-4 w-4" />
      Sign out
    </button>
  </div>
</div>
