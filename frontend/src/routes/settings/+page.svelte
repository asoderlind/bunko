<script lang="ts">
  import { onMount } from "svelte";
  import { KeyRound, Loader2, Pencil, Save, X } from "lucide-svelte";
  import { api, type Provider } from "$lib/api";
  import { providers as providerStore } from "$lib/stores.svelte";

  let providers = $state<Provider[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let editingId = $state<string | null>(null);

  let label = $state("OpenRouter");
  let baseUrl = $state("https://openrouter.ai/api/v1");
  let model = $state("");
  let apiKey = $state("");
  let isDefault = $state(true);
  let isLocal = $state(false);

  async function load() {
    loading = true;
    error = null;
    try {
      providers = (await api.listProviders()).results;
    } catch {
      error = "Could not load provider settings.";
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    editingId = null;
    label = "OpenRouter";
    baseUrl = "https://openrouter.ai/api/v1";
    model = "";
    apiKey = "";
    isDefault = providers.length === 0;
    isLocal = false;
  }

  function editProvider(provider: Provider) {
    editingId = provider.id;
    label = provider.label;
    baseUrl = provider.base_url;
    model = provider.model;
    apiKey = "";
    isDefault = provider.is_default;
    isLocal = provider.is_local;
    error = null;
  }

  async function save() {
    if (!label.trim() || !baseUrl.trim() || !model.trim()) return;
    saving = true;
    error = null;
    try {
      const data = {
        label: label.trim(),
        base_url: baseUrl.trim().replace(/\/$/, ""),
        model: model.trim(),
        ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
        is_default: isDefault,
        is_local: isLocal,
        enabled: true,
      };
      if (editingId) {
        await api.updateProvider(editingId, data);
      } else {
        await api.createProvider(data);
      }
      await load();
      void providerStore.load();
      resetForm();
    } catch {
      error = "Could not save provider settings.";
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    void load();
  });
</script>

<div class="mx-auto w-full max-w-3xl px-4 pb-5 pt-14 md:py-5">
  <h1 class="mb-1 text-xl font-semibold tracking-tight">Settings</h1>
  <p class="mb-5 text-sm text-muted-foreground">Configure the AI provider used for automatic titles and tags.</p>

  <section class="space-y-4 rounded-xl border bg-card p-4">
    <div class="flex items-start gap-3">
      <KeyRound class="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
      <div>
        <h2 class="text-sm font-medium">{editingId ? "Edit provider" : "Add provider"}</h2>
        <p class="mt-1 text-xs text-muted-foreground">
          OpenRouter uses an OpenAI-compatible endpoint. API keys are stored in Bunko's SQLite database and are never displayed again.
        </p>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-2">
      <label class="space-y-1 text-sm">
        <span class="text-muted-foreground">Name</span>
        <input bind:value={label} class="h-10 w-full rounded-md border border-input bg-background px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
      </label>
      <label class="space-y-1 text-sm">
        <span class="text-muted-foreground">Model</span>
        <input bind:value={model} placeholder="openai/gpt-4o-mini" class="h-10 w-full rounded-md border border-input bg-background px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
      </label>
    </div>

    <label class="block space-y-1 text-sm">
      <span class="text-muted-foreground">Base URL</span>
      <input bind:value={baseUrl} class="h-10 w-full rounded-md border border-input bg-background px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
    </label>

    <label class="block space-y-1 text-sm">
      <span class="text-muted-foreground">API key</span>
      <input bind:value={apiKey} type="password" autocomplete="new-password" placeholder={editingId ? "Leave blank to keep the current key" : "sk-or-v1-…"} class="h-10 w-full rounded-md border border-input bg-background px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
    </label>

    <div class="flex flex-wrap gap-4 text-sm text-muted-foreground">
      <label class="inline-flex items-center gap-2">
        <input type="checkbox" bind:checked={isDefault} />
        Use as default provider
      </label>
      <label class="inline-flex items-center gap-2">
        <input type="checkbox" bind:checked={isLocal} />
        Local provider
      </label>
    </div>

    {#if error}
      <p class="text-sm text-red-400">{error}</p>
    {/if}

    <div class="flex gap-2">
      <button
        onclick={() => void save()}
        disabled={saving || !label.trim() || !baseUrl.trim() || !model.trim()}
        class="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        <Save class="h-4 w-4" />
        {saving ? "Saving…" : editingId ? "Save changes" : "Add provider"}
      </button>
      {#if editingId}
        <button
          onclick={resetForm}
          disabled={saving}
          class="inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50"
        >
          <X class="h-4 w-4" /> Cancel
        </button>
      {/if}
    </div>
  </section>

  <section class="mt-6 space-y-2">
    <h2 class="px-1 text-sm font-medium text-muted-foreground">Configured providers</h2>
    {#if loading}
      <div class="flex items-center gap-2 py-4 text-sm text-muted-foreground">
        <Loader2 class="h-4 w-4 animate-spin" /> Loading…
      </div>
    {:else if providers.length === 0}
      <p class="rounded-xl border px-4 py-4 text-sm text-muted-foreground">No provider configured yet.</p>
    {:else}
      {#each providers as provider (provider.id)}
        <div class="flex items-center justify-between gap-3 rounded-xl border px-4 py-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-medium">{provider.label}</span>
              {#if provider.is_default}
                <span class="rounded-full bg-primary/15 px-2 py-0.5 text-xs text-primary">default</span>
              {/if}
              {#if provider.api_key_set}
                <span class="text-xs text-muted-foreground">key saved</span>
              {/if}
            </div>
            <p class="truncate text-xs text-muted-foreground">{provider.base_url} · {provider.model}</p>
          </div>
          <button
            onclick={() => editProvider(provider)}
            class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label={`Edit ${provider.label}`}
            title="Edit provider"
          >
            <Pencil class="h-4 w-4" />
          </button>
        </div>
      {/each}
    {/if}
  </section>
</div>
