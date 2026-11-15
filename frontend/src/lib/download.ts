import type { Note } from "./api";
import { showToast } from "./toast.svelte";

/** Both single-note downloads and full exports use the same front matter. */
export async function downloadNotesFile(path: string, filename: string) {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) throw new Error("Could not export notes.");
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function downloadNote(note: Note) {
  const safe = (note.title || "note")
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim().replace(/\s+/g, "-").slice(0, 60) || "note";
  try {
    await downloadNotesFile(`/api/notes/${note.id}/export`, `${safe}.md`);
  } catch {
    showToast("Could not export this note.", "error");
  }
}
