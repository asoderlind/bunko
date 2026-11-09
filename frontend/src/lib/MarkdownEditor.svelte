<script lang="ts">
  import { onMount } from "svelte";
  import { EditorState } from "@codemirror/state";
  import { EditorView, keymap, placeholder as cmPlaceholder } from "@codemirror/view";
  import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
  import { markdown } from "@codemirror/lang-markdown";
  import { oneDark } from "@codemirror/theme-one-dark";
  import { showToast } from "$lib/toast.svelte";

  let {
    value = "",
    onchange,
    onblur,
    onsave,
    onupload,
    placeholder = "Write something…",
    ariaLabel = "Note body",
    padTop = 0,
    padBottom = 0,
    autofocus = false,
  }: {
    value?: string;
    onchange?: (value: string) => void;
    onblur?: () => void;
    onsave?: () => void;
    onupload?: (file: File) => Promise<string>;
    placeholder?: string;
    ariaLabel?: string;
    padTop?: number;
    padBottom?: number;
    autofocus?: boolean;
  } = $props();

  let host: HTMLDivElement;
  let view: EditorView | null = null;
  let ready = $state(false);
  let syncing = false;

  const theme = EditorView.theme({
    "&": {
      height: "100%",
      backgroundColor: "transparent",
      color: "hsl(var(--foreground))",
    },
    ".cm-scroller": {
      overflow: "auto",
      fontFamily:
        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
      lineHeight: "1.7",
    },
    ".cm-content": {
      paddingTop: "var(--cm-pad-top, 0px)",
      paddingBottom: "var(--cm-pad-bottom, 0px)",
      paddingLeft: "var(--cm-pad-x, 1rem)",
      paddingRight: "var(--cm-pad-x, 1rem)",
      caretColor: "hsl(var(--primary))",
    },
    ".cm-placeholder": { color: "hsl(var(--muted-foreground) / 0.5)" },
    ".cm-gutters": { display: "none" },
    ".cm-activeLine": { backgroundColor: "transparent" },
    "&.cm-focused": { outline: "none" },
    "&.cm-focused .cm-cursor": { borderLeftColor: "hsl(var(--primary))" },
    ".cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection": {
      backgroundColor: "hsl(var(--primary) / 0.25)",
    },
  });

  async function uploadAt(file: File, target: EditorView, pos: number) {
    if (!onupload) return;
    try {
      const markdownText = await onupload(file);
      // The note can change while the upload is in flight.
      if (target !== view || !target.dom.isConnected) return;
      const at = Math.min(Math.max(pos, 0), target.state.doc.length);
      target.dispatch({
        changes: { from: at, insert: markdownText },
        selection: { anchor: at + markdownText.length },
        scrollIntoView: true,
      });
      target.focus();
    } catch {
      showToast("Image upload failed.", "error");
    }
  }

  function imageFromClipboard(event: ClipboardEvent): File | null {
    const items = event.clipboardData?.items;
    if (items) {
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) return file;
        }
      }
    }
    for (const file of Array.from(event.clipboardData?.files ?? [])) {
      if (file.type.startsWith("image/")) return file;
    }
    return null;
  }

  onMount(() => {
    view = new EditorView({
      parent: host,
      state: EditorState.create({
        doc: value,
        extensions: [
          history(),
          keymap.of([
            ...defaultKeymap,
            ...historyKeymap,
            indentWithTab,
            {
              key: "Mod-s",
              run: () => {
                onsave?.();
                return true;
              },
            },
          ]),
          markdown(),
          EditorView.lineWrapping,
          EditorView.contentAttributes.of({ "aria-label": ariaLabel }),
          cmPlaceholder(placeholder),
          oneDark,
          theme,
          EditorView.updateListener.of((update) => {
            if (update.docChanged && !syncing) {
              onchange?.(update.state.doc.toString());
            }
          }),
          EditorView.domEventHandlers({
            blur: () => {
              onblur?.();
              return false;
            },
            paste: (event, currentView) => {
              const file = imageFromClipboard(event);
              if (!file || !onupload) return false;
              event.preventDefault();
              void uploadAt(file, currentView, currentView.state.selection.main.from);
              return true;
            },
            drop: (event, currentView) => {
              const files = Array.from(event.dataTransfer?.files ?? []);
              const file = files.find((candidate) => candidate.type.startsWith("image/"));
              if (!file || !onupload) return false;
              event.preventDefault();
              const pos =
                currentView.posAtCoords({ x: event.clientX, y: event.clientY }) ??
                currentView.state.selection.main.from;
              void uploadAt(file, currentView, pos);
              return true;
            },
          }),
        ],
      }),
    });
    ready = true;
    if (autofocus) view.focus();
    return () => {
      ready = false;
      view?.destroy();
      view = null;
    };
  });

  // Keep the editor in sync when the parent swaps notes or resets the body.
  $effect(() => {
    if (!ready || !view) return;
    const next = value;
    const current = view.state.doc.toString();
    if (next === current) return;
    syncing = true;
    view.dispatch({ changes: { from: 0, to: current.length, insert: next } });
    syncing = false;
  });

  /** Insert Markdown at the current cursor (used by the image toolbar button). */
  export function insert(text: string) {
    if (!view) return;
    const at = view.state.selection.main.from;
    view.dispatch({
      changes: { from: at, insert: text },
      selection: { anchor: at + text.length },
      scrollIntoView: true,
    });
    view.focus();
  }

  export function focusEditor() {
    view?.focus();
  }
</script>

<div
  bind:this={host}
  class="markdown-editor h-full min-h-0 w-full"
  style="--cm-pad-top: {padTop}px; --cm-pad-bottom: {padBottom}px"
></div>
