import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { clsx } from "clsx";
import type { ReactNode } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  className?: string;
  /** Max width class override (default: max-w-lg) */
  maxWidth?: string;
}

export function Dialog({
  open,
  onClose,
  title,
  children,
  className,
  maxWidth = "max-w-lg",
}: Props) {
  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="bg-overlay absolute inset-0 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden
      />
      {/* Panel */}
      <div
        role="dialog"
        aria-modal
        className={clsx(
          "border-border bg-surface-50 relative w-full rounded-xl border shadow-2xl",
          maxWidth,
          className,
        )}
      >
        {/* Header */}
        <div className="border-border flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-fg text-base font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="text-fg-subtle hover:bg-surface-100 hover:text-fg-tertiary rounded-md p-1.5 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        {/* Body */}
        <div className="p-5">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
