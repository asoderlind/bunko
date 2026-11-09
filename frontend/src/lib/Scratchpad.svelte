<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { Eye, ImagePlus, PenLine } from "lucide-svelte";
  import { api, type Note } from "$lib/api";
  import { tree } from "$lib/stores.svelte";
  import { showToast } from "$lib/toast.svelte";
  import { cn } from "$lib/utils";
  import MarkdownEditor from "$lib/MarkdownEditor.svelte";
  import MarkdownPreview from "$lib/MarkdownPreview.svelte";

  /**
   * New-note composer. Same Markdown editor and preview as the note view,
   * autosaved. The note is created on the first keystroke (so it appears in
   * the sidebar) and then patched as you type, which means tagging starts
   * early and finishes sooner.
   */
  let body = $state("");
  let saving = $state(false);
  let saveError = $state<string | null>(null);
  let editor = $state<{ insert: (text: string) => void } | null>(null);
  let fileInput = $state<HTMLInputElement | null>(null);
  let previewOpen = $state(false);
  // The title floats over the composer, so measure it to pad the first line.
  // Keep a minimum fade band on desktop, where the header is very short.
  let headerHeight = $state(0);
  const fadeStart = $derived(Math.max(headerHeight, 64));
  const fadeEnd = $derived(fadeStart + 48);

  // The note we have already created in this session, if any.
  let created = $state<Note | null>(null);
  let pending = $state(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  onMount(() => {
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    previewOpen = desktop && localStorage.getItem("bunko.preview-open") !== "0";
  });

  // The newest text seen, so a save that finishes mid-typing can follow up
  // with whatever arrived meanwhile instead of dropping those keystrokes.
  let latest = "";

  /** Create on first content, then patch. Debounced so typing stays smooth. */
  async function persist(value: string) {
    latest = value;
    if (!value.trim()) return;
    if (pending) return;

    pending = true;
    saving = true;
    saveError = null;
    try {
      // Loop until no newer text arrived while we were saving.
      let target = value;
      while (target.trim()) {
        if (!created) {
          created = await api.createNote(target);
          // The sidebar renders the tree, so refresh it: the note appears
          // immediately, while the editor keeps focus.
          void tree.query();
          // Swap the URL to the real note without remounting this editor.
          history.replaceState({}, "", `/notes/${created.id}`);
        } else {
          created = await api.updateNote(created.id, { body_md: target });
          tree.patch(created.id, () => created!);
        }
        if (latest === target) break;
        target = latest;
      }
    } catch {
      saveError = "Could not save.";
    } finally {
      pending = false;
      saving = false;
    }
  }

  function oninput() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => void persist(body), 800);
  }

  function onblur() {
    if (timer) clearTimeout(timer);
    void persist(body);
  }

  function saveNow() {
    if (timer) clearTimeout(timer);
    void persist(body);
  }

  function togglePreview() {
    previewOpen = !previewOpen;
    localStorage.setItem("bunko.preview-open", previewOpen ? "1" : "0");
  }

  async function uploadImage(file: File): Promise<string> {
    const result = await api.uploadMedia(file);
    return result.markdown;
  }

  function openFilePicker() {
    fileInput?.click();
  }

  async function onFilePicked(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    try {
      const markdown = await uploadImage(file);
      editor?.insert(markdown);
      if (previewOpen && window.matchMedia("(max-width: 1023px)").matches) {
        togglePreview();
      }
    } catch {
      showToast("Image upload failed.", "error");
    }
  }

  async function finish() {
    if (!body.trim()) return;
    if (!created) await persist(body);
    if (created) await goto(`/notes/${created.id}`, { replaceState: true });
  }
</script>

<div
  class="relative flex min-h-0 w-full flex-1 flex-col"
  style="background-color: hsl(var(--note-bg))"
>
  <!-- Title overlay, matching the note editor. -->
  <div bind:clientHeight={headerHeight} class="pointer-events-none absolute inset-x-0 top-0 z-20">
    <div
      class="pointer-events-none absolute inset-x-0 top-0"
      style="height: {fadeEnd}px; background: linear-gradient(to bottom, hsl(var(--note-bg)) 0px, hsl(var(--note-bg)) {fadeStart}px, transparent {fadeEnd}px)"
    ></div>
    <div class="relative flex min-h-8 items-center gap-2 pl-14 pr-4 pt-3 pb-2 md:px-8">
      <h1 class="min-w-0 flex-1 truncate text-base font-normal tracking-tight text-foreground/90">
        {created ? created.title || "(untitled)" : "New note"}
      </h1>
      <div class="flex shrink-0 items-center gap-1">
        <button
          type="button"
          class="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          onclick={openFilePicker}
          aria-label="Insert image"
          title="Insert image"
        >
          <ImagePlus class="h-4 w-4" />
        </button>
        <button
          type="button"
          class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          onclick={togglePreview}
          aria-label={previewOpen ? "Show editor" : "Show preview"}
          title={previewOpen ? "Show editor" : "Show preview"}
        >
          {#if previewOpen}
            <PenLine class="h-4 w-4" />
            <span class="hidden sm:inline">Hide preview</span>
            <span class="sm:hidden">Write</span>
          {:else}
            <Eye class="h-4 w-4" />
            <span>Preview</span>
          {/if}
        </button>
      </div>
    </div>
  </div>

  <div class="relative flex min-h-0 flex-1">
    <div class={cn("relative flex min-h-0 flex-1 flex-col", previewOpen && "hidden lg:flex")}>
      <MarkdownEditor
        bind:this={editor}
        value={body}
        onchange={(value) => {
          body = value;
          oninput();
        }}
        onblur={onblur}
        onsave={saveNow}
        onupload={uploadImage}
        padTop={fadeEnd + 8}
        padBottom={64}
        placeholder="Write something…"
        ariaLabel="New note body"
        autofocus
      />
    </div>

    {#if previewOpen}
      <div
        class="relative flex min-h-0 flex-1 overflow-hidden lg:w-[42%] lg:max-w-[42%] lg:flex-none lg:border-l lg:border-border/60"
      >
        <div
          class="scrollbar-thin h-full w-full overflow-y-auto overscroll-contain"
          style="padding-top: {fadeEnd + 8}px; padding-bottom: 64px"
        >
          <div class="px-4 md:px-8">
            <MarkdownPreview source={body} />
          </div>
        </div>
      </div>
    {/if}

    <!-- Match the top fade at the bottom, above the status bar. -->
    <div
      class="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-12"
      style="background: linear-gradient(to top, hsl(var(--note-bg)) 0px, hsl(var(--note-bg) / 0.8) 50%, transparent 100%)"
    ></div>
  </div>

  <input
    bind:this={fileInput}
    type="file"
    accept="image/png,image/jpeg,image/gif,image/webp"
    class="hidden"
    onchange={onFilePicked}
  />

  <div class="flex min-h-11 items-center gap-3 px-4 md:px-8 pt-2 pb-6 text-sm text-muted-foreground">
    {#if saving}
      Saving…
    {:else if saveError}
      <span class="text-red-400">{saveError}</span>
    {:else if body.trim()}
      Saved
    {:else}
      Nothing to save yet
    {/if}
    {#if body.trim()}
      <button
        class="ml-auto text-xs text-muted-foreground hover:text-foreground"
        onclick={() => void finish()}
      >
        Open note
      </button>
    {:else}
      <span class="ml-auto text-xs">⌘/Ctrl + S</span>
    {/if}
  </div>
</div>
