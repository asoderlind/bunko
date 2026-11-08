import { api, type Folder, type Note, type Tag, type TagsResponse, type User } from "./api";

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

  async load(id: string) {
    this.loading = true;
    this.error = null;
    try {
      const n = await api.getNote(id);
      this.note = n;
      this.tagsState = { tag_status: n.tag_status, tag_error: n.tag_error, tags: n.tags };
      this.#schedulePoll(id);
    } catch {
      this.note = null;
      this.error = "Could not load this note.";
    } finally {
      this.loading = false;
    }
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
        this.tagsState = r;
        if (this.note) this.note = { ...this.note, tag_status: r.tag_status, tag_error: r.tag_error };
        if (r.tag_status === "done" || r.tag_status === "failed") {
          // Tags/usage counts changed server-side.
          void tags.load();
          void sidebarNotes.query();
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
      this.note = { ...this.note, tag_status: r.tag_status, tag_error: r.tag_error };
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
