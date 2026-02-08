import { useState } from "react";
import { useParams, Navigate, Link } from "react-router-dom";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { CodeBlock } from "@/shared/ui/CodeBlock";
import {
  ExternalLink,
  ShieldCheck,
  Copy,
  Check,
  Send,
  Terminal,
  FileJson,
} from "lucide-react";
import { clsx } from "clsx";
import { SITES, getSiteById } from "@/shared/config/sites";
import { SessionPanel, type SessionData } from "./components/SessionPanel";
import { OperationCard, type LastJobInfo } from "./components/OperationCard";
import { PasteAuthDialog } from "./components/PasteAuthDialog";

// ═══════════════════════════════════════════════════════
// Mock Data (replaced by API calls when backend is ready)
// ═══════════════════════════════════════════════════════

const MOCK_SESSIONS: Record<string, SessionData | null> = {
  burghound: {
    status: "active",
    ttlRemaining: "2d 14h",
    ttlPct: 68,
    useCount: 23,
    lastLogin: "2h ago",
    userAgent: "Chrome/144.0 on macOS",
    cleanClose: true,
    kitExported: true,
  },
  vivino: null,
  "wine-searcher": {
    status: "expired",
    ttlRemaining: "expired",
    ttlPct: 0,
    useCount: 15,
    lastLogin: "4d ago",
    userAgent: "Chrome/144.0 on macOS",
    cleanClose: true,
    kitExported: false,
  },
};

interface MockJob extends LastJobInfo {
  operation: string;
}

const MOCK_JOBS: Record<string, MockJob[]> = {
  burghound: [
    {
      id: "#47",
      operation: "search-all",
      status: "success",
      items: 142,
      ago: "3m",
    },
    {
      id: "#46",
      operation: "search-all",
      status: "success",
      items: 89,
      ago: "1h",
    },
    {
      id: "#45",
      operation: "wine-detail",
      status: "failed",
      items: 0,
      ago: "2h",
    },
  ],
  vivino: [],
  "wine-searcher": [
    {
      id: "#44",
      operation: "search",
      status: "success",
      items: 200,
      ago: "2d",
    },
  ],
};

const MOCK_SNIPPETS: Record<string, { code: string; lang: string }> = {
  cURL: {
    code: `curl 'https://www.burghound.com/tnsearch/tasting_notes.php' \\
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36' \\
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \\
  -H 'Accept-Language: en-US,en;q=0.9' \\
  -H 'Cookie: PHPSESSID=abc123def456; tn_user=xyz789; remember_me=token_here'`,
    lang: "bash",
  },
  httpx: {
    code: `import httpx

cookies = {
    "PHPSESSID": "abc123def456",
    "tn_user": "xyz789",
    "remember_me": "token_here",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
}

r = httpx.get(
    "https://www.burghound.com/tnsearch/tasting_notes.php",
    cookies=cookies,
    headers=headers,
)
print(r.status_code, len(r.text))`,
    lang: "python",
  },
  "Storage State": {
    code: JSON.stringify(
      {
        cookies: [
          {
            name: "PHPSESSID",
            value: "abc123def456",
            domain: ".burghound.com",
            path: "/",
            expires: 1738972800,
            httpOnly: true,
            secure: true,
          },
          {
            name: "tn_user",
            value: "xyz789",
            domain: ".burghound.com",
            path: "/",
          },
        ],
        origins: [],
      },
      null,
      2,
    ),
    lang: "json",
  },
};

// ═══════════════════════════════════════════════════════
// SitesPage — Per-site command center
// ═══════════════════════════════════════════════════════

