import { useState } from "react";
import { Dialog } from "@/shared/ui/Dialog";
import { Button } from "@/shared/ui/Button";
import { ClipboardPaste, Cookie, Globe, FileJson } from "lucide-react";
import { clsx } from "clsx";

// ── Types ──────────────────────────────────────────────

export type PasteMode = "cookies" | "headers" | "storage-state";

interface Props {
  open: boolean;
  onClose: () => void;
  siteName: string;
  onSubmit: (mode: PasteMode, content: string) => void;
}

// ── Mode definitions ───────────────────────────────────

const modes: {
  id: PasteMode;
  label: string;
  icon: typeof Cookie;
  hint: string;
  placeholder: string;
}[] = [
  {
    id: "cookies",
    label: "Cookie String",
    icon: Cookie,
    hint: "Paste from DevTools → Network tab → Request Headers → Cookie value. Supports both 'key=value; key2=value2' format and line-separated 'key=value' pairs.",
    placeholder: "PHPSESSID=abc123def456; tn_user=xyz789; remember_me=token_here",
  },
  {
    id: "headers",
    label: "Headers",
    icon: Globe,
    hint: "Paste key: value pairs from DevTools → Network → select request → copy request headers. Include at minimum the Cookie header.",
    placeholder: [
      "Cookie: PHPSESSID=abc123; tn_user=xyz789",
      "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
      "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language: en-US,en;q=0.9",
    ].join("\n"),
  },
  {
    id: "storage-state",
    label: "Storage State",
    icon: FileJson,
    hint: "Paste the full Playwright storage state JSON. Get it from: await context.storageState() or the state.json file in storage_state/<site>/.",
    placeholder: JSON.stringify(
      {
        cookies: [
          {
            name: "PHPSESSID",
            value: "abc123",
            domain: ".example.com",
            path: "/",
          },
        ],
        origins: [],
      },
      null,
      2,
    ),
  },
];

// ── Component ──────────────────────────────────────────

export function PasteAuthDialog({ open, onClose, siteName, onSubmit }: Props) {
  const [mode, setMode] = useState<PasteMode>("cookies");
  const [content, setContent] = useState("");

  const current = modes.find((m) => m.id === mode)!;

  const handleSubmit = () => {
    const trimmed = content.trim();
    if (!trimmed) return;
    onSubmit(mode, trimmed);
    setContent("");
    onClose();
  };

  const handleClose = () => {
    setContent("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} title={`Paste Authentication — ${siteName}`}>
      {/* Mode selector */}
      <div className="border-border bg-surface-0 mb-4 flex gap-0.5 rounded-lg border p-0.5">
        {modes.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={clsx(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-colors",
              mode === m.id
                ? "bg-accent-muted text-accent-fg"
                : "text-fg-subtle hover:text-fg-tertiary",
            )}
          >
            <m.icon size={13} />
            {m.label}
          </button>
        ))}
      </div>

      {/* Hint */}
      <p className="text-fg-subtle mb-3 text-xs leading-relaxed">{current.hint}</p>

      {/* Textarea */}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder={current.placeholder}
        rows={8}
        className="border-border bg-surface-0 text-fg-tertiary placeholder:text-fg-faint focus:border-accent-500 focus:ring-accent-500/30 w-full rounded-lg border p-3 font-mono text-xs leading-relaxed focus:ring-1 focus:outline-none"
        spellCheck={false}
        autoFocus
      />

      {/* Actions */}
      <div className="mt-4 flex items-center justify-between">
        <p className="text-fg-faint text-[11px]">
          {content.trim().length > 0
            ? `${content.trim().length} characters`
            : "Paste your auth data above"}
        </p>
        <div className="flex gap-2">
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            variant="primary"
            icon={<ClipboardPaste size={14} />}
            onClick={handleSubmit}
            disabled={!content.trim()}
          >
            Apply & Login
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
