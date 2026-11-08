<script lang="ts">
  import Sidebar from "./Sidebar.svelte";
  import { page } from "$app/stores";
  import { header } from "$lib/header.svelte";
  import { search } from "$lib/search.svelte";
  import SearchModal from "$lib/SearchModal.svelte";
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
  // Search is opened from the sidebar; the field renders under the header.


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
      if (e.key === "/" && !typing && !search.visible) {
        e.preventDefault();
        search.show();
      }
      if (e.key === "Escape") {
        search.hide();
        drawer = false;
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

</script>

<div class="flex min-h-dvh">
  <!--
    Desktop rail, collapsible. The width (w-72) is written out on both the
    aside and the inner wrapper; Tailwind needs literal classes, and the two
    must match or content clips while animating.
  -->
  <aside
    class="hidden shrink-0 border-r bg-card/40 transition-[width] duration-200 md:block"
    class:md:w-72={!collapsed}
    class:md:w-0={collapsed}
    class:md:border-r-0={collapsed}
    aria-hidden={collapsed}
  >
    <div class="sticky top-0 h-dvh overflow-hidden">
      <div class="h-full w-72">
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
    <!-- Fixed height: the app bar and any page bar line up exactly. -->
    <header
      class="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-1 border-b bg-background/95 px-2 backdrop-blur"
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

      <!-- Room for the current page's title, set by the page itself. -->
      {#if header.title}
        <div class="mx-2 min-w-0">
          <div class="truncate text-sm font-medium leading-tight">{header.title}</div>
          {#if header.subtitle}
            <div class="truncate text-xs leading-tight text-muted-foreground">
              {header.subtitle}
            </div>
          {/if}
        </div>
      {/if}

    </header>

    <main class="flex min-w-0 flex-1 flex-col">
      {@render children?.()}
    </main>

    <SearchModal />
  </div>
</div>
