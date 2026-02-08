import { useLocation } from "react-router-dom";
import { Search, ExternalLink } from "lucide-react";
import { getSiteById } from "@/shared/config/sites";
import { clsx } from "clsx";

// ── Static titles for non-site pages ───────────────────

const titles: Record<string, string> = {
  "/": "Overview",
  "/jobs": "Jobs",
  "/rules": "Rules",
  "/playground": "Playground",
  "/logs": "Logs",
};

// ── Site logo color map ────────────────────────────────

const siteBgMap: Record<string, string> = {
  rose: "bg-rose-500/20 text-rose-500 dark:text-rose-400",
  violet: "bg-violet-500/20 text-violet-500 dark:text-violet-400",
  amber: "bg-amber-500/20 text-amber-600 dark:text-amber-400",
};

// ── Component ──────────────────────────────────────────

export function Header() {
  const { pathname } = useLocation();

  // Detect site context from URL
  const siteMatch = pathname.match(/^\/sites\/([^/]+)/);
  const site = siteMatch ? getSiteById(siteMatch[1]) : null;

  const title = site
    ? site.name
    : titles[pathname] ?? pathname.split("/").pop() ?? "";

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-surface-0 px-6">
      <div className="flex items-center gap-3">
        {/* Site logo in header when on site page */}
        {site && (
          <div
            className={clsx(
              "flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold",
              siteBgMap[site.themeColor] ??
                "bg-accent-500/20 text-accent-fg",
            )}
          >
            {site.name[0]}
          </div>
        )}
        <div>
          <h1 className="text-lg font-semibold text-fg">{title}</h1>
          {site && (
            <a
              href={site.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[11px] text-fg-subtle transition-colors hover:text-accent-fg"
            >
              {site.domain}
              <ExternalLink size={9} />
            </a>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-64 items-center gap-2 rounded-lg border border-border bg-surface-50 px-3 text-sm text-fg-subtle">
          <Search size={14} />
          <span className="select-none">Search...</span>
          <kbd className="ml-auto rounded border border-kbd-border bg-kbd-bg px-1.5 py-0.5 font-mono text-[10px] text-fg-subtle">
            /
          </kbd>
        </div>
      </div>
    </header>
  );
}
