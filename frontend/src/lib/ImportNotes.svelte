<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { downloadNotesFile } from "$lib/download";
  import { folders, tags, providers, sidebarNotes, tree } from "$lib/stores.svelte";
  import { onMount } from "svelte";

  let files = $state<File[]>([]);
  let generateTags = $state(true);
  let generateTitle = $state(true);
  let importing = $state(false);
  let exporting = $state(false);
  let exportError = $state("");
  let collectionFile = $state<File | null>(null);
  let collectionInput: HTMLInputElement;
  let importingCollection = $state(false);
  let collectionError = $state("");
  let collectionSummary = $state("");

  async function importCollection() {
    if (!collectionFile || importingCollection) return;
    importingCollection = true;
    collectionError = "";
    collectionSummary = "";
    try {
      const result = await api.importCollection(collectionFile);
      collectionSummary = `Imported ${result.imported} notes from the collection.`;
      collectionFile = null;
      collectionInput.value = "";
      await Promise.allSettled([tree.query(), sidebarNotes.query(), folders.load(), tags.load()]);
    } catch (error) {
      const detail = error instanceof ApiError ? (error.body as { detail?: string })?.detail : null;
      collectionError = detail || "Could not import the collection. Please try again.";
    } finally {
      importingCollection = false;
    }
  }

  async function exportAll() {
    exporting = true;
    exportError = "";
    try {
      await downloadNotesFile("/api/notes/export", "bunko-collection.zip");
    } catch {
      exportError = "Could not export the collection. Please try again.";
    } finally {
      exporting = false;
    }
  }
  let progress = $state("");
  let summary = $state("");
  let errors = $state<string[]>([]);
  let fileInput: HTMLInputElement;

  const hasProvider = $derived(!!providers.selected);
  const needsProvider = $derived(generateTags || generateTitle);

  onMount(() => { void providers.load(); });

  function selectFiles(event: Event) {
    files = Array.from((event.currentTarget as HTMLInputElement).files ?? []);
    summary = "";
    errors = [];
  }

  async function importFiles() {
    if (importing || !files.length) return;
    importing = true;
    errors = [];
    summary = "";
    const selected = [...files];
    const failed: File[] = [];
    const generation = { generate_tags: generateTags, generate_title: generateTitle };
    let imported = 0;
    try {
      for (const [index, file] of selected.entries()) {
        progress = `Importing ${index + 1} of ${selected.length}…`;
        try {
          if (!file.name.toLowerCase().endsWith(".md")) {
            throw new Error("Only .md files are supported.");
          }
          const body = await file.text();
          if (!body.trim()) throw new Error("The file is empty.");
          await api.importNote(body, generation);
          imported += 1;
        } catch (error) {
          failed.push(file);
          const detail = error instanceof ApiError ? (error.body as { detail?: string })?.detail : null;
          errors = [...errors, `${file.name}: ${detail || (error instanceof Error ? error.message : "Import failed.")}`];
        }
      }
      // Keep only unsuccessful files selected so retrying does not duplicate successes.
      files = failed;
      fileInput.value = "";
      summary = `Imported ${imported} of ${selected.length} notes.`;
      if (imported && (generation.generate_tags || generation.generate_title)) {
        summary += " Any eligible generation tasks will run in the background.";
      }
      if (imported) await Promise.allSettled([tree.query(), sidebarNotes.query(), folders.load(), tags.load()]);
    } finally {
      importing = false;
      progress = "";
    }
  }
</script>

<section class="mb-6 space-y-4 rounded-xl border bg-card p-4">
  <div>
    <h2 class="text-sm font-medium">Import Markdown notes</h2>
    <p class="mt-1 text-xs text-muted-foreground">
      Choose one or more .md files. Front matter takes precedence for title, dates,
      tags, folder, and privacy. Missing titles use generation or the first non-empty line.
      Notes without privacy metadata are non-private. Private notes never use AI.
    </p>
  </div>

  <label class="block space-y-2 text-sm">
    <span>Markdown files</span>
    <input
      bind:this={fileInput}
      type="file"
      accept=".md,text/markdown"
      multiple
      disabled={importing}
      onchange={selectFiles}
      class="block w-full text-sm text-muted-foreground"
    />
  </label>

  {#if files.length}
    <p class="text-xs text-muted-foreground">{files.length} file(s) selected</p>
  {/if}

  <div class="flex flex-wrap gap-4 text-sm">
    <label class="inline-flex items-center gap-2">
      <input type="checkbox" bind:checked={generateTags} disabled={importing} />
      Generate tags
    </label>
    <label class="inline-flex items-center gap-2">
      <input type="checkbox" bind:checked={generateTitle} disabled={importing} />
      Generate title
    </label>
  </div>
  <p class="text-xs text-muted-foreground">
    Generation sends note content to your configured provider. Tags are selected from your existing tags.
  </p>

  {#if needsProvider && !hasProvider}
    <p class="text-sm text-muted-foreground">
      No provider is configured. Metadata will still be imported, but AI generation will be skipped.
    </p>
  {/if}

  <button
    type="button"
    onclick={() => void importFiles()}
    disabled={importing || !files.length}
    class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
  >
    {importing ? progress : "Import notes"}
  </button>

  <div aria-live="polite" class="space-y-1 text-sm">
    {#if summary}<p>{summary}</p>{/if}
    {#each errors as error}
      <p class="text-red-400">{error}</p>
    {/each}
  </div>
</section>

<section class="mb-6 space-y-3 rounded-xl border bg-card p-4">
  <h2 class="text-sm font-medium">Export collection</h2>
  <p class="text-xs text-muted-foreground">
    Download all notes as a ZIP with a separate .md file for each note.
    Includes title, dates, tags, folder path, and privacy in YAML front matter.
    Private notes are included as plain text; keep the archive safe.
    Import this ZIP on another instance using Import collection below.
    This is a notes backup, not a full database backup: attachments, provider settings,
    and empty folders are not included.
  </p>
  <button
    type="button"
    onclick={() => void exportAll()}
    disabled={exporting}
    class="inline-flex h-10 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
  >
    {exporting ? "Exporting…" : "Export collection"}
  </button>
  {#if exportError}<p role="alert" class="text-sm text-red-400">{exportError}</p>{/if}
</section>

<section class="mb-6 space-y-3 rounded-xl border bg-card p-4">
  <h2 class="text-sm font-medium">Import collection</h2>
  <p class="text-xs text-muted-foreground">
    Restore a ZIP from Export collection. Titles, dates, tags, folders, and privacy
    are preserved without AI generation. Notes are added to this instance; existing
    notes are not replaced. Importing the same collection again creates duplicates.
    If any file is invalid, nothing is imported.
  </p>
  <label class="block space-y-2 text-sm">
    <span>Collection ZIP (up to 50 MiB)</span>
    <input
      bind:this={collectionInput}
      type="file"
      accept=".zip,application/zip"
      disabled={importingCollection}
      onchange={(event) => {
        collectionFile = event.currentTarget.files?.[0] ?? null;
        collectionError = "";
        collectionSummary = "";
      }}
      class="block w-full text-sm text-muted-foreground"
    />
  </label>
  <button
    type="button"
    onclick={() => void importCollection()}
    disabled={importingCollection || !collectionFile}
    class="inline-flex h-10 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
  >
    {importingCollection ? "Importing collection…" : "Import collection"}
  </button>
  <div aria-live="polite" class="text-sm">
    {#if collectionSummary}<p>{collectionSummary}</p>{/if}
    {#if collectionError}<p class="text-red-400">{collectionError}</p>{/if}
  </div>
</section>
