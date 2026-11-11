import {
  api,
  type Folder,
  type Note,
  type Provider,
  type Tag,
  type TagsResponse,
  type User,
} from "./api";

/**
 * Small reactive data layer built on Svelte 5 runes.
 *
 * This replaces TanStack Query. The pieces that mattered are kept explicit:
 *  - a cached tag list, refetched after mutations
 *  - a note list that pages in increments of 10 for the sidebar
 *  - tag polling that stops once a note settles (done/failed)
 */

const POLL_MS = 2000;

// --- auth -----------------------------------------------------------------

class AuthStore {
  user = $state<User | null>(null);
  loaded = $state(false);
  error = $state<string | null>(null);
  pending = $state(false);

  async load() {
    try {
      this.user = await api.me();
    } catch {
      this.user = null;
    } finally {
      this.loaded = true;
    }
  }

  async login(password: string) {
    this.pending = true;
    this.error = null;
    try {
      this.user = await api.login(password);
      await tags.load();
      void providers.load();
      return true;
    } catch (e) {
      const status = (e as { status?: number }).status;
      this.error =
        status === 401
          ? "Wrong password."
          : status === 429
            ? "Too many attempts. Wait a minute."
            : "Could not sign in.";
      return false;
    } finally {
      this.pending = false;
    }
  }

  async logout() {
    try {
      await api.logout();
    } finally {
      this.user = null;
      notes.reset();
      tags.reset();
      providers.reset();
      folders.reset();
    }
  }
}

export const auth = new AuthStore();

// --- tags -----------------------------------------------------------------

class TagsStore {
  items = $state<Tag[]>([]);
  loaded = $state(false);

  async load() {
    try {
      const page = await api.listTags();
      this.items = page.results;
    } finally {
      this.loaded = true;
    }
  }

  reset() {
    this.items = [];
    this.loaded = false;
  }

  get bySlug() {
    return new Map(this.items.map((t) => [t.slug, t]));
  }
}

export const tags = new TagsStore();

// --- folders --------------------------------------------------------------

class FoldersStore {
  items = $state<Folder[]>([]);
  loaded = $state(false);

  async load() {
    try {
      this.items = await api.listFolders();
    } finally {
      this.loaded = true;
    }
  }

  reset() {
    this.items = [];
    this.loaded = false;
  }

  /** All folders as a flat list, ordered. No parent container item. */
  get rootFolders() {
    return [...this.items].sort(
      (a, b) => a.position - b.position || a.name.localeCompare(b.name)
    );
  }

  get tree() {
    const roots = this.items
      .filter((f) => !f.parent_id)
      .sort((a, b) => a.position - b.position || a.name.localeCompare(b.name));
    return roots.map((r) => ({
      ...r,
      children: this.items
        .filter((f) => f.parent_id === r.id)
        .sort((a, b) => a.position - b.position),
    }));
  }
}

export const folders = new FoldersStore();

// --- providers ------------------------------------------------------------

class ProvidersStore {
  items = $state<Provider[]>([]);
  loaded = $state(false);

  async load() {
    try {
      this.items = (await api.listProviders()).results;
    } finally {
      this.loaded = true;
    }
  }

  reset() {
    this.items = [];
    this.loaded = false;
  }

  get selected() {
    return (
      this.items.find((provider) => provider.enabled && provider.is_default) ??
      this.items.find((provider) => provider.enabled) ??
      null
    );
  }

  forNote(localOnly: boolean) {
    if (!localOnly) return this.selected;
    return (
      this.items.find((provider) => provider.enabled && provider.is_default && provider.is_local) ??
      this.items.find((provider) => provider.enabled && provider.is_local) ??
      null
    );
  }
}

export const providers = new ProvidersStore();

// --- note lists -----------------------------------------------------------

type ListFilter = { q?: string; tag?: string[]; tag_status?: string; folder?: string };

class NotesStore {
  items = $state<Note[]>([]);
  count = $state(0);
  loading = $state(false);
  loadingMore = $state(false);
  error = $state<string | null>(null);
  limit = $state(10);

  protected filter: ListFilter = {};

  get hasMore() {
    return this.items.length < this.count;
  }

  /** Fetch a fresh first page for the given filter. */
  async query(filter: ListFilter = {}) {
    this.filter = filter;
    this.limit = 10;
    this.loading = true;
    this.error = null;
    try {
      const page = await api.listNotes({ ...filter, limit: this.limit, offset: 0 });
      this.items = page.results;
      this.count = page.count;
    } catch {
      this.items = [];
      this.count = 0;
      this.error = "Could not load notes.";
    } finally {
      this.loading = false;
    }
  }

  /** Append another page (used by the sidebar's "Load more"). */
  async loadMore() {
    if (this.loadingMore || !this.hasMore) return;
    this.loadingMore = true;
    this.limit += 10;
    try {
      const page = await api.listNotes({ ...this.filter, limit: this.limit, offset: 0 });
      this.items = page.results;
      this.count = page.count;
    } catch {
      this.error = "Could not load more notes.";
    } finally {
      this.loadingMore = false;
    }
  }

