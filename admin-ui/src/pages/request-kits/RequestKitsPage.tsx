import { useState } from "react";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { CodeBlock } from "@/shared/ui/CodeBlock";
import { Select } from "@/shared/ui/Select";
import { Input } from "@/shared/ui/Input";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Send, RefreshCw, ShieldCheck } from "lucide-react";

const MOCK_CURL = `curl 'https://www.burghound.com/tnsearch/tasting_notes.php?search=romanee' \\
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36' \\
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \\
  -H 'Accept-Language: en-US,en;q=0.9' \\
  -H 'Cookie: PHPSESSID=abc123def456; tn_user=xyz789; remember_me=token_here'`;

const MOCK_HTTPX = `import httpx

cookies = {
    "PHPSESSID": "abc123def456",
    "tn_user": "xyz789",
    "remember_me": "token_here",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
}

r = httpx.get(
    "https://www.burghound.com/tnsearch/tasting_notes.php?search=romanee",
    cookies=cookies,
    headers=headers,
)
print(r.status_code, len(r.text))`;

const snippets: Record<string, { code: string; lang: string }> = {
  curl: { code: MOCK_CURL, lang: "bash" },
  httpx: { code: MOCK_HTTPX, lang: "python" },
  cookies: {
    code: "# Netscape HTTP Cookie File\n.burghound.com\tTRUE\t/\tFALSE\t1717829400\tPHPSESSID\tabc123def456",
    lang: "text",
  },
};

const history = [
  { id: "#5", format: "curl", ago: "2 min", used: 0, status: "pass" },
  { id: "#4", format: "httpx", ago: "1h", used: 3, status: "pass" },
  { id: "#3", format: "curl", ago: "3h", used: 12, status: "fail" },
];

export function RequestKitsPage() {
  const [format, setFormat] = useState("curl");

  const current = snippets[format] ?? snippets.curl;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Export Panel */}
      <Card glow>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-fg text-base font-semibold">
            Export Request Kit
            <span className="text-fg-subtle ml-2 text-sm font-normal">burghound</span>
          </h2>
          <StatusBadge status="active" />
        </div>

        {/* Controls */}
        <div className="mb-4 grid grid-cols-3 gap-4">
          <Select
            label="Format"
            options={[
              { value: "curl", label: "cURL (minimal headers)" },
              { value: "httpx", label: "httpx (Python)" },
              { value: "cookies", label: "Raw Cookies (Netscape)" },
              { value: "storage_state", label: "Storage State (Playwright)" },
            ]}
            value={format}
            onChange={(e) => setFormat(e.target.value)}
          />
          <Input
            label="Base URL"
            placeholder="https://www.burghound.com/tnsearch/..."
            defaultValue="https://www.burghound.com/tnsearch/tasting_notes.php"
          />
          <div className="flex items-end gap-2">
            <Button variant="primary" icon={<Send size={14} />}>
              Export
            </Button>
            <Button icon={<RefreshCw size={14} />}>Re-login & Export</Button>
          </div>
        </div>

        {/* Snippet */}
        <CodeBlock code={current.code} language={current.lang} />
      </Card>

      <div className="grid grid-cols-2 gap-4">
        {/* Kit Health */}
        <Card>
          <h3 className="text-fg-tertiary mb-3 text-sm font-semibold">Kit Health</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-fg-subtle">Session valid</span>
              <span className="text-status-success">PHPSESSID expires in 23h</span>
            </div>
            <div className="flex justify-between">
              <span className="text-fg-subtle">Cookies</span>
              <span className="text-fg-tertiary">3 (PHPSESSID, tn_user, remember)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-fg-subtle">Headers</span>
              <span className="text-fg-tertiary">4 minimal</span>
            </div>
            <div className="flex justify-between">
              <span className="text-fg-subtle">Persona match</span>
              <span className="text-status-success">UA consistent</span>
            </div>
          </div>
          <div className="mt-4">
            <Button size="sm" icon={<ShieldCheck size={14} />}>
              Validate Kit
            </Button>
          </div>
        </Card>

        {/* Export History */}
        <Card>
          <h3 className="text-fg-tertiary mb-3 text-sm font-semibold">Export History</h3>
          <div className="space-y-2">
            {history.map((h) => (
              <div
                key={h.id}
                className="bg-surface-0 flex items-center justify-between rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span className="text-fg-subtle font-mono text-xs">{h.id}</span>
                  <span className="bg-surface-200 text-fg-muted rounded px-1.5 py-0.5 font-mono text-[10px]">
                    {h.format}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-fg-subtle text-xs">{h.ago}</span>
                  <span className="text-fg-subtle text-xs">used {h.used}x</span>
                  <StatusBadge status={h.status} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
