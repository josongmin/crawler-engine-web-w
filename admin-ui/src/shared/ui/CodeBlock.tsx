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
        <div className="absolute top-2.5 left-3 text-[10px] font-mono uppercase tracking-wider text-fg-subtle">
          {language}
        </div>
      )}
      {showCopy && (
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 rounded-md border border-border-strong bg-surface-100 p-1.5 text-fg-muted opacity-0 transition-all hover:border-border-hover hover:text-fg-secondary group-hover:opacity-100"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      )}
      <pre className="code-block overflow-x-auto p-4 pt-8 text-fg-tertiary">
        <code>{code}</code>
      </pre>
    </div>
  );
}
