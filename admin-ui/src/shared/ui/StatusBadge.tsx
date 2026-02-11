import { clsx } from "clsx";

/* ── Status → semantic token mapping ─────────────────
 *
 * Maps domain status strings to the design system's
 * status token categories (success/danger/warning/info/neutral).
 * Uses bg-status-*-muted for background, text-status-* for text,
 * and border-status-*-subtle for borders.
 * ──────────────────────────────────────────────────── */

type StatusCategory = "success" | "danger" | "warning" | "info" | "neutral";

const statusCategoryMap: Record<string, StatusCategory> = {
  active: "success",
  success: "success",
  pass: "success",
  inactive: "neutral",
  pending: "neutral",
  cancelled: "neutral",
  expired: "danger",
  failed: "danger",
  fail: "danger",
  logged_out: "warning",
  partial: "warning",
  running: "info",
};

const categoryStyles: Record<StatusCategory, string> = {
  success: "bg-status-success-muted text-status-success border-status-success-subtle",
  danger: "bg-status-danger-muted text-status-danger border-status-danger-subtle",
  warning: "bg-status-warning-muted text-status-warning border-status-warning-subtle",
  info: "bg-status-info-muted text-status-info border-status-info-subtle",
  neutral: "bg-status-neutral-muted text-status-neutral border-status-neutral-subtle",
};

const dotCategoryMap: Record<string, StatusCategory | undefined> = {
  active: "success",
  running: "info",
  success: "success",
  failed: "danger",
  expired: "danger",
  pass: "success",
  fail: "danger",
};

const dotStyles: Record<StatusCategory, string> = {
  success: "bg-status-success",
  danger: "bg-status-danger",
  warning: "bg-status-warning",
  info: "bg-status-info animate-pulse",
  neutral: "bg-status-neutral",
};

export function StatusBadge({ status }: { status: string }) {
  const category = statusCategoryMap[status] ?? "neutral";
  const dotCategory = dotCategoryMap[status];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        categoryStyles[category],
      )}
    >
      {dotCategory && <span className={clsx("h-1.5 w-1.5 rounded-full", dotStyles[dotCategory])} />}
      {status.replace("_", " ")}
    </span>
  );
}
