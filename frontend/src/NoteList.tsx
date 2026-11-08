import { Link, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { TagPill } from "@/components/tag-colors";
import { useNotes } from "@/queries";

export default function NoteList({ inbox = false }: { inbox?: boolean }) {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const tagFilter = params.get("tag") || "";

  const notes = useNotes({
    q: q || undefined,
    tag: tagFilter ? [tagFilter] : undefined,
    // The needs-tags inbox is "tagged, but nothing was applied" (spec 6).
    tag_status: inbox ? "done" : undefined,
  });

  const all = notes.data?.results ?? [];
  const shown = inbox ? all.filter((n) => n.tags.length === 0) : all;

  const heading = inbox ? "Needs tags" : q ? `Search: ${q}` : "Notes";

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold tracking-tight">{heading}</h1>
        {tagFilter && <Badge variant="muted">tag: {tagFilter}</Badge>}
      </div>

      {notes.isPending && (
        <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}

      {notes.isError && (
        <p className="py-6 text-sm text-red-400">Could not load notes.</p>
      )}

      {!notes.isPending && shown.length === 0 && (
        <p className="py-6 text-sm text-muted-foreground">
          {inbox ? "Nothing waiting for tags." : q ? "No matches." : "No notes yet."}
        </p>
      )}

      <ul className="divide-y">
        {shown.map((n) => (
          <li key={n.id}>
            <Link
              to={`/notes/${n.id}`}
              className="block min-h-11 py-3.5 transition-colors hover:bg-accent/40"
            >
              <span className="block truncate">{n.title || "(untitled)"}</span>
              <span className="mt-1.5 flex flex-wrap items-center gap-1.5">
                {(n.tag_status === "pending" || n.tag_status === "processing") && (
                  <Badge variant="muted">tagging…</Badge>
                )}
                {n.tag_status === "failed" && (
                  <Badge variant="destructive">failed</Badge>
                )}
                {n.tags.map((t) => (
                  <TagPill key={t.id} name={t.name} color={t.color} />
                ))}
                <span className="text-xs text-muted-foreground/70">
                  {new Date(n.updated_at).toLocaleDateString()}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
