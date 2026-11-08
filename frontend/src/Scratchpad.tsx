import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCreateNote } from "@/queries";

const DRAFT_KEY = "easy-notes.draft";

export default function Scratchpad() {
  const nav = useNavigate();
  const [body, setBody] = useState(() => localStorage.getItem(DRAFT_KEY) || "");
  const create = useCreateNote();
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  // Draft persisted on every keystroke (spec 8).
  useEffect(() => {
    if (body) localStorage.setItem(DRAFT_KEY, body);
    else localStorage.removeItem(DRAFT_KEY);
  }, [body]);

  const save = useCallback(() => {
    if (create.isPending) return;
    if (!body.trim()) return; // empty notes are never created
    create.mutate(
      { body },
      {
        onSuccess: (note) => {
          localStorage.removeItem(DRAFT_KEY);
          setBody("");
          nav(`/notes/${note.id}`);
        },
      }
    );
  }, [body, create, nav]);

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      save();
    }
  }

  const hasText = body.trim().length > 0;

  return (
    <div className="flex flex-1 flex-col">
      <textarea
        ref={ref}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Write something…"
        spellCheck={false}
        aria-label="New note"
        className="min-h-0 flex-1 resize-none bg-transparent px-4 py-5 text-[17px] leading-relaxed outline-none placeholder:text-muted-foreground/60"
      />

      {create.isError && (
        <p role="alert" className="px-4 pb-2 text-sm text-red-400">
          Could not save. Your text is kept in this browser.
        </p>
      )}

      {hasText && (
        <div className="sticky bottom-0 flex items-center gap-3 border-t bg-background px-4 py-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))]">
          <Button onClick={save} disabled={create.isPending}>
            {create.isPending ? (
              <>
                <Loader2 className="animate-spin" /> Saving…
              </>
            ) : (
              "Save"
            )}
          </Button>
          <span className="text-sm text-muted-foreground">⌘/Ctrl + Enter</span>
        </div>
      )}
    </div>
  );
}
