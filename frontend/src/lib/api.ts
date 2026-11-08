export type TagOnNote = {
  id: string;
  tag_id: string;
  slug: string;
  name: string;
  color: string;
  source: "auto" | "manual";
  confidence: number | null;
};

export type TagStatus = "pending" | "processing" | "done" | "failed";

export type TitleSource = "derived" | "generated" | "user";

export type Note = {
  id: string;
  body_md: string;
  title: string;
  title_source: TitleSource;
  tags: TagOnNote[];
  tag_status: TagStatus;
  tag_error: string;
  local_only: boolean;
  created_at: string;
  updated_at: string;
};

export type TagsResponse = {
  tag_status: TagStatus;
  tag_error: string;
  tags: TagOnNote[];
};

export type Tag = {
  id: string;
  slug: string;
  name: string;
  description: string;
  color: string;
  note_count: number;
};

export type User = { id: number; username: string };

export type Page<T> = {
  count: number;
  next: boolean | string | null;
  previous: boolean | string | null;
  results: T[];
};

const BASE = "/api";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[2]) : null;
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...((opts.headers as Record<string, string>) || {}),
  };
  if (opts.body) headers["Content-Type"] = "application/json";

  const method = (opts.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = getCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  const res = await fetch(BASE + path, {
    ...opts,
    headers,
    credentials: "same-origin",
  });

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const body = text ? safeJson(text) : null;
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

function safeJson(t: string): unknown {
  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

export const api = {
  me: () => request<User | null>("/user/"),
  login: (password: string) =>
    request<User>("/auth/login/", { method: "POST", body: JSON.stringify({ password }) }),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),

  listNotes: (
    p: { q?: string; tag?: string[]; tag_status?: string; limit?: number; offset?: number } = {}
  ) => {
    const sp = new URLSearchParams();
    if (p.q) sp.set("q", p.q);
    if (p.tag_status) sp.set("tag_status", p.tag_status);
    if (p.limit) sp.set("limit", String(p.limit));
    if (p.offset) sp.set("offset", String(p.offset));
    (p.tag || []).forEach((t) => sp.append("tag", t));
    const qs = sp.toString();
    return request<Page<Note>>(`/notes/${qs ? "?" + qs : ""}`);
  },

  getNote: (id: string) => request<Note>(`/notes/${id}/`),

  createNote: (body_md: string, local_only = false) =>
    request<Note>("/notes/", { method: "POST", body: JSON.stringify({ body_md, local_only }) }),

  updateNote: (id: string, patch: Partial<Pick<Note, "body_md" | "title" | "local_only">>) =>
    request<Note>(`/notes/${id}/`, { method: "PATCH", body: JSON.stringify(patch) }),

  deleteNote: (id: string) => request<void>(`/notes/${id}/`, { method: "DELETE" }),

  getNoteTags: (id: string) => request<TagsResponse>(`/notes/${id}/tags/`),

  addNoteTag: (id: string, slug: string) =>
    request<TagsResponse>(`/notes/${id}/tags/`, {
      method: "POST",
      body: JSON.stringify({ slug }),
    }),

  removeNoteTag: (id: string, tagId: string) =>
    request<TagsResponse>(`/notes/${id}/tags/${tagId}/`, { method: "DELETE" }),

  listTags: () => request<Page<Tag>>("/tags/"),

  createTag: (data: { slug: string; name: string; description?: string }) =>
    request<Tag>("/tags/", { method: "POST", body: JSON.stringify(data) }),

  updateTag: (
    id: string,
    data: Partial<{ slug: string; name: string; description: string; color: string }>
  ) => request<Tag>(`/tags/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),

  mergeTag: (id: string, merge_into: string) =>
    request<Tag>(`/tags/${id}/merge/`, { method: "POST", body: JSON.stringify({ merge_into }) }),
};

export const slugify = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
