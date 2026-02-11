import { clsx } from "clsx";
import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
}

export function Card({ children, className, hover, glow }: Props) {
  return (
    <div
      className={clsx(
        "border-border bg-surface-50 rounded-xl border p-5",
        hover && "hover:border-border-hover transition-colors",
        glow && "glow-accent",
        className,
      )}
    >
      {children}
    </div>
  );
}
