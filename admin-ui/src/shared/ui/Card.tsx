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
        "rounded-xl border border-border bg-surface-50 p-5",
        hover && "transition-colors hover:border-border-hover",
        glow && "glow-accent",
        className,
      )}
    >
      {children}
    </div>
  );
}
