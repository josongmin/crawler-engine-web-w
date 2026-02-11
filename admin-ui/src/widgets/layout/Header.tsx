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

  const title = site ? site.name : (titles[pathname] ?? pathname.split("/").pop() ?? "");

  return (
    <header className="border-border bg-surface-0 flex h-14 items-center justify-between border-b px-6">
      <div className="flex items-center gap-3">
        {/* Site logo in header when on site page */}
        {site && (
          <div
            className={clsx(
              "flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold",
              siteBgMap[site.themeColor] ?? "bg-accent-500/20 text-accent-fg",
            )}
          >
            {site.name[0]}
          </div>
        )}
        <div>
          <h1 className="text-fg text-lg font-semibold">{title}</h1>
          {site && (
            <a
              href={site.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-fg-subtle hover:text-accent-fg flex items-center gap-1 text-[11px] transition-colors"
            >
              {site.domain}
              <ExternalLink size={9} />
            </a>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="border-border bg-surface-50 text-fg-subtle flex h-8 w-64 items-center gap-2 rounded-lg border px-3 text-sm">
          <Search size={14} />
          <span className="select-none">Search...</span>
          <kbd className="border-kbd-border bg-kbd-bg text-fg-subtle ml-auto rounded border px-1.5 py-0.5 font-mono text-[10px]">
            /
          </kbd>
        </div>
      </div>
    </header>
  );
}
