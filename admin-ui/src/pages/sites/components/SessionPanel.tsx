import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { LogIn, LogOut, ClipboardPaste, RefreshCw } from "lucide-react";
import type { SiteDefinition } from "@/shared/config/sites";

// ── Types ──────────────────────────────────────────────

export interface SessionData {
  status: "active" | "expired" | "logged_out";
  ttlRemaining: string;
  ttlPct: number;
  useCount: number;
  lastLogin: string;
  userAgent: string;
  cleanClose: boolean;
  kitExported: boolean;
}

interface Props {
  site: SiteDefinition;
  session: SessionData | null;
  onLogin: () => void;
  onLogout: () => void;
  onPasteAuth: () => void;
  onRefresh: () => void;
}

// ── Component ──────────────────────────────────────────

export function SessionPanel({
  site,
  session,
  onLogin,
  onLogout,
  onPasteAuth,
  onRefresh,
}: Props) {
  // ── Not connected ───────────────────────────────────
  if (!session) {
    return (
      <Card className="border-dashed">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-surface-400" />
              <span className="text-sm font-semibold text-fg-tertiary">
                Not Connected
              </span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-fg-faint">
              Login or paste authentication cookies to start using{" "}
              <span className="text-fg-subtle">{site.name}</span>
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              icon={<LogIn size={14} />}
              onClick={onLogin}
            >
              Login
            </Button>
            <Button
              size="sm"
              icon={<ClipboardPaste size={14} />}
              onClick={onPasteAuth}
            >
              Paste Auth
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // ── Connected / Expired ─────────────────────────────
  const isExpired = session.status === "expired";
  const isLoggedOut = session.status === "logged_out";
  const isHealthy = session.status === "active";

  return (
    <Card className={isExpired ? "border-status-danger-subtle" : undefined}>
      <div className="flex items-start justify-between gap-6">
        {/* Left: status info */}
        <div className="flex-1 space-y-3">
          {/* Status row */}
          <div className="flex items-center gap-3">
            <StatusBadge status={session.status} />
            {isHealthy && (
              <span className="text-xs font-medium text-fg-subtle">
                TTL {session.ttlRemaining}
              </span>
            )}
            {isExpired && (
              <span className="text-xs font-medium text-status-danger/80">
                Session expired — re-login required
              </span>
            )}
          </div>

          {/* TTL progress bar */}
          {isHealthy && (
            <div className="max-w-xs space-y-1">
              <div className="h-1.5 rounded-full bg-surface-200">
                <div
                  className="h-full rounded-full bg-status-success/60 transition-all duration-500"
                  style={{ width: `${session.ttlPct}%` }}
                />
              </div>
            </div>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-fg-subtle">
            <span>Uses: {session.useCount}</span>
            <span>Last login: {session.lastLogin}</span>
            <span>
              Clean close: {session.cleanClose ? "yes" : "no"}
            </span>
            {session.kitExported && <span>Kit: exported</span>}
          </div>

          {/* Persona */}
          <div className="inline-block rounded-md bg-surface-0 px-2.5 py-1.5 font-mono text-[11px] text-fg-subtle">
            {session.userAgent}
          </div>
        </div>

        {/* Right: action buttons */}
        <div className="flex shrink-0 flex-wrap items-start gap-2">
          {isExpired || isLoggedOut ? (
            <>
              <Button
                variant="primary"
                size="sm"
                icon={<LogIn size={14} />}
                onClick={onLogin}
              >
                Re-login
              </Button>
              <Button
                size="sm"
                icon={<ClipboardPaste size={14} />}
                onClick={onPasteAuth}
              >
                Paste Auth
              </Button>
            </>
          ) : (
            <>
              <Button
                size="sm"
                icon={<RefreshCw size={14} />}
                onClick={onRefresh}
              >
                Refresh
              </Button>
              <Button
                size="sm"
                icon={<ClipboardPaste size={14} />}
                onClick={onPasteAuth}
              >
                Paste Auth
              </Button>
              <Button
                size="sm"
                variant="danger"
                icon={<LogOut size={14} />}
                onClick={onLogout}
              >
                Logout
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}
