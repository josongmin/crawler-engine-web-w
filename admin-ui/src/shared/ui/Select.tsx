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
        <label htmlFor={id} className="text-fg-muted text-xs font-medium">
          {label}
        </label>
      )}
      <select
        id={id}
        className={clsx(
          "border-border bg-surface-0 text-fg-secondary h-9 rounded-lg border px-3 text-sm",
          "focus:border-accent-500 focus:ring-accent-500/30 focus:ring-1 focus:outline-none",
          "appearance-none transition-colors",
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
