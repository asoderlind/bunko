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
    Tag as TagIcon,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";
  import { api } from "$lib/api";
  import { auth, folders, sidebarNotes, tags } from "$lib/stores.svelte";
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

  const selectedTags = $derived($page.url.searchParams.getAll("tag"));
  const activeFolder = $derived($page.url.searchParams.get("folder"));
  const hasFilters = $derived(selectedTags.length > 0 || !!activeFolder);

  /** Navigate to the notes list, optionally with filters, without a reload. */
  function goNotes(params: URLSearchParams) {
    const qs = params.toString();
    onNavigate?.();
    void goto(`/notes${qs ? "?" + qs : ""}`);
  }

  function buildParams(): URLSearchParams {
    const next = new URLSearchParams();
    selectedTags.forEach((t) => next.append("tag", t));
    if (activeFolder) next.set("folder", activeFolder);
    return next;
  }

  function toggleTag(slug: string) {
    const next = buildParams();
    const current = next.getAll("tag");
    next.delete("tag");
    const updated = current.includes(slug)
      ? current.filter((s) => s !== slug)
      : [...current, slug];
    updated.forEach((s) => next.append("tag", s));
    goNotes(next);
  }

  function selectFolder(id: string | null) {
    const next = buildParams();
    if (id) next.set("folder", id);
    else next.delete("folder");
    goNotes(next);
  }

  function clearFilters() {
    const next = new URLSearchParams();
    if (activeFolder) next.set("folder", activeFolder);
    goNotes(next);
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
  <div class="shrink-0 border-b px-3 py-2">
    <div class="px-1 text-sm font-semibold tracking-tight text-muted-foreground">easy-notes</div>
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

      <!-- Folders -->
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
            class="mb-1 px-2"
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

        <button
          class={cn(
            "flex min-h-9 w-full items-center gap-2 rounded-md px-2 text-sm transition-colors",
            !activeFolder
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
          )}
          onclick={() => selectFolder(null)}
        >
          <Layers class="h-4 w-4 shrink-0" />
          All notes
        </button>

        {#each folders.tree as folder (folder.id)}
          <div>
            <div
              class={cn(
                "group/folder flex items-center rounded-md transition-colors",
                activeFolder === folder.id ? "bg-accent" : "hover:bg-accent/50"
              )}
            >
              {#if folder.children.length}
                <button
                  class="ml-1 inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-foreground"
                  aria-label={folder.collapsed ? "Expand" : "Collapse"}
                  onclick={() => void toggleCollapse(folder.id, folder.collapsed)}
                >
                  {#if folder.collapsed}
                    <ChevronRight class="h-3.5 w-3.5" />
                  {:else}
                    <ChevronDown class="h-3.5 w-3.5" />
                  {/if}
                </button>
              {:else}
                <span class="ml-1 w-6"></span>
              {/if}
              <button
                class={cn(
                  "flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md pr-2 text-sm transition-colors",
                  activeFolder === folder.id
                    ? "text-accent-foreground"
                    : "text-muted-foreground group-hover/folder:text-foreground"
                )}
                onclick={() => selectFolder(folder.id)}
              >
                <FolderIcon class="h-4 w-4 shrink-0" />
                <span class="truncate">{folder.name}</span>
                <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">
                  {folder.note_count}
                </span>
              </button>
            </div>

            {#if !folder.collapsed && folder.children.length}
              {#each folder.children as child (child.id)}
                <button
                  class={cn(
                    "flex min-h-8 w-full items-center gap-2 rounded-md pl-9 pr-2 text-sm transition-colors",
                    activeFolder === child.id
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  )}
                  onclick={() => selectFolder(child.id)}
                >
                  <FolderIcon class="h-3.5 w-3.5 shrink-0" />
                  <span class="truncate">{child.name}</span>
                  <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">
                    {child.note_count}
                  </span>
                </button>
              {/each}
            {/if}
          </div>
        {/each}
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
                <span
                  data-checked={checked}
                  class={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded border border-muted-foreground/40 transition-colors",
                    tagStyle(t.color).box
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
      <a
        href={hasFilters ? `/notes?${buildParams().toString()}` : "/notes"}
        onclick={onNavigate}
        class="block px-2 pb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground/70 hover:text-foreground"
      >
        Recent notes
      </a>

      {#if sidebarNotes.loading && sidebarNotes.items.length === 0}
        <p class="px-2 py-1 text-xs text-muted-foreground">Loading…</p>
      {:else if sidebarNotes.items.length === 0}
        <p class="px-2 py-1 text-xs text-muted-foreground">No notes yet.</p>
      {:else}
        <ul class="space-y-px">
          {#each sidebarNotes.items as n (n.id)}
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
              Load more ({sidebarNotes.items.length} of {sidebarNotes.count})
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
