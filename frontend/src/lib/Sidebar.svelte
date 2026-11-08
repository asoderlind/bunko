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
  import { api } from "$lib/api";
  import { auth, folders, sidebarNotes, tags } from "$lib/stores.svelte";
  import { search } from "$lib/search.svelte";
  import TagPill from "./TagPill.svelte";
  import NoteActions from "./NoteActions.svelte";

  let { onNavigate }: { onNavigate?: () => void } = $props();

  let filterOpen = $state(false);
  let creatingFolder = $state(false);
  let newFolderName = $state("");
  let folderBusy = $state(false);

  const NAV = [
    { href: "/", label: "New note", icon: NotebookPen },
    { href: "/inbox", label: "Needs tags", icon: Inbox },
    { href: "/tags", label: "Tags", icon: TagIcon },
  ];

  // Sidebar filter state is local: it narrows the note list *in the sidebar*
  // rather than navigating to a separate view.
  let selectedTags = $state<string[]>([]);
  let activeFolder = $state<string | null>(null);

  const scopedNotes = $derived(sidebarNotes.items);
  const hasFilters = $derived(selectedTags.length > 0 || activeFolder !== null);

  /** Re-query the sidebar list from the current filter state. */
  function refreshSidebar() {
    void sidebarNotes.applyFilters({
      tag: selectedTags.length ? selectedTags : undefined,
      folder: activeFolder ?? undefined,
      limit: 10,
    } as never);
  }

  function toggleTag(slug: string) {
    selectedTags = selectedTags.includes(slug)
      ? selectedTags.filter((s) => s !== slug)
      : [...selectedTags, slug];
    refreshSidebar();
  }

  /**
   * Clicking a folder scopes the note list to it (Open WebUI behaviour);
   * clicking it again clears the scope and shows everything.
   */
  function selectFolder(id: string | null) {
    activeFolder = activeFolder === id ? null : id;
    refreshSidebar();
  }

  function clearFilters() {
    selectedTags = [];
    activeFolder = null;
    refreshSidebar();
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
    if (!sidebarNotes.loadedOnce) {
      sidebarNotes.loadedOnce = true;
      void sidebarNotes.query();
    }
    if (!tags.loaded) void tags.load();
    if (!folders.loaded) void folders.load();
  });
</script>

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

      <!-- Folders: all top-level, no parent container item -->
      <div class="pt-1">
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
          <div class="group/folder flex items-center rounded-md transition-colors">
            <button
              class={cn(
                "flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md px-2 text-sm transition-colors",
                activeFolder === folder.id
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
              aria-pressed={activeFolder === folder.id}
              onclick={() => selectFolder(folder.id)}
            >
              <FolderIcon class="h-4 w-4 shrink-0" />
              <span class="truncate">{folder.name}</span>
              <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">
                {folder.note_count}
              </span>
            </button>
          </div>
        {/each}

        {#if folders.items.length === 0 && !creatingFolder}
          <p class="px-2 py-1 text-xs text-muted-foreground">No folders yet.</p>
        {/if}
      </div>

      <!-- Tag filter -->
      <div class="px-1 pt-1">
        <button
          class="flex min-h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          aria-expanded={filterOpen}
          onclick={() => (filterOpen = !filterOpen)}
        >
          <Filter class="h-4 w-4 shrink-0" />
          <span>Filter</span>
          {#if selectedTags.length > 0}
            <span class="rounded-full bg-primary/20 px-1.5 text-xs text-primary">
              {selectedTags.length}
            </span>
          {/if}
          <ChevronDown
            class={cn(
              "ml-auto h-4 w-4 shrink-0 transition-transform duration-200",
              filterOpen && "rotate-180"
            )}
          />
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
                <input
                  type="checkbox"
                  class="sr-only"
                  {checked}
                  onchange={() => toggleTag(t.slug)}
                />
                <!-- Filled in the tag's colour when on; a plain outline when off. -->
                <span
                  class={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border-2 transition-colors",
                    checked
                      ? tagStyle(t.color).box
                      : "border-muted-foreground/50 bg-transparent"
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
    </nav>

    <div class="border-t px-3 pb-2 pt-2">
      <div class="flex items-center justify-between px-2 pb-1">
        <span class="truncate text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
          {#if activeFolder}
            {folders.items.find((f) => f.id === activeFolder)?.name ?? "Folder"}
          {:else if selectedTags.length}
            Filtered
          {:else}
            Recent notes
          {/if}
        </span>
        {#if hasFilters}
          <button
            onclick={clearFilters}
            class="text-xs text-muted-foreground hover:text-foreground"
          >
            Clear
          </button>
        {/if}
        <a
          href="/notes"
          onclick={onNavigate}
          class="ml-auto text-xs text-muted-foreground hover:text-foreground"
        >
          All
        </a>
      </div>

      {#if sidebarNotes.loading && scopedNotes.length === 0}
        <p class="px-2 py-1 text-xs text-muted-foreground">Loading…</p>
      {:else if scopedNotes.length === 0}
        <p class="px-2 py-1 text-xs text-muted-foreground">
          {hasFilters ? "No notes match these filters." : "No notes yet."}
        </p>
      {:else}
        <ul class="space-y-px">
          {#each scopedNotes as n (n.id)}
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
                onDeleted={() => void sidebarNotes.query()}
                class="mr-0.5 opacity-0 group-hover/row:opacity-100 focus-visible:opacity-100 data-[open]:opacity-100 [@media(hover:none)]:opacity-100"
              />
            </li>
          {/each}
        </ul>

        {#if sidebarNotes.hasMore}
          <button
            onclick={() => sidebarNotes.loadMore()}
            disabled={sidebarNotes.loadingMore}
            class="mt-1 flex min-h-9 w-full items-center justify-center gap-2 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground disabled:opacity-60"
          >
            {#if sidebarNotes.loadingMore}
              <Loader2 class="h-3 w-3 animate-spin" /> Loading…
            {:else}
              <ChevronDown class="h-3 w-3" />
              Load more ({scopedNotes.length} of {sidebarNotes.count})
            {/if}
          </button>
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
