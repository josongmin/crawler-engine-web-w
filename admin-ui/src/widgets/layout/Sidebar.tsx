import { NavLink } from "react-router-dom";
import { clsx } from "clsx";
import {
  LayoutGrid,
  Play,
  FileCode2,
  ScrollText,
  FlaskConical,
  Sun,
  Moon,
  Monitor,
} from "lucide-react";
import { SITES } from "@/shared/config/sites";
import { useTheme, type ThemePreference } from "@/shared/hooks/useTheme";

// ── Mock session status per site ───────────────────────
// TODO: replace with real data from useSessionStore or API

const siteSessionStatus: Record<string, "active" | "inactive" | "expired"> = {
  burghound: "active",
  vivino: "inactive",
  "wine-searcher": "expired",
};

const dotColors: Record<string, string> = {
  active: "bg-status-success",
  inactive: "bg-surface-400",
  expired: "bg-status-danger",
};

const siteBgMap: Record<string, string> = {
  rose: "bg-rose-500/20 text-rose-500 dark:text-rose-400",
  violet: "bg-violet-500/20 text-violet-500 dark:text-violet-400",
  amber: "bg-amber-500/20 text-amber-600 dark:text-amber-400",
};

// ── Navigation items ───────────────────────────────────

const toolNav = [
  { to: "/jobs", icon: Play, label: "Jobs" },
  { to: "/rules", icon: FileCode2, label: "Rules" },
  { to: "/playground", icon: FlaskConical, label: "Playground" },
  { to: "/logs", icon: ScrollText, label: "Logs" },
] as const;

// ── Theme toggle options ───────────────────────────────

const themeOptions: { value: ThemePreference; icon: typeof Sun; label: string }[] = [
  { value: "light", icon: Sun, label: "Light" },
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "system", icon: Monitor, label: "System" },
];

// ── Sidebar component ──────────────────────────────────

export function Sidebar() {
  const { theme, setTheme } = useTheme();

  return (
    <aside className="flex w-56 flex-col border-r border-border bg-surface-0">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-500 text-xs font-bold text-white">
          W
        </div>
        <div>
          <div className="text-sm font-semibold text-fg">
            Wine Crawler
          </div>
          <div className="text-[10px] text-fg-subtle">Admin</div>
        </div>
      </div>

      {/* Overview */}
      <nav className="mt-2 px-3">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent-muted text-accent-fg"
                : "text-fg-muted hover:bg-surface-100 hover:text-fg-secondary",
            )
          }
        >
          <LayoutGrid size={16} strokeWidth={1.8} />
          Overview
        </NavLink>
      </nav>

      {/* Sites section */}
      <div className="mt-5 px-3">
        <div className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-fg-faint">
          Sites
        </div>
        <nav className="flex flex-col gap-0.5">
          {SITES.map((site) => {
            const status =
              siteSessionStatus[site.id] ?? "inactive";
            return (
              <NavLink
                key={site.id}
                to={`/sites/${site.id}`}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-accent-muted text-accent-fg"
                      : "text-fg-muted hover:bg-surface-100 hover:text-fg-secondary",
                  )
                }
              >
                {/* Site logo mini */}
                <div
                  className={clsx(
                    "flex h-5 w-5 items-center justify-center rounded text-[9px] font-bold",
                    siteBgMap[site.themeColor] ??
                      "bg-accent-500/20 text-accent-fg",
                  )}
                >
                  {site.name[0]}
                </div>
                <span className="flex-1 truncate">{site.name}</span>
                {/* Status dot */}
                <span
                  className={clsx(
                    "h-1.5 w-1.5 shrink-0 rounded-full",
                    dotColors[status],
                  )}
                />
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Tools section */}
      <div className="mt-5 px-3">
        <div className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-fg-faint">
          Tools
        </div>
        <nav className="flex flex-col gap-0.5">
          {toolNav.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent-muted text-accent-fg"
                    : "text-fg-muted hover:bg-surface-100 hover:text-fg-secondary",
                )
              }
            >
              <Icon size={16} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Theme switcher */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex gap-0.5 rounded-lg border border-border bg-surface-0 p-0.5">
          {themeOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setTheme(opt.value)}
              className={clsx(
                "flex flex-1 items-center justify-center gap-1 rounded-md px-1.5 py-1.5 text-[10px] font-medium transition-colors",
                theme === opt.value
                  ? "bg-surface-200 text-fg"
                  : "text-fg-subtle hover:text-fg-muted",
              )}
              title={opt.label}
            >
              <opt.icon size={12} strokeWidth={2} />
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border px-5 py-3">
        <div className="flex items-center gap-2 text-xs text-fg-subtle">
          <span className="h-1.5 w-1.5 rounded-full bg-status-success" />
          API Connected
        </div>
      </div>
    </aside>
  );
}
