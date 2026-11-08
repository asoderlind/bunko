<script lang="ts">
  import Sidebar from "./Sidebar.svelte";
  import { page } from "$app/stores";
  import {
    Menu,
    PanelLeftClose,
    PanelLeftOpen,
    Search,
    X,
  } from "lucide-svelte";

  let { children } = $props();

  // Desktop: the rail can be collapsed to give the note full width.
  let collapsed = $state(false);
  // Mobile: the sidebar is an overlay drawer.
  let drawer = $state(false);
  let searching = $state(false);
  let searchInput = $state<HTMLInputElement | null>(null);
  let q = $state("");

  // Persist the desktop preference across reloads.
  if (typeof localStorage !== "undefined") {
    collapsed = localStorage.getItem("easy-notes.sidebar-collapsed") === "1";
  }
  $effect(() => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("easy-notes.sidebar-collapsed", collapsed ? "1" : "0");
    }
  });

  // Close the drawer whenever the route changes.
  $effect(() => {
    void $page.url.pathname;
    drawer = false;
  });

  // `/` opens search unless the user is already typing somewhere.
  $effect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      const typing =
        !!t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable);
      if (e.key === "/" && !typing && !searching) {
        e.preventDefault();
        searching = true;
      }
      if (e.key === "Escape") {
        searching = false;
        drawer = false;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  $effect(() => {
    if (searching) searchInput?.focus();
  });

  function submitSearch(e: SubmitEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    searching = false;
    window.location.href = `/notes?q=${encodeURIComponent(q.trim())}`;
  }
</script>

<div class="flex min-h-dvh">
  <!-- Desktop rail, collapsible -->
  <aside
    class="hidden shrink-0 border-r bg-card/40 transition-[width] duration-200 md:block"
    class:md:w-56={!collapsed}
    class:md:w-0={collapsed}
    class:md:border-r-0={collapsed}
    aria-hidden={collapsed}
  >
    <div class="sticky top-0 h-dvh overflow-hidden">
      <div class="h-full w-56">
        <Sidebar />
      </div>
    </div>
  </aside>

  <!-- Mobile drawer -->
  {#if drawer}
    <div class="fixed inset-0 z-40 md:hidden">
      <button
        class="absolute inset-0 touch-none bg-black/60 animate-in fade-in-0"
        aria-label="Close menu"
        onclick={() => (drawer = false)}
      ></button>
      <div
        class="absolute left-0 top-0 h-dvh w-[90%] border-r bg-card shadow-xl animate-in slide-in-from-left duration-200"
      >
        <Sidebar onNavigate={() => (drawer = false)} />
      </div>
    </div>
  {/if}

  <div class="flex min-w-0 flex-1 flex-col">
    <header
      class="sticky top-0 z-30 flex items-center gap-1 border-b bg-background/95 px-2 py-1.5 backdrop-blur"
    >
      <!-- Mobile: open the drawer -->
      <button
        class="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
        onclick={() => (drawer = true)}
        aria-label="Open menu"
      >
        <Menu class="h-5 w-5" />
      </button>

      <!-- Desktop: collapse/expand the rail -->
      <button
        class="hidden h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground md:inline-flex"
        onclick={() => (collapsed = !collapsed)}
        aria-label={collapsed ? "Show sidebar" : "Hide sidebar"}
        aria-pressed={!collapsed}
        title={collapsed ? "Show sidebar" : "Hide sidebar"}
      >
        {#if collapsed}
          <PanelLeftOpen class="h-5 w-5" />
        {:else}
          <PanelLeftClose class="h-5 w-5" />
        {/if}
      </button>

      <span class="px-2 text-sm font-semibold tracking-tight md:hidden">easy-notes</span>
      <div class="ml-auto">
        <button
          class="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
          onclick={() => (searching = true)}
          aria-label="Search"
        >
          <Search class="h-5 w-5" />
        </button>
      </div>
    </header>

    {#if searching}
      <form
        onsubmit={submitSearch}
        class="flex items-center gap-2 border-b bg-background px-3 py-2"
      >
        <Search class="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          bind:this={searchInput}
          bind:value={q}
          placeholder="Search notes…"
          aria-label="Search notes"
          class="h-10 flex-1 border-0 bg-transparent text-base outline-none placeholder:text-muted-foreground"
          onkeydown={(e) => e.key === "Escape" && (searching = false)}
        />
        <button
          type="button"
          class="inline-flex h-11 w-11 items-center justify-center rounded-md text-muted-foreground hover:bg-accent"
          onclick={() => (searching = false)}
          aria-label="Close search"
        >
          <X class="h-5 w-5" />
        </button>
      </form>
    {/if}

    <main class="flex min-w-0 flex-1 flex-col">
      {@render children?.()}
    </main>
  </div>
</div>