  reset() {
    this.items = [];
    this.count = 0;
    this.limit = 10;
    this.loadedOnce = false;
  }

  loadedOnce = $state(false);

  /** Replace one note in place (after edit, tag change, delete). */
  patch(id: string, updater: (n: Note) => Note | null) {
    this.items = this.items.flatMap((n) => {
      if (n.id !== id) return [n];
      const next = updater(n);
      return next ? [next] : [];
    });
  }
}

export const notes = new NotesStore();

/**
 * Sidebar tree: notes grouped by folder, so each folder renders its own
 * children. Filters (text + tags) apply across every folder.
 */
class TreeStore {
  items = $state<Note[]>([]);
  loading = $state(false);
  error = $state<string | null>(null);
  loaded = $state(false);

  /** Notes per folder cap, matching the API default. */
  perFolder = 10;

  async query(filter: { q?: string; tag?: string[] } = {}) {
    this.loading = true;
    this.error = null;
    try {
      const page = await api.listNotesTree({ ...filter, per_folder: this.perFolder });
      this.items = page.results;
    } catch {
      this.error = "Could not load notes.";
      this.items = [];
    } finally {
      this.loading = false;
      this.loaded = true;
    }
  }

  /** Notes belonging to one folder (null = unfiled). */
  inFolder(folderId: string | null): Note[] {
    return this.items.filter((n) => (n.folder_id ?? null) === folderId);
  }

  patch(id: string, updater: (n: Note) => Note | null) {
    this.items = this.items.flatMap((n) => {
      if (n.id !== id) return [n];
      const next = updater(n);
      return next ? [next] : [];
    });
  }

  reset() {
    this.items = [];
    this.loaded = false;
  }
}

export const tree = new TreeStore();

// The create-note flow already has a complete Note response. Hand it to the
// note route so navigation can render immediately instead of showing a second
// loading state while fetching the same note again.
let createdNoteHandoff: Note | null = null;

export function handoffCreatedNote(note: Note) {
  createdNoteHandoff = note;
}

export function consumeCreatedNote(id: string): Note | null {
  if (createdNoteHandoff?.id !== id) return null;
  const note = createdNoteHandoff;
  createdNoteHandoff = null;
  return note;
}

/**
 * Sidebar list: most recent 10 of whatever the sidebar filters select,
 * "Load more" appends 10 more.
 */
class SidebarNotesStore extends NotesStore {
  /** Re-query using the current sidebar filter state. */
  applyFilters(filter: ListFilter) {
    this.activeFilter = filter;
    return this.query(filter);
  }

  activeFilter: ListFilter = {};

  override reset() {
    this.activeFilter = {};
    super.reset();
  }
}

export const sidebarNotes = new SidebarNotesStore();

// --- single note + tag polling -------------------------------------------

class NoteStore {
  note = $state<Note | null>(null);
  tagsState = $state<TagsResponse | null>(null);
  loading = $state(false);
  error = $state<string | null>(null);

  #timer: ReturnType<typeof setTimeout> | null = null;
  #generation = 0;

  async load(id: string, initial: Note | null = null) {
    this.loading = true;
    this.error = null;
    if (initial?.id === id) this.hydrate(initial);
    try {
      const n = await api.getNote(id);
      this.hydrate(n);
    } catch {
      if (!this.note) this.note = null;
      this.error = "Could not load this note.";
    } finally {
      this.loading = false;
    }
  }

  hydrate(n: Note) {
    this.note = n;
    this.tagsState = { tag_status: n.tag_status, tag_error: n.tag_error, tags: n.tags };
    this.#schedulePoll(n.id);
  }

  /** Poll /notes/{id}/tags until the note settles, then stop. */
  #schedulePoll(id: string) {
    this.#stopPoll();
    const status = this.tagsState?.tag_status;
    if (!status || status === "done" || status === "failed") return;

    const generation = this.#generation;
    this.#timer = setTimeout(async () => {
      if (generation !== this.#generation) return;
      try {
        const r = await api.getNoteTags(id);
        this.setTags(r);
        if (r.tag_status === "done" || r.tag_status === "failed") {
          // Tags and generated titles changed server-side.
          const updated = this.note;
          if (updated) {
            notes.patch(id, () => updated);
            sidebarNotes.patch(id, () => updated);
            tree.patch(id, () => updated);
          }
          void tags.load();
          void sidebarNotes.query();
          void tree.query();
        }
        this.#schedulePoll(id);
      } catch {
        this.#schedulePoll(id);
      }
    }, POLL_MS);
  }

  #stopPoll() {
    this.#generation += 1;
    if (this.#timer) {
      clearTimeout(this.#timer);
      this.#timer = null;
    }
  }

  setTags(r: TagsResponse) {
    this.tagsState = r;
    if (this.note) {
      this.note = {
        ...this.note,
        ...(r.title !== undefined && r.title !== null ? { title: r.title } : {}),
        tag_status: r.tag_status,
        tag_error: r.tag_error,
      };
      this.#schedulePoll(this.note.id);
    }
  }

  setNote(n: Note) {
    this.note = n;
  }

  dispose() {
    this.#stopPoll();
  }
}

export function createNoteStore() {
  return new NoteStore();
}
