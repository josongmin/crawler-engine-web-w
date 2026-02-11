import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  code: string;
  language?: string;
  className?: string;
  showCopy?: boolean;
}

export function CodeBlock({ code, language, className, showCopy = true }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={clsx("group relative", className)}>
      {language && (
        <div className="text-fg-subtle absolute top-2.5 left-3 font-mono text-[10px] tracking-wider uppercase">
          {language}
        </div>
      )}
      {showCopy && (
        <button
          onClick={() => {
            void handleCopy();
          }}
          className="border-border-strong bg-surface-100 text-fg-muted hover:border-border-hover hover:text-fg-secondary absolute top-2 right-2 rounded-md border p-1.5 opacity-0 transition-all group-hover:opacity-100"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      )}
      <pre className="code-block text-fg-tertiary overflow-x-auto p-4 pt-8">
        <code>{code}</code>
      </pre>
    </div>
  );
}
