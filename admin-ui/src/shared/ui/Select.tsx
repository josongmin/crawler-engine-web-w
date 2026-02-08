import { clsx } from "clsx";
import type { SelectHTMLAttributes } from "react";

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
}

export function Select({ label, options, className, id, ...rest }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-xs font-medium text-fg-muted">
          {label}
        </label>
      )}
      <select
        id={id}
        className={clsx(
          "h-9 rounded-lg border border-border bg-surface-0 px-3 text-sm text-fg-secondary",
          "focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/30",
          "transition-colors appearance-none",
          className,
        )}
        {...rest}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
