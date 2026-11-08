import { useEffect, useRef, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { Loader2, Menu, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SidebarNav } from "./Sidebar";
import Login from "./Login";
import NoteList from "./NoteList";
import NoteView from "./NoteView";
import Scratchpad from "./Scratchpad";
import Tags from "./Tags";
import { useMe } from "./queries";
import { cn } from "./lib/utils";

function SearchOverlay({ onClose }: { onClose: () => void }) {
  const [q, setQ] = useState("");
  const nav = useNavigate();
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    nav(`/?q=${encodeURIComponent(q.trim())}`);
    onClose();
  }

  return (
    <form
      onSubmit={submit}
      className="flex items-center gap-2 border-b bg-background px-3 py-2"
    >
      <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
      <Input
        ref={ref}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search notes…"
        className="h-10 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
        aria-label="Search notes"
        onKeyDown={(e) => e.key === "Escape" && onClose()}
      />
      <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close search">
        <X className="h-5 w-5" />
      </Button>
    </form>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const [searching, setSearching] = useState(false);
  const [params] = useSearchParams();
  const location = useLocation();

  // `/` opens search unless the user is already typing somewhere (spec 8).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null;
      const typing =
        !!t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable);
      if (e.key === "/" && !typing && !searching) {
        e.preventDefault();
        setSearching(true);
      }
      if (e.key === "Escape") {
        if (searching) setSearching(false);
        if (drawer) setDrawer(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [searching, drawer]);

  // Close the drawer on navigation.
  useEffect(() => {
    setDrawer(false);
  }, [location.pathname, params.toString()]);

  return (
    <div className="flex min-h-dvh">
      {/* Desktop rail */}
      <aside className="hidden w-56 shrink-0 border-r bg-card/40 md:block">
        <div className="sticky top-0 h-dvh">
          <SidebarNav />
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawer && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setDrawer(false)}
            aria-hidden="true"
          />
          {/* 90% of the viewport on phones; the rail takes over at md. */}
          <div className="absolute inset-y-0 left-0 w-[90%] border-r bg-card shadow-xl">
            <SidebarNav onNavigate={() => setDrawer(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-1 border-b bg-background/95 px-2 py-1.5 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="px-2 text-sm font-semibold tracking-tight md:hidden">
            easy-notes
          </span>
          <div className="ml-auto">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSearching(true)}
              aria-label="Search"
            >
              <Search className="h-5 w-5" />
            </Button>
          </div>
        </header>

        {searching && <SearchOverlay onClose={() => setSearching(false)} />}

        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Scratchpad />} />
      <Route path="/inbox" element={<NoteList inbox />} />
      <Route path="/notes/:id" element={<NoteView />} />
      <Route path="/tags" element={<Tags />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const me = useMe();

  // While the auth probe is in flight, show nothing rather than the app,
  // so a signed-out visitor never sees the note UI (even briefly).
  if (me.isPending) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!me.data) return <Login />;

  return (
    <BrowserRouter>
      <Shell>
        <AppRoutes />
      </Shell>
    </BrowserRouter>
  );
}

export { cn };
