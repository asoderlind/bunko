import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Tag } from "./api";

const slugify = (s: string) =>
  s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

export default function Tags() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [mergeFrom, setMergeFrom] = useState<Tag | null>(null);
  const [mergeInto, setMergeInto] = useState("");

  const load = () => api.listTags().then((p) => setTags(p.results)).catch(() => {});
  useEffect(() => { void load(); }, []);

  async function create() {
    const slug = slugify(name);
    if (!slug) return;
    try {
      setError(null);
      await api.createTag({ slug, name: name.trim(), description: description.trim() });
      setName("");
      setDescription("");
      await load();
    } catch {
      setError("Could not create tag — it may already exist.");
    }
  }

  async function doMerge() {
    if (!mergeFrom || !mergeInto) return;
    try {
      setError(null);
      await api.mergeTag(mergeFrom.id, mergeInto);
      setMergeFrom(null);
      setMergeInto("");
      await load();
    } catch {
      setError("Merge failed.");
    }
  }

  return (
    <div className="page">
      <div className="row between">
        <h1 className="h1">Tags</h1>
        <Link className="btn ghost" to="/">← Notes</Link>
      </div>

      {error && <div className="banner err">{error}</div>}

      <div className="card">
        <h2 className="h2">New tag</h2>
        <input
          className="input"
          placeholder="Name (e.g. Trading)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="input"
          placeholder="One line: what belongs in this tag?"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={200}
        />
        <p className="muted small">
          Slug: <code>{slugify(name) || "—"}</code> — the description is load-bearing;
          it is how the model tells similar tags apart.
        </p>
        <button className="btn primary" onClick={() => void create()} disabled={!slugify(name)}>
          Create
        </button>
      </div>

      <ul className="note-list">
        {tags.map((t) => (
          <li key={t.id} className="tag-item">
            <div>
              <span className="tag-name">{t.name}</span>
              <span className="dim small"> /{t.slug} · {t.note_count} note{t.note_count === 1 ? "" : "s"}</span>
              {t.description && <div className="muted small">{t.description}</div>}
            </div>
            <button className="btn ghost small" onClick={() => setMergeFrom(t)}>
              Merge…
            </button>
          </li>
        ))}
      </ul>

      {mergeFrom && (
        <div className="modal-backdrop" onClick={() => setMergeFrom(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2">Merge “{mergeFrom.name}” into…</h2>
            <select className="input" value={mergeInto} onChange={(e) => setMergeInto(e.target.value)}>
              <option value="">Choose target tag</option>
              {tags.filter((t) => t.id !== mergeFrom.id).map((t) => (
                <option key={t.id} value={t.slug}>{t.name}</option>
              ))}
            </select>
            <p className="muted small">
              All notes tagged “{mergeFrom.name}” move to the target. Duplicates are
              collapsed. “{mergeFrom.name}” is then deleted.
            </p>
            <div className="row gap">
              <button className="btn primary" onClick={() => void doMerge()} disabled={!mergeInto}>
                Merge
              </button>
              <button className="btn ghost" onClick={() => setMergeFrom(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
