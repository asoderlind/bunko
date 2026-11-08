import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TagPill } from "@/components/tag-colors";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { ApiError, TagStatus } from "@/api";
import {
  useAddNoteTag,
  useDeleteNote,
  useNote,
  useNoteTags,
  useRemoveNoteTag,
  useTags,
  useUpdateNote,
} from "@/queries";

function StatusBadge({ status, error }: { status: TagStatus; error?: string }) {
  if (status === "pending" || status === "processing") {
    return (
      <Badge variant="muted" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" /> tagging…
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge variant="destructive" title={error}>
        tagging failed
      </Badge>
    );
  }
  return null;
}

export default function NoteView() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const note = useNote(id);
  const tagsQ = useNoteTags(
    id,
    note.data
      ? {
          tag_status: note.data.tag_status,
          tag_error: note.data.tag_error,
          tags: note.data.tags,
        }
      : undefined
  );
  const allTags = useTags();
  const addTag = useAddNoteTag(id ?? "");
  const removeTag = useRemoveNoteTag(id ?? "");
  const update = useUpdateNote(id ?? "");
  const del = useDeleteNote();

  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState("");
  const [title, setTitle] = useState("");

  useEffect(() => {
    if (note.data && !editing) {
      setBody(note.data.body_md);
      setTitle(note.data.title);
    }
  }, [note.data, editing]);

  if (note.isPending) {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    );
  }
  if (note.isError || !note.data) {
    return (
      <div className="mx-auto max-w-3xl p-5 text-sm text-red-400">
        Could not load this note.
      </div>
    );
  }

  const n = note.data;
  const status = tagsQ.data?.tag_status ?? n.tag_status;
  const errorText = tagsQ.data?.tag_error ?? n.tag_error;
  const chips = tagsQ.data?.tags ?? n.tags;
  const tagging = status === "pending" || status === "processing";
  const known = new Set(chips.map((c) => c.slug));
  const available = (allTags.data ?? []).filter((t) => !known.has(t.slug));

  function save() {
    const current = note.data;
    if (!current || !body.trim()) return;
    update.mutate(
      {
        body_md: body,
        // Only send the title if the user actually changed it, so a generated
        // title is not silently converted into a user title.
        ...(title.trim() !== current.title ? { title: title.trim() } : {}),
      },
      { onSuccess: () => setEditing(false) }
    );
  }

  function onDelete() {
    if (!confirm("Delete this note?")) return;
    del.mutate(n.id, { onSuccess: () => nav("/", { replace: true }) });
  }

  const addTagError =
    addTag.error instanceof ApiError && addTag.error.status === 400
      ? "That tag does not exist."
      : addTag.error
        ? "Could not add tag."
        : null;

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <Button variant="ghost" asChild className="-ml-2 px-2">
          <Link to="/">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
        </Button>
        <Button variant="ghost" className="text-red-400" onClick={onDelete}>
          Delete
        </Button>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-1.5">
        <StatusBadge status={status} error={errorText} />

        {chips.map((t) => (
          <TagPill key={t.id} name={t.name} color={t.color} className="gap-0.5 py-0.5 pl-2.5 pr-1">
            <button
              className="ml-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full opacity-60 hover:opacity-100"
              aria-label={`Remove ${t.name}`}
              onClick={() => removeTag.mutate({ id: n.id, tagId: t.tag_id })}
            >
              ×
            </button>
          </TagPill>
        ))}

        {!tagging && available.length > 0 && (
          <Select
            className="h-8 w-auto min-w-24 px-2 text-xs"
            value=""
            onChange={(e) => e.target.value && addTag.mutate({ id: n.id, slug: e.target.value })}
            aria-label="Add tag"
          >
            <option value="">+ tag</option>
            {available.map((t) => (
              <option key={t.id} value={t.slug}>
                {t.name}
              </option>
            ))}
          </Select>
        )}
      </div>

      {addTagError && <p className="mb-2 text-sm text-red-400">{addTagError}</p>}
      {status === "failed" && errorText && (
        <p className="mb-2 text-sm text-muted-foreground">{errorText}</p>
      )}

      {editing ? (
        <div className="space-y-3">
          <div>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title"
              aria-label="Title"
              maxLength={200}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              {n.title_source === "user"
                ? "Your title is kept when the note is re-tagged."
                : "Leave empty to let the title be generated from the note."}
            </p>
          </div>
          <Textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="min-h-[45vh] resize-y py-3 text-[16px] leading-relaxed"
            autoFocus
          />
          <div className="flex items-center gap-2">
            <Button onClick={save} disabled={update.isPending || !body.trim()}>
              {update.isPending ? "Saving…" : "Save"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setBody(n.body_md);
                setTitle(n.title);
                setEditing(false);
              }}
            >
              Cancel
            </Button>
            <span className="text-sm text-muted-foreground">Editing re-tags the note</span>
          </div>
          {update.isError && (
            <p className="text-sm text-red-400">Could not save changes.</p>
          )}
        </div>
      ) : (
        <>
          <h2
            className="mb-1 cursor-text text-lg font-semibold tracking-tight"
            onClick={() => setEditing(true)}
          >
            {n.title || "(untitled)"}
          </h2>
          <pre
            className="cursor-text whitespace-pre-wrap break-words pb-10 pt-1 text-[16px] leading-relaxed"
            onClick={() => setEditing(true)}
          >
            {n.body_md}
          </pre>
        </>
      )}
    </div>
  );
}
