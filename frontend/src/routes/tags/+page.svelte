<script lang="ts">
  import { onMount } from "svelte";
  import { Dialog } from "bits-ui";
  import { Loader2, Merge } from "lucide-svelte";
  import { api, slugify, type Tag } from "$lib/api";
  import { tags } from "$lib/stores.svelte";

  let name = $state("");
  let description = $state("");
  let creating = $state(false);
  let createError = $state<string | null>(null);

  let mergeFrom = $state<Tag | null>(null);
  let mergeInto = $state("");
  let mergeOpen = $state(false);
  let merging = $state(false);
  let mergeError = $state<string | null>(null);

  const slug = $derived(slugify(name));

  onMount(() => {
    if (!tags.loaded) void tags.load();
  });

  async function create() {
    if (!slug) return;
    creating = true;
    createError = null;
    try {
      await api.createTag({ slug, name: name.trim(), description: description.trim() });
      name = "";
      description = "";
      await tags.load();
    } catch {
      createError = "Could not create — a tag with that slug may already exist.";
    } finally {
      creating = false;
    }
  }

  async function doMerge() {
    if (!mergeFrom || !mergeInto) return;
    merging = true;
    mergeError = null;
    try {
      await api.mergeTag(mergeFrom.id, mergeInto);
      mergeOpen = false;
      mergeFrom = null;
      mergeInto = "";
      await tags.load();
    } catch {
      mergeError = "Merge failed.";
    } finally {
      merging = false;
    }
  }
</script>

<div class="mx-auto w-full max-w-3xl px-4 py-5">
  <h1 class="mb-4 text-xl font-semibold tracking-tight">Tags</h1>

  <section class="mb-6 space-y-2 rounded-xl border bg-card p-4">
    <h2 class="text-sm font-medium text-muted-foreground">New tag</h2>
    <input
      bind:value={name}
      placeholder="Name (e.g. Trading)"
      class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    />
    <input
      bind:value={description}
      placeholder="One line: what belongs in this tag?"
      maxlength={200}
      class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    />
    <p class="text-sm text-muted-foreground">
      Slug: <code class="rounded bg-muted px-1">{slug || "—"}</code> — the description is how the
      model tells similar tags apart.
    </p>
    <button
      onclick={() => void create()}
      disabled={!slug || creating}
      class="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
    >
      {creating ? "Creating…" : "Create"}
    </button>
    {#if createError}
      <p class="text-sm text-red-400">{createError}</p>
    {/if}
  </section>

  {#if !tags.loaded}
    <div class="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" /> Loading…
    </div>
  {:else}
    <ul class="divide-y">
      {#each tags.items as t (t.id)}
        <li class="flex items-start justify-between gap-3 py-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="font-medium">{t.name}</span>
              <span class="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                /{t.slug}
              </span>
              <span class="text-xs text-muted-foreground">
                {t.note_count} note{t.note_count === 1 ? "" : "s"}
              </span>
            </div>
            {#if t.description}
              <p class="mt-0.5 text-sm text-muted-foreground">{t.description}</p>
            {/if}
          </div>
          <button
            class="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-md border border-input px-3 text-xs hover:bg-accent"
            onclick={() => {
              mergeFrom = t;
              mergeInto = "";
              mergeOpen = true;
            }}
          >
            <Merge class="h-3.5 w-3.5" /> Merge
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<Dialog.Root bind:open={mergeOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/70 animate-in fade-in-0" />
    <Dialog.Content
      class="fixed bottom-0 left-0 right-0 z-50 grid gap-4 rounded-t-2xl border bg-card p-5 shadow-lg animate-in slide-in-from-bottom-4 sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl"
    >
      <div class="flex flex-col space-y-1.5">
        <Dialog.Title class="text-lg font-semibold leading-none tracking-tight">
          Merge “{mergeFrom?.name}” into…
        </Dialog.Title>
        <Dialog.Description class="text-sm text-muted-foreground">
          All notes tagged “{mergeFrom?.name}” move to the target. Duplicates collapse.
          “{mergeFrom?.name}” is then deleted.
        </Dialog.Description>
      </div>

      <select
        bind:value={mergeInto}
        class="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-base"
      >
        <option value="">Choose target tag</option>
        {#each tags.items.filter((t) => t.id !== mergeFrom?.id) as t (t.id)}
          <option value={t.slug}>{t.name}</option>
        {/each}
      </select>

      {#if mergeError}
        <p class="text-sm text-red-400">{mergeError}</p>
      {/if}

      <div class="flex gap-2">
        <button
          onclick={() => void doMerge()}
          disabled={!mergeInto || merging}
          class="inline-flex h-11 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {merging ? "Merging…" : "Merge"}
        </button>
        <button
          onclick={() => (mergeOpen = false)}
          class="inline-flex h-11 items-center rounded-md px-4 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          Cancel
        </button>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
