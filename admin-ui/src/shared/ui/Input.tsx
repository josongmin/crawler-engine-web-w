import { clsx } from "clsx";
import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className, id, ...rest }: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-fg-muted text-xs font-medium">
          {label}
        </label>
      )}
      <input
        id={id}
        className={clsx(
          "border-border bg-surface-0 text-fg-secondary h-9 rounded-lg border px-3 text-sm",
          "placeholder:text-fg-subtle",
          "focus:border-accent-500 focus:ring-accent-500/30 focus:ring-1 focus:outline-none",
          "transition-colors",
          className,
        )}
        {...rest}
      />
    </div>
  );
}
