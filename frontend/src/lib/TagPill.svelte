<script lang="ts" generics="T extends any">
  import { cn } from "$lib/utils";
  import { tagStyle } from "$lib/tag-colors";

  let {
    name,
    color,
    class: className,
    children,
  }: {
    name: string;
    color?: string;
    class?: string;
    children?: import("svelte").Snippet;
  } = $props();
</script>

<span
  class={cn(
    "inline-flex max-w-full items-center gap-1 truncate rounded-full px-2 py-0.5 text-xs font-medium",
    tagStyle(color).pill,
    className
  )}
>
  <span class="truncate">{name}</span>
  {@render children?.()}
</span>
