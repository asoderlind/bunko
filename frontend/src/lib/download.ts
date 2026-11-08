import type { Note } from "./api";

/** Download a note as a markdown file with a small YAML front matter block. */
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
