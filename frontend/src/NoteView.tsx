import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, Note, TagsResponse } from "./api";

const POLL_MS = 2000;

export default function NoteView() {
  const { id } = useParams<{ id: string }>();
  const [note, setNote] = useState<Note | null>(null);
  const [body, setBody] = useState("");
  const [tagState, setTagState] = useState<TagsResponse | null>(null);
  const [allTags, setAllTags] = useState<{ slug: string; name: string }[]>([]);
  const [adding, setAdding] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    api
      .getNote(id)
      .then((n) => {
        if (!alive) return;
        setNote(n);
        setBody(n.body_md);
        setTagState({ tag_status: n.tag_status, tag_error: n.tag_error, tags: n.tags });
      })
      .catch(() => setError("Could not load note."));
    api.listTags().then((p) => alive && setAllTags(p.results)).catch(() => {});
    return () => {
      alive = false;
    };
  }, [id]);

  // Poll tags until tagging settles (spec 8).
  useEffect(() => {
    if (!id) return;
    const status = tagState?.tag_status;
    if (!status || status === "done" || status === "failed") return;
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const r = await api.getNoteTags(id);
        if (!cancelled) setTagState(r);
      } catch {
        /* keep polling */
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [id, tagState?.tag_status]);

  async function saveBody() {
    if (!id || !note) return;
    try {
      const updated = await api.updateNote(id, { body_md: body });
      setNote(updated);
      setTagState({ tag_status: updated.tag_status, tag_error: updated.tag_error, tags: updated.tags });
      setEditing(false);
      setDirty(false);
    } catch {
      setError("Could not save changes.");
    }
  }

  async function removeTag(tagId: string) {
    if (!id) return;
    try {
      setTagState(await api.removeNoteTag(id, tagId));
    } catch {
      setError("Could not remove tag.");
    }
  }

  async function addTag(slug: string) {
    if (!id || !slug) return;
    try {
      setTagState(await api.addNoteTag(id, slug));
      setAdding("");
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) setError("That tag does not exist.");
      else setError("Could not add tag.");
    }
  }

  async function del() {
    if (!id) return;
    if (!confirm("Delete this note?")) return;
    await api.deleteNote(id);
    window.location.href = "/";
  }

  if (error && !note) return <div className="page"><div className="banner err">{error}</div></div>;
  if (!note) return <div className="page muted">Loading…</div>;

  const status = tagState?.tag_status ?? note.tag_status;
  const tagging = status === "pending" || status === "processing";
  const knownSlugs = new Set((tagState?.tags ?? []).map((t) => t.slug));

  return (
    <div className="page note-view">
      <div className="row between">
        <Link to="/" className="back">← Back</Link>
        <button className="btn ghost danger" onClick={() => void del()}>Delete</button>
      </div>

      {error && <div className="banner err">{error}</div>}

      <div className="tag-row">
        {tagging && <span className="chip pending">tagging…</span>}
        {status === "failed" && (
          <span className="chip failed" title={tagState?.tag_error || note.tag_error}>
            tagging failed
          </span>
        )}
        {(tagState?.tags ?? []).map((t) => (
          <span key={t.id} className={`chip ${t.source}`}>
            {t.name}
            <button
              className="chip-x"
              aria-label={`Remove ${t.name}`}
              onClick={() => void removeTag(t.tag_id)}
            >
              ×
            </button>
          </span>
        ))}

        {!tagging && (
          <select
            className="tag-add"
            value={adding}
            onChange={(e) => void addTag(e.target.value)}
            aria-label="Add tag"
          >
            <option value="">+ tag</option>
            {allTags
              .filter((t) => !knownSlugs.has(t.slug))
              .map((t) => (
                <option key={t.slug} value={t.slug}>
                  {t.name}
                </option>
              ))}
          </select>
        )}
      </div>

      {status === "failed" && tagState?.tag_error && (
        <p className="muted small">{tagState.tag_error}</p>
      )}

      {editing ? (
        <>
          <textarea
            className="editor"
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
              setDirty(true);
            }}
            spellCheck={false}
          />
          <div className="row gap">
            <button className="btn primary" onClick={() => void saveBody()} disabled={!dirty}>
              Save
            </button>
            <button
              className="btn ghost"
              onClick={() => {
                setBody(note.body_md);
                setEditing(false);
                setDirty(false);
              }}
            >
              Cancel
            </button>
            <span className="hint">Editing resets tagging</span>
          </div>
        </>
      ) : (
        <pre className="note-body" onClick={() => setEditing(true)}>
          {note.body_md}
        </pre>
      )}
    </div>
  );
}
