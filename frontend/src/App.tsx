import React, { useEffect, useRef, useState } from "react";
import { BrowserRouter, Route, Routes, useNavigate } from "react-router-dom";
import NoteList from "./NoteList";
import NoteView from "./NoteView";
import Scratchpad from "./Scratchpad";
import Tags from "./Tags";

function SearchBar() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const nav = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  // `/` focuses search (spec 8), unless already typing in a field.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement;
      const typing =
        t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if (e.key === "/" && !typing) {
        e.preventDefault();
        setOpen(true);
        setTimeout(() => inputRef.current?.focus(), 0);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
        setQ("");
        inputRef.current?.blur();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    nav(`/?q=${encodeURIComponent(q.trim())}`);
    setOpen(false);
  }

  if (!open) {
    return (
      <button className="search-trigger" onClick={() => setOpen(true)} aria-label="Search">
        <span aria-hidden="true">⌕</span>
      </button>
    );
  }

  return (
    <form className="search-form" onSubmit={submit}>
      <input
        ref={inputRef}
        className="input"
        placeholder="Search notes…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onBlur={() => !q && setOpen(false)}
      />
    </form>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="topbar">
          <span className="brand">easy-notes</span>
          <SearchBar />
        </header>
        <main className="main">
          <Routes>
            <Route path="/" element={<Scratchpad />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/notes/:id" element={<NoteView />} />
            <Route path="/tags" element={<Tags />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

function Inbox() {
  return <NoteListWrapper status="done" />;
}

// NoteList reads filters from the URL; render it with a forced status.
function NoteListWrapper({ status }: { status: string }) {
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.pathname === "/inbox") {
      url.pathname = "/";
      url.searchParams.set("status", status);
      window.history.replaceState({}, "", url);
    }
  }, [status]);
  return <NoteList />;
}
