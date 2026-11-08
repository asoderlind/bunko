import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "./api";

const DRAFT_KEY = "easy-notes.draft";

export default function Scratchpad() {
  const nav = useNavigate();
  const [body, setBody] = useState(() => localStorage.getItem(DRAFT_KEY) || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  // Draft persisted on every keystroke (spec 8).
  useEffect(() => {
    if (body) localStorage.setItem(DRAFT_KEY, body);
    else localStorage.removeItem(DRAFT_KEY);
  }, [body]);

  const save = useCallback(async () => {
    if (saving) return;
    if (!body.trim()) return; // empty notes are never created
    setSaving(true);
    setError(null);
    try {
      const note = await api.createNote(body);
      localStorage.removeItem(DRAFT_KEY);
      setBody("");
      nav(`/notes/${note.id}`);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        setAuthRequired(true);
      } else {
        setError("Could not save. Your text is kept in this browser.");
      }
    } finally {
      setSaving(false);
    }
  }, [body, nav, saving]);

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void save();
    }
  }

  const hasText = body.trim().length > 0;

  return (
    <div className="scratchpad">
      {authRequired && (
        <div className="banner warn">
          Not signed in.{" "}
          <a href="/admin/login/?next=/">Sign in</a> to save notes.
        </div>
      )}
      {error && <div className="banner err">{error}</div>}

      <textarea
        ref={ref}
        className="scratchpad-input"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Write something…"
        spellCheck={false}
        aria-label="New note"
      />

      {hasText && (
        <div className="scratchpad-bar">
          <button className="btn primary" onClick={() => void save()} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
          <span className="hint">⌘/Ctrl + Enter</span>
        </div>
      )}
    </div>
  );
}
