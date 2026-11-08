import { useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useSearchParams } from "react-router-dom";
import {
  ChevronDown,
  Filter,
  Inbox,
  LogOut,
  MoreHorizontal,
  NotebookPen,
  Pencil,
  Tag as TagIcon,
  Trash2,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TagCheckbox, TagPill } from "@/components/tag-colors";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Note } from "@/api";
import {
  useDeleteNote,
  useLogout,
  useSidebarNotes,
  useTags,
  useUpdateNote,
} from "@/queries";

const NAV = [
  { to: "/", label: "New note", icon: NotebookPen, end: true },
  { to: "/inbox", label: "Needs tags", icon: Inbox, end: false },
  { to: "/tags", label: "Tags", icon: TagIcon, end: false },
];

/** Download a note as a markdown file. */
export function downloadNote(note: Note) {
  const safe =
    (note.title || "note")
      .replace(/[^\p{L}\p{N}\s-]/gu, "")
      .trim()
      .replace(/\s+/g, "-")
      .slice(0, 60) || "note";
  const front = [
    "---",
    `title: ${JSON.stringify(note.title || "")}`,
    `created: ${note.created_at}`,
    `updated: ${note.updated_at}`,
    note.tags.length ? `tags: [${note.tags.map((t) => t.slug).join(", ")}]` : null,
    "---",
    "",
  ]
    .filter((l) => l !== null)
    .join("\n");
  const blob = new Blob([front + note.body_md + "\n"], {
    type: "text/markdown;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${safe}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function TagFilter({ onNavigate }: { onNavigate?: () => void }) {
  const [open, setOpen] = useState(false);
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const tags = useTags();

  const selected = useMemo(() => new Set(params.getAll("tag")), [params]);

  function toggle(slug: string) {
    const next = new URLSearchParams(params);
    const current = next.getAll("tag");
    next.delete("tag");
    const updated = current.includes(slug)
      ? current.filter((s) => s !== slug)
      : [...current, slug];
    updated.forEach((s) => next.append("tag", s));
    navigate({ pathname: "/", search: next.toString() });
    onNavigate?.();
  }

  function clear() {
    const next = new URLSearchParams(params);
    next.delete("tag");
    navigate({ pathname: "/", search: next.toString() });
  }

  const count = selected.size;

  return (
    <div className="px-1">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground"
        aria-expanded={open}
      >
        <Filter className="h-4 w-4 shrink-0" />
        <span>Filter</span>
        {count > 0 && (
          <span className="rounded-full bg-primary/20 px-1.5 text-xs text-primary">
            {count}
          </span>
        )}
        <ChevronDown
          className={cn("ml-auto h-4 w-4 transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="mt-1 space-y-0.5 pl-1">
          {(tags.data ?? []).length === 0 && (
            <p className="px-2 py-1 text-xs text-muted-foreground">No tags yet.</p>
          )}
          {(tags.data ?? []).map((t) => {
            const checked = selected.has(t.slug);
            return (
              <label
                key={t.id}
                className="flex min-h-9 cursor-pointer items-center gap-2 rounded-md px-2 text-sm hover:bg-accent/50"
              >
                <input
                  type="checkbox"
                  className="sr-only"
                  checked={checked}
                  onChange={() => toggle(t.slug)}
                />
                <TagCheckbox color={t.color} checked={checked} />
                <span className="truncate">{t.name}</span>
                <span className="ml-auto shrink-0 text-xs text-muted-foreground/70">
                  {t.note_count}
                </span>
              </label>
            );
          })}
          {count > 0 && (
            <button
              onClick={clear}
              className="mt-1 min-h-9 w-full rounded-md px-2 text-left text-xs text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            >
              Clear filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function RenameDialog({
  note,
  onClose,
}: {
  note: Note | null;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(note?.title ?? "");
  const update = useUpdateNote(note?.id ?? "");

  // Reset the field whenever a different note is opened.
  const [lastId, setLastId] = useState(note?.id);
  if (note && note.id !== lastId) {
    setLastId(note.id);
    setTitle(note.title);
  }

  function save() {
    if (!note) return;
    update.mutate(
      { title: title.trim() },
      { onSuccess: onClose }
    );
  }

  return (
    <Dialog open={!!note} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change title</DialogTitle>
          <DialogDescription>
            A title you set is kept when the note is re-tagged.
          </DialogDescription>
        </DialogHeader>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
          }}
          placeholder="Title"
          aria-label="Title"
          maxLength={200}
          autoFocus
        />
        <div className="flex gap-2">
          <Button onClick={save} disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save"}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function NoteLinks({ onNavigate }: { onNavigate?: () => void }) {
  const notes = useSidebarNotes();
  const del = useDeleteNote();
  const [renaming, setRenaming] = useState<Note | null>(null);

  if (notes.isPending) {
    return <p className="px-2 py-1 text-xs text-muted-foreground">Loading…</p>;
  }
  if (!notes.data?.length) {
    return <p className="px-2 py-1 text-xs text-muted-foreground">No notes yet.</p>;
  }

  return (
    <>
      <ul className="space-y-px">
        {notes.data.map((n) => {
          const pills = n.tags.slice(0, 2);
          const overflow = n.tags.length - pills.length;
          return (
            <li key={n.id} className="group/row relative">
              <NavLink
                to={`/notes/${n.id}`}
                onClick={onNavigate}
                title={n.title || undefined}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-9 items-center gap-2 rounded-md py-1 pl-2 pr-1 text-sm transition-colors",
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  )
                }
              >
                <span className="min-w-0 flex-1 truncate">
                  {n.title || "(untitled)"}
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  {pills.map((t) => (
                    <TagPill
                      key={t.id}
                      name={t.name}
                      color={t.color}
                      className="max-w-20 px-1.5 py-0 text-[10px]"
                    />
                  ))}
                  {overflow > 0 && (
                    <span className="text-[10px] text-muted-foreground/70">
                      +{overflow}
                    </span>
                  )}
                </span>
              </NavLink>

              {/* Three-dots menu. Sits outside the link so tapping it does not navigate. */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    className="absolute right-0.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-background/80 hover:text-foreground focus-visible:opacity-100 data-[state=open]:bg-background/80 data-[state=open]:opacity-100 md:group-hover/row:opacity-100 [@media(hover:none)]:opacity-100"
                    aria-label={`Actions for ${n.title || "note"}`}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onSelect={() => {
                      downloadNote(n);
                      onNavigate?.();
                    }}
                  >
                    <Download className="h-4 w-4" /> Download
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onSelect={() => {
                      setRenaming(n);
                    }}
                  >
                    <Pencil className="h-4 w-4" /> Change title
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    destructive
                    onSelect={() => {
                      if (!confirm(`Delete “${n.title || "this note"}”?`)) return;
                      del.mutate(n.id, { onSuccess: () => onNavigate?.() });
                    }}
                  >
                    <Trash2 className="h-4 w-4" /> Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </li>
          );
        })}
      </ul>

      <RenameDialog note={renaming} onClose={() => setRenaming(null)} />
    </>
  );
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const logout = useLogout();

  return (
    <div className="flex h-full flex-col">
      <nav className="shrink-0 space-y-1 p-3 pb-2">
        <div className="px-2 pb-2 pt-1 text-sm font-semibold tracking-tight text-muted-foreground">
          easy-notes
        </div>

        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}

        <TagFilter onNavigate={onNavigate} />
      </nav>

      <div className="flex min-h-0 flex-1 flex-col border-t px-3 pt-2">
        <Link
          to="/"
          onClick={onNavigate}
          className="px-2 pb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground/70 hover:text-foreground"
        >
          Recent notes
        </Link>
        <div className="min-h-0 flex-1 overflow-y-auto pb-2">
          <NoteLinks onNavigate={onNavigate} />
        </div>
      </div>

      <div className="shrink-0 border-t p-3">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 px-3 text-muted-foreground"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </div>
  );
}
