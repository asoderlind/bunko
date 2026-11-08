import { NavLink } from "react-router-dom";
import { Inbox, LogOut, NotebookPen, Tag as TagIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useLogout } from "@/queries";

const items = [
  { to: "/", label: "Notes", icon: NotebookPen, end: true },
  { to: "/inbox", label: "Needs tags", icon: Inbox, end: false },
  { to: "/tags", label: "Tags", icon: TagIcon, end: false },
];

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const logout = useLogout();

  return (
    <nav className="flex h-full flex-col gap-1 p-3">
      <div className="px-2 pb-3 pt-1 text-sm font-semibold tracking-tight text-muted-foreground">
        easy-notes
      </div>

      {items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" />
          {label}
        </NavLink>
      ))}

      <div className="mt-auto">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 px-3 text-muted-foreground"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </nav>
  );
}
