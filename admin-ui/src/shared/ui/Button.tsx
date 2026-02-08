import { clsx } from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-accent-500 text-white hover:bg-accent-600 border-accent-600 shadow-md shadow-accent-500/10",
  secondary:
    "bg-surface-100 text-fg-secondary hover:bg-surface-200 border-border hover:border-border-hover",
  ghost:
    "bg-transparent text-fg-muted hover:text-fg-secondary hover:bg-surface-100 border-transparent",
  danger:
    "bg-status-danger-muted text-status-danger hover:bg-status-danger-subtle border-status-danger-subtle",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-9 px-3.5 text-sm gap-2",
  lg: "h-11 px-5 text-sm gap-2",
};

export function Button({
  variant = "secondary",
  size = "md",
  icon,
  loading,
  className,
  children,
  disabled,
  ...rest
}: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-lg border font-medium transition-all",
        "disabled:pointer-events-none disabled:opacity-40",
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}
