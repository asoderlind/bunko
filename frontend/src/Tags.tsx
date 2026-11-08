import { useState } from "react";
import { Loader2, Merge } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tag, slugify } from "@/api";
import { useCreateTag, useMergeTag, useTags } from "@/queries";

export default function Tags() {
  const tags = useTags();
  const createTag = useCreateTag();
  const mergeTag = useMergeTag();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [mergeFrom, setMergeFrom] = useState<Tag | null>(null);
  const [mergeInto, setMergeInto] = useState("");

  const slug = slugify(name);

  function create() {
    if (!slug) return;
    createTag.mutate(
      { slug, name: name.trim(), description: description.trim() },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
        },
      }
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-5">
      <h1 className="mb-4 text-xl font-semibold tracking-tight">Tags</h1>

      <section className="mb-6 space-y-2 rounded-xl border bg-card p-4">
        <h2 className="text-sm font-medium text-muted-foreground">New tag</h2>
        <Input
          placeholder="Name (e.g. Trading)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          placeholder="One line: what belongs in this tag?"
          value={description}
          maxLength={200}
          onChange={(e) => setDescription(e.target.value)}
        />
        <p className="text-sm text-muted-foreground">
          Slug: <code className="rounded bg-muted px-1">{slug || "—"}</code> — the
          description is how the model tells similar tags apart.
        </p>
        <Button onClick={create} disabled={!slug || createTag.isPending}>
          {createTag.isPending ? "Creating…" : "Create"}
        </Button>
        {createTag.isError && (
          <p className="text-sm text-red-400">
            Could not create — a tag with that slug may already exist.
          </p>
        )}
      </section>

      {tags.isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}

      <ul className="divide-y">
        {(tags.data ?? []).map((t) => (
          <li key={t.id} className="flex items-start justify-between gap-3 py-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="font-medium">{t.name}</span>
                <Badge variant="muted">/{t.slug}</Badge>
                <span className="text-xs text-muted-foreground">
                  {t.note_count} note{t.note_count === 1 ? "" : "s"}
                </span>
              </div>
              {t.description && (
                <p className="mt-0.5 text-sm text-muted-foreground">{t.description}</p>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={() => {
                setMergeFrom(t);
                setMergeInto("");
              }}
            >
              <Merge className="h-3.5 w-3.5" /> Merge
            </Button>
          </li>
        ))}
      </ul>

      <Dialog open={!!mergeFrom} onOpenChange={(o) => !o && setMergeFrom(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Merge “{mergeFrom?.name}” into…</DialogTitle>
            <DialogDescription>
              All notes tagged “{mergeFrom?.name}” move to the target. Duplicates
              collapse. “{mergeFrom?.name}” is then deleted.
            </DialogDescription>
          </DialogHeader>

          <Select value={mergeInto} onChange={(e) => setMergeInto(e.target.value)}>
            <option value="">Choose target tag</option>
            {(tags.data ?? [])
              .filter((t) => t.id !== mergeFrom?.id)
              .map((t) => (
                <option key={t.id} value={t.slug}>
                  {t.name}
                </option>
              ))}
          </Select>

          {mergeTag.isError && (
            <p className="text-sm text-red-400">Merge failed.</p>
          )}

          <div className="flex gap-2">
            <Button
              disabled={!mergeInto || mergeTag.isPending}
              onClick={() => {
                if (!mergeFrom) return;
                mergeTag.mutate(
                  { id: mergeFrom.id, mergeInto },
                  { onSuccess: () => setMergeFrom(null) }
                );
              }}
            >
              {mergeTag.isPending ? "Merging…" : "Merge"}
            </Button>
            <Button variant="ghost" onClick={() => setMergeFrom(null)}>
              Cancel
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
