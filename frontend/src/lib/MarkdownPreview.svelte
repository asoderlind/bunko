<script lang="ts">
  import MarkdownIt from "markdown-it";
  import markdownItKatex from "markdown-it-katex";
  import DOMPurify from "dompurify";
  import hljs from "highlight.js";
  import { cn } from "$lib/utils";
  import "highlight.js/styles/github-dark.css";
  import "katex/dist/katex.min.css";

  let {
    source,
    class: className,
  }: {
    source: string;
    class?: string;
  } = $props();

  function escapeHtml(value: string): string {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const md = new MarkdownIt({
    html: false,
    linkify: true,
    breaks: true,
    highlight(code, language): string {
      if (language && hljs.getLanguage(language)) {
        try {
          return `<pre><code class="hljs language-${language}">${hljs.highlight(code, { language, ignoreIllegals: true }).value}</code></pre>`;
        } catch {
          // Fall through to escaped plain text.
        }
      }
      return `<pre><code class="hljs">${escapeHtml(code)}</code></pre>`;
    },
  }).use(markdownItKatex);

  const rendered = $derived(DOMPurify.sanitize(md.render(source ?? "")));
</script>

<div class={cn("markdown-body", className)}>
  {@html rendered}
</div>
