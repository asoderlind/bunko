import { cn } from "@/lib/utils";

/**
 * Tag colours. Keys match Tag.COLORS in the backend; change the palette there
 * and here together. Deliberately literal classes (not dynamic strings) so
 * Tailwind keeps them in the build.
 */
export const TAG_COLORS: Record<
  string,
  { pill: string; box: string; dot: string; label: string }
> = {
  blue: {
    pill: "bg-blue-500/15 text-blue-300 ring-1 ring-inset ring-blue-500/25",
    box: "data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500",
    dot: "bg-blue-400",
    label: "Blue",
  },
  green: {
    pill: "bg-green-500/15 text-green-300 ring-1 ring-inset ring-green-500/25",
    box: "data-[state=checked]:bg-green-500 data-[state=checked]:border-green-500",
    dot: "bg-green-400",
    label: "Green",
  },
  amber: {
    pill: "bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/25",
    box: "data-[state=checked]:bg-amber-500 data-[state=checked]:border-amber-500",
    dot: "bg-amber-400",
    label: "Amber",
  },
  red: {
    pill: "bg-red-500/15 text-red-300 ring-1 ring-inset ring-red-500/25",
    box: "data-[state=checked]:bg-red-500 data-[state=checked]:border-red-500",
    dot: "bg-red-400",
    label: "Red",
  },
  purple: {
    pill: "bg-purple-500/15 text-purple-300 ring-1 ring-inset ring-purple-500/25",
    box: "data-[state=checked]:bg-purple-500 data-[state=checked]:border-purple-500",
    dot: "bg-purple-400",
    label: "Purple",
  },
  pink: {
    pill: "bg-pink-500/15 text-pink-300 ring-1 ring-inset ring-pink-500/25",
    box: "data-[state=checked]:bg-pink-500 data-[state=checked]:border-pink-500",
    dot: "bg-pink-400",
    label: "Pink",
  },
  teal: {
    pill: "bg-teal-500/15 text-teal-300 ring-1 ring-inset ring-teal-500/25",
    box: "data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500",
    dot: "bg-teal-400",
    label: "Teal",
  },
  orange: {
    pill: "bg-orange-500/15 text-orange-300 ring-1 ring-inset ring-orange-500/25",
    box: "data-[state=checked]:bg-orange-500 data-[state=checked]:border-orange-500",
    dot: "bg-orange-400",
    label: "Orange",
  },
  slate: {
    pill: "bg-slate-400/15 text-slate-300 ring-1 ring-inset ring-slate-400/25",
    box: "data-[state=checked]:bg-slate-400 data-[state=checked]:border-slate-400",
    dot: "bg-slate-400",
    label: "Slate",
  },
  lime: {
    pill: "bg-lime-500/15 text-lime-300 ring-1 ring-inset ring-lime-500/25",
    box: "data-[state=checked]:bg-lime-500 data-[state=checked]:border-lime-500",
    dot: "bg-lime-400",
    label: "Lime",
  },
};

const FALLBACK = TAG_COLORS.slate;

export function tagStyle(color?: string) {
  return (color && TAG_COLORS[color]) || FALLBACK;
}

export function TagPill({
  name,
  color,
  className,
  children,
}: {
  name: string;
  color?: string;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 truncate rounded-full px-2 py-0.5 text-xs font-medium",
        tagStyle(color).pill,
        className
      )}
    >
      <span className="truncate">{name}</span>
      {children}
    </span>
  );
}

/** Square checkbox tinted with the tag's colour. */
export function TagCheckbox({
  color,
  checked,
}: {
  color?: string;
  checked: boolean;
}) {
  return (
    <span
      data-state={checked ? "checked" : "unchecked"}
      className={cn(
        "flex h-4 w-4 shrink-0 items-center justify-center rounded border border-muted-foreground/40 transition-colors",
        tagStyle(color).box
      )}
      aria-hidden="true"
    >
      {checked && (
        <svg viewBox="0 0 24 24" className="h-3 w-3 text-white" fill="none">
          <path
            d="M20 6L9 17l-5-5"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </span>
  );
}
