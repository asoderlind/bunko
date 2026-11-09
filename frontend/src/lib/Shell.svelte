<script lang="ts">
  import Sidebar from "./Sidebar.svelte";
  import { page } from "$app/stores";
  import { cn } from "$lib/utils";
  import { search } from "$lib/search.svelte";
  import SearchModal from "$lib/SearchModal.svelte";
  import Toasts from "$lib/Toasts.svelte";
  import {
    Menu,
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
    collapsed = localStorage.getItem("bunko.sidebar-collapsed") === "1";
  }
  $effect(() => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("bunko.sidebar-collapsed", collapsed ? "1" : "0");
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

<div class="flex h-dvh overflow-hidden">
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
        <Sidebar {collapsed} onCollapse={() => (collapsed = true)} />
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
        <Sidebar onNavigate={() => (drawer = false)} {collapsed} onCollapse={() => (collapsed = true)} />
      </div>
    </div>
  {/if}

  <div class="relative flex min-h-0 min-w-0 flex-1 flex-col">
    {#if collapsed}
      <button
        class="absolute left-3 top-3 z-30 hidden h-8 w-8 items-center justify-center rounded-md border bg-background text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground md:inline-flex"
        onclick={() => (collapsed = false)}
        aria-label="Show sidebar"
        title="Show sidebar"
      >
        <PanelLeftOpen class="h-4 w-4" />
      </button>
    {/if}
    <button
      class="absolute left-3 top-3 z-30 inline-flex h-8 w-8 items-center justify-center rounded-md border bg-background text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground md:hidden"
      onclick={() => (drawer = true)}
      aria-label="Open menu"
    >
      <Menu class="h-4 w-4" />
    </button>

    <main
      class={cn(
        "flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto",
        collapsed ? "md:pt-6" : "md:pt-0"
      )}
    >
      {@render children?.()}
    </main>

    <SearchModal />
    <Toasts />
  </div>
</div>
