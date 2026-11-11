<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { Popover } from "bits-ui";
  import {
    Check,
    ChevronDown,
    ChevronRight,
    ChevronsUpDown,
    Filter,
    Folder as FolderIcon,
    FolderPlus,
    Lock,
    LogOut,
    NotebookPen,
    PanelLeftClose,
    Pin,
    Search,
    Settings,
    Tag as TagIcon,
    X,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";
  import { api, type Note } from "$lib/api";
  import { auth, folders, providers, tags, tree } from "$lib/stores.svelte";
  import { search } from "$lib/search.svelte";
  import TagPill from "./TagPill.svelte";
  import NoteActions from "./NoteActions.svelte";
  import FolderActions from "./FolderActions.svelte";

  let {
    onNavigate,
    collapsed,
    onCollapse,
  }: {
    onNavigate?: () => void;
    collapsed?: boolean;
    onCollapse?: () => void;
  } = $props();

  let filterOpen = $state(false);
  let creatingFolder = $state(false);
  let newFolderName = $state("");
  let folderBusy = $state(false);

  // Bottom user menu. OpenWebUI puts the account entry at the bottom of the
  // rail and hides sign-out inside its popover.
  let userMenuOpen = $state(false);
  const username = $derived(auth.user?.username ?? "Account");
  const userInitial = $derived((username[0] ?? "?").toUpperCase());

  async function signOut() {
    userMenuOpen = false;
    await auth.logout();
  }

  // Which folders are expanded, by id. Unfiled uses the empty string.
  let expanded = $state<Set<string>>(new Set());

  // Pin state persisted to localStorage.
  let pinnedIds = $state<string[]>(loadPinned());
  function loadPinned(): string[] {
    try {
      return JSON.parse(localStorage.getItem("bunko-pinned") || "[]");
    } catch {
      return [];
    }
  }
  function savePinned() {
    localStorage.setItem("bunko-pinned", JSON.stringify(pinnedIds));
  }
  function isPinned(id: string) {
    return pinnedIds.includes(id);
  }
  function togglePin(id: string) {
    pinnedIds = isPinned(id)
      ? pinnedIds.filter((x) => x !== id)
      : [...pinnedIds, id];
    savePinned();
  }
  function sortPinnedFirst(notes: Note[]) {
    return [...notes].sort((a, b) => {
      const ap = isPinned(a.id) ? -1 : 0;
      const bp = isPinned(b.id) ? -1 : 0;
      return ap - bp;
    });
  }

  // Inline folder rename state.
  let renamingFolderId = $state<string | null>(null);
  let renamingFolderName = $state("");

  const NAV = [
    { href: "/", label: "New note", icon: NotebookPen },
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

  function cancelCreateFolder() {
    if (folderBusy) return;
    newFolderName = "";
    creatingFolder = false;
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

  function startRenameFolder(folder: import("$lib/api").Folder) {
    renamingFolderId = folder.id;
    renamingFolderName = folder.name;
  }

  function cancelFolderRename() {
    renamingFolderId = null;
    renamingFolderName = "";
  }

  async function saveFolderRename(id: string) {
    const name = renamingFolderName.trim();
    if (!name) {
      cancelFolderRename();
      return;
    }
    await api.updateFolder(id, { name });
    renamingFolderId = null;
    renamingFolderName = "";
    await folders.load();
  }

  async function deleteFolder(folder: import("$lib/api").Folder) {
    await api.deleteFolder(folder.id);
    await folders.load();
    await tree.query({ tag: selectedTags.length ? selectedTags : undefined });
  }

  function isActive(href: string) {
    const p = $page.url.pathname;
    return href === "/" ? p === "/" : p.startsWith(href);
  }

  onMount(() => {
    if (!tree.loaded) void tree.query();
    if (!tags.loaded) void tags.load();
    if (!folders.loaded) void folders.load();
    if (!providers.loaded) void providers.load();
  });
</script>

{#snippet noteRow(n: Note)}
  {@const isActiveNote = $page.url.pathname === `/notes/${n.id}`}
  <li class={cn("group/row flex items-center rounded-md transition-colors hover:bg-accent/50", isActiveNote && "bg-accent/50")}>
    <a
      href={`/notes/${n.id}`}
      onclick={onNavigate}
      title={n.title}
      class={cn(
        "flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md py-1 pl-2 pr-1 text-sm transition-colors",
        isActiveNote
          ? "text-accent-foreground"
          : "text-muted-foreground group-hover/row:text-foreground"
      )}
    >
      {#if n.local_only}
        <Lock class="h-3 w-3 shrink-0 text-primary/80" aria-label="Private note" />
      {/if}
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
    <button
      onclick={() => togglePin(n.id)}
      class={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-md transition-colors",
        isPinned(n.id)
          ? "text-primary opacity-100"
          : "text-muted-foreground opacity-0 group-hover/row:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
      )}
      aria-label={isPinned(n.id) ? "Unpin note" : "Pin note"}
      title={isPinned(n.id) ? "Unpin note" : "Pin note"}
    >
      <Pin class={cn("h-4 w-4", isPinned(n.id) && "fill-current")} />
    </button>
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
  <!--
    Compact rail header, like OpenWebUI's: no divider, a short row with the
    app name and the collapse control, so the note list starts higher up.
  -->
  <div class="flex h-9 shrink-0 items-center justify-between gap-1 px-2">
    <a
      href="/"
      onclick={onNavigate}
      class="min-w-0 flex-1 truncate rounded-lg px-1.5 py-1 text-sm font-normal tracking-tight text-foreground/90 transition-colors hover:text-foreground"
    >
      bunko
    </a>
    {#if onCollapse}
      <button
        class="hidden h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:inline-flex"
        onclick={onCollapse}
        aria-label="Collapse sidebar"
        title="Collapse sidebar"
      >
        <PanelLeftClose class="h-4 w-4" />
      </button>
    {/if}
  </div>

  <div class="scrollbar-thin min-h-0 flex-1 overflow-y-auto overscroll-contain">
    <nav class="space-y-1 p-3 pt-1">
      <!-- Search opens a modal, so it is a button rather than a link. -->
      <button
        onclick={() => search.show()}
        class="flex min-h-9 w-full items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
      >
        <Search class="h-4 w-4 shrink-0" />
        Search
        <kbd class="ml-auto rounded border px-1.5 text-[10px] text-muted-foreground/70">/</kbd>
      </button>

      {#each NAV as item (item.href)}
        <a
          href={item.href}
          onclick={onNavigate}
          class={cn(
            "flex min-h-9 items-center gap-3 rounded-md px-3 text-sm transition-colors",
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
            class="mb-1 flex items-center gap-1 px-1"
            onsubmit={(e) => {
              e.preventDefault();
              void createFolder();
            }}
          >
            <input
              bind:value={newFolderName}
              placeholder="Folder name"
              aria-label="Folder name"
              class="h-8 min-w-0 flex-1 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              disabled={folderBusy}
            />
            <button
              type="submit"
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
              aria-label="Create folder"
              title="Create folder"
              disabled={folderBusy || !newFolderName.trim()}
            >
              <Check class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
              aria-label="Cancel creating folder"
              title="Cancel"
              onclick={cancelCreateFolder}
              disabled={folderBusy}
            >
              <X class="h-4 w-4" />
            </button>
          </form>
        {/if}

        {#each folders.rootFolders as folder (folder.id)}
          {@const isOpen = expanded.has(folder.id)}
          {@const children = tree.inFolder(folder.id)}
          <div class="group/folder">
            <div class="flex items-center gap-0.5 rounded-md ps-2 transition-colors hover:bg-accent/50">
              <button
                class="inline-flex h-8 w-6 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground"
                aria-label={isOpen ? `Collapse ${folder.name}` : `Expand ${folder.name}`}
                aria-expanded={isOpen}
                onclick={() => toggleExpanded(folder.id)}
              >
                <ChevronRight
                  class={cn(
                    "h-4 w-4 transition-transform duration-200",
                    isOpen && "rotate-90"
                  )}
                />
              </button>
              {#if renamingFolderId === folder.id}
                <form
                  class="flex min-h-9 flex-1 items-center"
                  onsubmit={(e) => {
                    e.preventDefault();
                    void saveFolderRename(folder.id);
                  }}
                >
                  <input
                    bind:value={renamingFolderName}
                    placeholder="Folder name"
                    aria-label="Folder name"
                    class="h-8 w-full rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onkeydown={(e) => {
                      if (e.key === "Escape") cancelFolderRename();
                    }}
                    onblur={() => {
                      if (renamingFolderId === folder.id) void saveFolderRename(folder.id);
                    }}
                  />
                </form>
              {:else}
                <button
                  class="flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-md px-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
                  onclick={() => toggleExpanded(folder.id)}
                >
                  <FolderIcon class="h-4 w-4 shrink-0" />
                  <span class="truncate">{folder.name}</span>
                  <span class="ml-auto shrink-0 text-xs text-muted-foreground/70">
                    {folder.note_count}
                  </span>
                </button>
              {/if}
              <FolderActions
                {folder}
                onRename={startRenameFolder}
                onDelete={deleteFolder}
                class="opacity-0 group-hover/folder:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
              />
            </div>

            <!-- Animated height reveal, same technique as the filter. -->
            {#if isOpen}
              <div class="ms-3 animate-in fade-in-0 slide-in-from-top-1 border-s border-border/60 ps-1">
                {#each sortPinnedFirst(children) as n (n.id)}
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
    <div class="px-3 pb-2 pt-4">
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
            {#each sortPinnedFirst(loose) as n (n.id)}
              {@render noteRow(n)}
            {/each}
          </ul>
        {/if}
      {/if}
    </div>
  </div>

  <!-- Account entry pinned to the bottom of the rail. -->
  <div class="shrink-0 p-2 pt-1">
    <Popover.Root bind:open={userMenuOpen}>
      <Popover.Trigger
        class="flex w-full items-center gap-2.5 rounded-lg px-1.5 py-1.5 text-left transition-colors hover:bg-accent data-[state=open]:bg-accent"
        aria-label="Open user menu"
      >
        <span
          class="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-medium text-primary"
          aria-hidden="true"
        >
          {userInitial}
          <span
            class="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-card bg-emerald-500"
          ></span>
        </span>
        <span class="min-w-0 flex-1 truncate text-sm text-foreground/90">{username}</span>
        <ChevronsUpDown class="h-4 w-4 shrink-0 text-muted-foreground" />
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          side="top"
          align="start"
          sideOffset={6}
          class="z-50 w-60 rounded-xl border bg-card p-1 text-card-foreground shadow-lg shadow-black/20 animate-in fade-in-0 zoom-in-95"
        >
          <div class="flex items-center gap-2.5 px-2 py-2">
            <span
              class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-medium text-primary"
            >
              {userInitial}
            </span>
            <div class="min-w-0">
              <p class="truncate text-sm font-medium">{username}</p>
              <p class="text-xs text-muted-foreground">Signed in</p>
            </div>
          </div>

          <div class="my-1 h-px bg-border"></div>

          <a
            href="/settings"
            class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <Settings class="h-4 w-4" />
            Settings
          </a>

          <button
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-red-500/15 hover:text-red-300"
            onclick={() => void signOut()}
          >
            <LogOut class="h-4 w-4" />
            Sign out
          </button>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  </div>
</div>