export function SitesPage() {
  const { site: siteId } = useParams<{ site: string }>();
  const site = getSiteById(siteId ?? "");

  const [pasteAuthOpen, setPasteAuthOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<string | null>(null);
  const [copiedFormat, setCopiedFormat] = useState<string | null>(null);

  // Redirect to first site if no valid site specified
  if (!site) {
    return <Navigate to={`/sites/${SITES[0].id}`} replace />;
  }

  const session = MOCK_SESSIONS[site.id] ?? null;
  const jobs = MOCK_JOBS[site.id] ?? [];
  const isSessionActive = session?.status === "active";

  // ── Handlers ─────────────────────────────────────────

  const handleExportClick = async (format: string) => {
    const snippet = MOCK_SNIPPETS[format];
    if (snippet) {
      await navigator.clipboard.writeText(snippet.code);
      setCopiedFormat(format);
      setExportFormat(format);
      setTimeout(() => setCopiedFormat(null), 2000);
    }
  };

  const handleRunOperation = (operationId: string, limit: number) => {
    // TODO: POST /api/jobs with { site, operation, limit }
    console.log(`Run ${site.id}/${operationId} with limit=${limit}`);
  };

  // ── Render ───────────────────────────────────────────

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* ── Site Header ─────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SiteLogo name={site.name} color={site.themeColor} />
          <div>
            <h1 className="text-lg font-bold text-fg">{site.name}</h1>
            <a
              href={site.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-fg-subtle transition-colors hover:text-accent-fg"
            >
              {site.domain}
              <ExternalLink size={10} />
            </a>
          </div>
        </div>
        <div className="text-xs text-fg-faint">
          {site.operations.length} operations ·{" "}
          {site.supportsRequestKit && "Kit export"}{" "}
          {site.supportsPasteAuth && "· Paste auth"}
        </div>
      </div>

      {/* ── Session & Auth ──────────────────────────── */}
      <section>
        <SectionLabel>Session</SectionLabel>
        <SessionPanel
          site={site}
          session={session}
          onLogin={() => {
            /* TODO: POST /api/sessions/{site}/login */
          }}
          onLogout={() => {
            /* TODO: POST /api/sessions/{site}/logout */
          }}
          onPasteAuth={() => setPasteAuthOpen(true)}
          onRefresh={() => {
            /* TODO: POST /api/sessions/{site}/refresh */
          }}
        />
      </section>

      {/* ── Operations ──────────────────────────────── */}
      <section>
        <SectionLabel>
          Operations
          {!isSessionActive && (
            <span className="ml-2 text-[10px] font-normal text-fg-faint">
              Login required to run
            </span>
          )}
        </SectionLabel>
        <div
          className={clsx(
            "grid gap-4",
            site.operations.length <= 2
              ? "grid-cols-2"
              : "grid-cols-2 lg:grid-cols-3",
          )}
        >
          {site.operations.map((op) => {
            const lastJob = jobs.find((j) => j.operation === op.id);
            return (
              <OperationCard
                key={op.id}
                operation={op}
                lastJob={
                  lastJob
                    ? {
                        id: lastJob.id,
                        status: lastJob.status,
                        items: lastJob.items,
                        ago: lastJob.ago,
                      }
                    : undefined
                }
                disabled={!isSessionActive}
                onRun={handleRunOperation}
              />
            );
          })}
        </div>
      </section>

      {/* ── Bottom Row: Export + Activity ────────────── */}
      <div className="grid grid-cols-5 gap-4">
        {/* Request Kit Export */}
        <section className="col-span-2">
          <SectionLabel>Request Kit</SectionLabel>
          <Card>
            {/* Export buttons */}
            <div className="flex flex-wrap gap-2">
              <ExportButton
                label="cURL"
                icon={<Terminal size={13} />}
                copied={copiedFormat === "cURL"}
                active={exportFormat === "cURL"}
                onClick={() => handleExportClick("cURL")}
                disabled={!isSessionActive}
              />
              <ExportButton
                label="httpx"
                icon={<Send size={13} />}
                copied={copiedFormat === "httpx"}
                active={exportFormat === "httpx"}
                onClick={() => handleExportClick("httpx")}
                disabled={!isSessionActive}
              />
              <ExportButton
                label="Storage State"
                icon={<FileJson size={13} />}
                copied={copiedFormat === "Storage State"}
                active={exportFormat === "Storage State"}
                onClick={() => handleExportClick("Storage State")}
                disabled={!isSessionActive}
              />
            </div>

            {/* Kit health */}
            {session && (
              <div className="mt-3 flex items-center gap-3 text-xs">
                <span
                  className={clsx(
                    "flex items-center gap-1.5",
                    isSessionActive ? "text-status-success" : "text-status-danger",
                  )}
                >
                  <span
                    className={clsx(
                      "h-1.5 w-1.5 rounded-full",
                      isSessionActive ? "bg-status-success" : "bg-status-danger",
                    )}
                  />
                  {isSessionActive ? "valid" : "expired"}
                </span>
                {isSessionActive && (
                  <span className="text-fg-subtle">23h remaining</span>
                )}
                <Button
                  size="sm"
                  variant="ghost"
                  icon={<ShieldCheck size={12} />}
                  disabled={!isSessionActive}
                >
                  Validate
                </Button>
              </div>
            )}

            {/* Snippet preview */}
            {exportFormat && MOCK_SNIPPETS[exportFormat] && (
              <div className="mt-3">
                <CodeBlock
                  code={MOCK_SNIPPETS[exportFormat].code}
                  language={MOCK_SNIPPETS[exportFormat].lang}
                />
              </div>
            )}
          </Card>
        </section>

        {/* Recent Activity */}
        <section className="col-span-3">
          <SectionLabel>Recent Activity</SectionLabel>
          <Card>
            {jobs.length === 0 ? (
              <p className="py-4 text-center text-xs text-fg-faint">
                No recent activity for {site.name}
              </p>
            ) : (
              <div className="space-y-2">
                {jobs.map((j) => (
                  <div
                    key={j.id}
                    className="flex items-center justify-between rounded-lg bg-surface-0 px-3 py-2.5"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-fg-subtle">
                        {j.id}
                      </span>
                      <span className="rounded bg-surface-200 px-1.5 py-0.5 font-mono text-[10px] text-fg-muted">
                        {j.operation}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {j.items > 0 && (
                        <span className="font-mono text-xs text-fg-subtle">
                          {j.items} items
                        </span>
                      )}
                      <StatusBadge status={j.status} />
                      <span className="text-xs text-fg-faint">{j.ago}</span>
                    </div>
                  </div>
                ))}
                <Link
                  to={`/jobs?site=${site.id}`}
                  className="mt-2 block text-center text-xs text-fg-subtle transition-colors hover:text-accent-fg"
                >
                  View all jobs for {site.name} →
                </Link>
              </div>
            )}
          </Card>
        </section>
      </div>

      {/* ── Paste Auth Dialog ───────────────────────── */}
      <PasteAuthDialog
        open={pasteAuthOpen}
        onClose={() => setPasteAuthOpen(false)}
        siteName={site.name}
        onSubmit={(mode, content) => {
          // TODO: POST /api/sessions/{site}/paste-auth
          console.log(`Paste auth for ${site.id}:`, mode, content);
        }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// Sub-components (internal to this module)
// ═══════════════════════════════════════════════════════

function SiteLogo({ name, color }: { name: string; color: string }) {
  const bgMap: Record<string, string> = {
    rose: "bg-rose-500/20 text-rose-500 dark:text-rose-400",
    violet: "bg-violet-500/20 text-violet-500 dark:text-violet-400",
    amber: "bg-amber-500/20 text-amber-600 dark:text-amber-400",
  };
  return (
    <div
      className={clsx(
        "flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold",
        bgMap[color] ?? "bg-accent-500/20 text-accent-fg",
      )}
    >
      {name[0]}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-2.5 text-xs font-semibold uppercase tracking-widest text-fg-subtle">
      {children}
    </h2>
  );
}

function ExportButton({
  label,
  icon,
  copied,
  active,
  onClick,
  disabled,
}: {
  label: string;
  icon: React.ReactNode;
  copied: boolean;
  active: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-all",
        "disabled:pointer-events-none disabled:opacity-40",
        active
          ? "border-accent-500/30 bg-accent-muted text-accent-fg"
          : "border-border bg-surface-0 text-fg-muted hover:border-border-hover hover:text-fg-secondary",
      )}
    >
      {copied ? (
        <Check size={13} className="text-status-success" />
      ) : (
        icon
      )}
      {label}
      {copied && (
        <span className="text-[10px] text-status-success">Copied!</span>
      )}
    </button>
  );
}
