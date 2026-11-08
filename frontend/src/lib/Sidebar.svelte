<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import {
    ChevronDown,
    Filter,
    Inbox,
    Loader2,
    LogOut,
    NotebookPen,
    Tag as TagIcon,
  } from "lucide-svelte";
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";
  import { auth, sidebarNotes, tags } from "$lib/stores.svelte";
  import TagPill from "./TagPill.svelte";
  import NoteActions from "./NoteActions.svelte";

  let { onNavigate }: { onNavigate?: () => void } = $props();

  let filterOpen = $state(false);

  const NAV = [
    { href: "/", label: "New note", icon: NotebookPen },
    { href: "/inbox", label: "Needs tags", icon: Inbox },
    { href: "/tags", label: "Tags", icon: TagIcon },
  ];

  const selectedTags = $derived($page.url.searchParams.getAll("tag"));

  onMount(() => {
    if (!sidebarNotes.loadedOnce) {
      sidebarNotes.loadedOnce = true;
      void sidebarNotes.query();
    }
    if (!tags.loaded) void tags.load();
  });

  function toggleTag(slug: string) {
    const next = new URLSearchParams($page.url.searchParams);
    const current = next.getAll("tag");
    next.delete("tag");
    const updated = current.includes(slug)
      ? current.filter((s) => s !== slug)
      : [...current, slug];
    updated.forEach((s) => next.append("tag", s));
    onNavigate?.();
    window.location.href = `/notes?${next.toString()}`;
  }

  function clearFilters() {
    window.location.href = "/notes";
    onNavigate?.();
  }

  function isActive(href: string) {
    const p = $page.url.pathname;
    return href === "/" ? p === "/" : p.startsWith(href);
  }
</script>

<!--
  Structure borrowed from Open WebUI's sidebar: a bounded column with a fixed
  header, ONE scrollable middle region, and a pinned footer. The tag filter
  lives inside that scroll region, so expanding it adds scrollable content
  instead of stealing height from the note list.
-->
<div class="flex h-full flex-col">
  <div class="shrink-0 border-b px-3 py-2">
    <div class="px-1 text-sm font-semibold tracking-tight text-muted-foreground">easy-notes</div>
  </div>

  <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
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

      <!-- Tag filter -->
      <div class="px-1">
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
        href="/notes"
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
            <li
              class="group/row flex items-center rounded-md transition-colors hover:bg-accent/50"
            >
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
