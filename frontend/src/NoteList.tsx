import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, Note, Tag } from "./api";

export default function NoteList() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const q = params.get("q") || "";
  const statusFilter = params.get("status") || "";
  const tagFilter = params.get("tag") || "";

  const [notes, setNotes] = useState<Note[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listTags().then((p) => setTags(p.results)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .listNotes({
        q: q || undefined,
        tag_status: statusFilter || undefined,
        tag: tagFilter ? [tagFilter] : undefined,
      })
      .then((p) => setNotes(p.results))
      .catch(() => setNotes([]))
      .finally(() => setLoading(false));
  }, [q, statusFilter, tagFilter]);

  // Needs-tags inbox: done but with zero tags.
  const showingInbox = statusFilter === "done" && !q && !tagFilter;
  const shown = showingInbox ? notes.filter((n) => n.tags.length === 0) : notes;

  return (
    <div className="page">
      <div className="row between">
        <h1 className="h1">{showingInbox ? "Needs tags" : q ? `Search: ${q}` : "Notes"}</h1>
        <div className="row gap small">
          <Link className="btn ghost" to="/inbox">Inbox</Link>
          <Link className="btn ghost" to="/tags">Tags</Link>
        </div>
      </div>

      {tagFilter && (
        <div className="tag-row">
          <span className="chip">tag: {tagFilter}
            <button className="chip-x" onClick={() => nav("/")}>×</button>
          </span>
        </div>
      )}

      {loading && <p className="muted">Loading…</p>}
      {!loading && shown.length === 0 && (
        <p className="muted">
          {showingInbox ? "Nothing waiting for tags." : "No notes yet."}
        </p>
      )}

      <ul className="note-list">
        {shown.map((n) => (
          <li key={n.id}>
            <Link to={`/notes/${n.id}`} className="note-item">
              <span className="note-title">{n.title || "(untitled)"}</span>
              <span className="note-meta">
                {(n.tag_status === "pending" || n.tag_status === "processing") && (
                  <span className="chip pending small">tagging…</span>
                )}
                {n.tag_status === "failed" && <span className="chip failed small">failed</span>}
                {n.tags.map((t) => (
                  <span key={t.id} className="chip small">{t.name}</span>
                ))}
                <span className="dim">{new Date(n.updated_at).toLocaleDateString()}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
