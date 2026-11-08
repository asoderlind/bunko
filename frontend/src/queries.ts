import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { api, Note, TagsResponse, User } from "./api";

export const qk = {
  me: ["me"] as const,
  notes: (params: object) => ["notes", params] as const,
  note: (id: string) => ["note", id] as const,
  noteTags: (id: string) => ["note-tags", id] as const,
  tags: ["tags"] as const,
};

/** Auth state. `data === null` means signed out; `undefined` means still loading. */
export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: api.me,
    staleTime: 30_000,
    retry: false,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (password: string) => api.login(password),
    onSuccess: (user) => {
      qc.setQueryData<User | null>(qk.me, user);
      // Everything else was fetched anonymously; refetch from scratch.
      void qc.invalidateQueries();
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      qc.clear();
      qc.setQueryData<User | null>(qk.me, null);
    },
  });
}

export function useNotes(params: {
  q?: string;
  tag?: string[];
  tag_status?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: qk.notes(params),
    queryFn: () => api.listNotes(params),
    placeholderData: keepPreviousData,
  });
}

/** Bounded, recency-ordered list for the sidebar. */
export const SIDEBAR_LIMIT = 30;

export function useSidebarNotes() {
  return useQuery({
    queryKey: ["notes", "sidebar", SIDEBAR_LIMIT],
    queryFn: () => api.listNotes({ limit: SIDEBAR_LIMIT }),
    select: (p) => p.results,
  });
}

export function useNote(id: string | undefined) {
  return useQuery({
    queryKey: qk.note(id ?? ""),
    queryFn: () => api.getNote(id!),
    enabled: !!id,
  });
}

/**
 * Note tags, polled until tagging settles.
 * Polling stops on `done`/`failed` so a finished note costs nothing.
 */
export function useNoteTags(id: string | undefined, initial?: TagsResponse) {
  return useQuery({
    queryKey: qk.noteTags(id ?? ""),
    queryFn: () => api.getNoteTags(id!),
    enabled: !!id,
    placeholderData: initial,
    refetchInterval: (query) => {
      const s = query.state.data?.tag_status;
      return s === "pending" || s === "processing" ? 2000 : false;
    },
  });
}

export function useCreateNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ body, localOnly }: { body: string; localOnly?: boolean }) =>
      api.createNote(body, localOnly),
    onSuccess: (note: Note) => {
      qc.setQueryData(qk.note(note.id), note);
      void qc.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useUpdateNote(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Parameters<typeof api.updateNote>[1]) =>
      api.updateNote(id, patch),
    onSuccess: (note) => {
      qc.setQueryData(qk.note(note.id), note);
      qc.setQueryData(qk.noteTags(note.id), {
        tag_status: note.tag_status,
        tag_error: note.tag_error,
        tags: note.tags,
      } satisfies TagsResponse);
      void qc.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useDeleteNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteNote(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}

export function useTags() {
  return useQuery({
    queryKey: qk.tags,
    queryFn: api.listTags,
    select: (p) => p.results,
  });
}

function useTagsResponseMutation(
  fn: (args: { id: string; tagId?: string; slug?: string }) => Promise<TagsResponse>
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (data, vars) => {
      qc.setQueryData(qk.noteTags(vars.id), data);
      // Tag usage counts change server-side.
      void qc.invalidateQueries({ queryKey: qk.tags });
      void qc.invalidateQueries({ queryKey: qk.note(vars.id) });
    },
  });
}

export function useAddNoteTag(noteId: string) {
  return useTagsResponseMutation(({ slug }) => api.addNoteTag(noteId, slug!));
}

export function useRemoveNoteTag(noteId: string) {
  return useTagsResponseMutation(({ tagId }) => api.removeNoteTag(noteId, tagId!));
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createTag,
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.tags }),
  });
}

export function useMergeTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, mergeInto }: { id: string; mergeInto: string }) =>
      api.mergeTag(id, mergeInto),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.tags });
      void qc.invalidateQueries({ queryKey: ["notes"] });
    },
  });
}
