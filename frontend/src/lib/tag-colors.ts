/**
 * Tag colours. Keys match Tag.COLORS on the backend; change both together.
 * Classes are written out literally so Tailwind keeps them.
 */
export type TagColor = {
  pill: string;
  box: string;
  dot: string;
  label: string;
};

export const TAG_COLORS: Record<string, TagColor> = {
  blue: {
    pill: "bg-blue-500/15 text-blue-300 ring-1 ring-inset ring-blue-500/25",
    box: "data-[checked]:bg-blue-500 data-[checked]:border-blue-500",
    dot: "bg-blue-400",
    label: "Blue",
  },
  green: {
    pill: "bg-green-500/15 text-green-300 ring-1 ring-inset ring-green-500/25",
    box: "data-[checked]:bg-green-500 data-[checked]:border-green-500",
    dot: "bg-green-400",
    label: "Green",
  },
  amber: {
    pill: "bg-amber-500/15 text-amber-300 ring-1 ring-inset ring-amber-500/25",
    box: "data-[checked]:bg-amber-500 data-[checked]:border-amber-500",
    dot: "bg-amber-400",
    label: "Amber",
  },
  red: {
    pill: "bg-red-500/15 text-red-300 ring-1 ring-inset ring-red-500/25",
    box: "data-[checked]:bg-red-500 data-[checked]:border-red-500",
    dot: "bg-red-400",
    label: "Red",
  },
  purple: {
    pill: "bg-purple-500/15 text-purple-300 ring-1 ring-inset ring-purple-500/25",
    box: "data-[checked]:bg-purple-500 data-[checked]:border-purple-500",
    dot: "bg-purple-400",
    label: "Purple",
  },
  pink: {
    pill: "bg-pink-500/15 text-pink-300 ring-1 ring-inset ring-pink-500/25",
    box: "data-[checked]:bg-pink-500 data-[checked]:border-pink-500",
    dot: "bg-pink-400",
    label: "Pink",
  },
  teal: {
    pill: "bg-teal-500/15 text-teal-300 ring-1 ring-inset ring-teal-500/25",
    box: "data-[checked]:bg-teal-500 data-[checked]:border-teal-500",
    dot: "bg-teal-400",
    label: "Teal",
  },
  orange: {
    pill: "bg-orange-500/15 text-orange-300 ring-1 ring-inset ring-orange-500/25",
    box: "data-[checked]:bg-orange-500 data-[checked]:border-orange-500",
    dot: "bg-orange-400",
    label: "Orange",
  },
  slate: {
    pill: "bg-slate-400/15 text-slate-300 ring-1 ring-inset ring-slate-400/25",
    box: "data-[checked]:bg-slate-400 data-[checked]:border-slate-400",
    dot: "bg-slate-400",
    label: "Slate",
  },
  lime: {
    pill: "bg-lime-500/15 text-lime-300 ring-1 ring-inset ring-lime-500/25",
    box: "data-[checked]:bg-lime-500 data-[checked]:border-lime-500",
    dot: "bg-lime-400",
    label: "Lime",
  },
};

const FALLBACK = TAG_COLORS.slate;

export function tagStyle(color?: string): TagColor {
  return (color && TAG_COLORS[color]) || FALLBACK;
}
