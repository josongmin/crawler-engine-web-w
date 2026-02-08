import { clsx } from "clsx";
import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className, id, ...rest }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-xs font-medium text-fg-muted">
          {label}
        </label>
      )}
      <input
        id={id}
        className={clsx(
          "h-9 rounded-lg border border-border bg-surface-0 px-3 text-sm text-fg-secondary",
          "placeholder:text-fg-subtle",
          "focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/30",
          "transition-colors",
          className,
        )}
        {...rest}
      />
    </div>
  );
}
