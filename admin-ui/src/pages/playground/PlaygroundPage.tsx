import { useState } from "react";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { Select } from "@/shared/ui/Select";
import { CodeBlock } from "@/shared/ui/CodeBlock";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Loader2, Zap, Globe, FileCode2, Send, FlaskConical } from "lucide-react";
import { clsx } from "clsx";

type Tab = "scrape" | "test-rule" | "export-kit";

const MOCK_RESULT = `{
  "url": "https://www.burghound.com/tnsearch/tasting_notes.php?search=romanee",
  "status": 200,
  "items_extracted": 25,
  "duration_ms": 3420,
  "data": [
    {
      "producer": "Domaine de la Romanee-Conti",
      "wine": "La Tache",
      "vintage": 2019,
      "score": "96-98",
      "drink_from": 2028,
      "drink_to": 2060,
      "detail_url": "/tnsearch/tasting_notes_detail.php?id=12345"
    },
    {
      "producer": "Domaine de la Romanee-Conti",
      "wine": "Romanee-Conti",
      "vintage": 2019,
      "score": "98-100",
      "drink_from": 2030,
      "drink_to": 2065,
      "detail_url": "/tnsearch/tasting_notes_detail.php?id=12346"
    },
    {
      "producer": "Domaine Leroy",
      "wine": "Musigny Grand Cru",
      "vintage": 2018,
      "score": "95-97",
      "drink_from": 2026,
      "drink_to": 2055,
      "detail_url": "/tnsearch/tasting_notes_detail.php?id=12347"
    }
  ]
}`;

const MOCK_LOG_LINES = [
  { time: "19:41:42", level: "INFO", msg: "Launching stealth browser..." },
  { time: "19:41:44", level: "INFO", msg: "Loading persona: Chrome/144.0 on macOS" },
  { time: "19:41:45", level: "INFO", msg: "Navigating to target URL" },
  { time: "19:41:47", level: "INFO", msg: "Applying rule: search-results v3" },
  { time: "19:41:48", level: "INFO", msg: 'Container matched: 25 rows in "table#results tbody tr"' },
  { time: "19:41:48", level: "INFO", msg: "Extracting fields: producer, wine, vintage, score, detail_url" },
  { time: "19:41:49", level: "INFO", msg: "All selectors validated: 25/25 matched" },
  { time: "19:41:49", level: "INFO", msg: "Extraction complete: 25 items in 3420ms" },
];

export function PlaygroundPage() {
  const [tab, setTab] = useState<Tab>("scrape");
  const [url, setUrl] = useState("https://www.burghound.com/tnsearch/tasting_notes.php?search=romanee");
  const [isRunning, setIsRunning] = useState(false);
  const [hasResult, setHasResult] = useState(false);

  const handleRun = () => {
    setIsRunning(true);
    setHasResult(false);
    setTimeout(() => {
      setIsRunning(false);
      setHasResult(true);
    }, 2000);
  };

  const tabs: { id: Tab; label: string; icon: typeof Globe }[] = [
    { id: "scrape", label: "Scrape", icon: Globe },
    { id: "test-rule", label: "Test Rule", icon: FileCode2 },
    { id: "export-kit", label: "Export Kit", icon: Send },
  ];

  return (
    <div className="mx-auto max-w-7xl">
      {/* Hero bar */}
      <Card glow className="mb-6 border-accent-500/20">
        <div className="flex items-center gap-4">
          <div className="flex rounded-lg border border-border bg-surface-0 p-0.5">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={clsx(
                  "flex items-center gap-1.5 rounded-md px-4 py-1.5 text-xs font-medium transition-all",
                  tab === t.id
                    ? "bg-accent-muted text-accent-fg"
                    : "text-fg-subtle hover:text-fg-tertiary",
                )}
              >
                <t.icon size={13} />
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex flex-1 items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://..."
                className="h-10 w-full rounded-lg border border-border bg-surface-0 pl-4 pr-4 font-mono text-sm text-fg-secondary placeholder:text-fg-faint focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500/30"
              />
            </div>

            {tab === "test-rule" && (
              <Select
                options={[
                  { value: "r1", label: "search-results v3" },
                  { value: "r2", label: "wine-detail v2" },
                  { value: "r3", label: "producer-list v1" },
                ]}
                className="w-48"
              />
            )}

            <Button
              variant="primary"
              size="lg"
              onClick={handleRun}
              loading={isRunning}
              icon={isRunning ? undefined : <Zap size={16} />}
              className="min-w-[140px]"
            >
              {isRunning ? "Running..." : tab === "export-kit" ? "Export" : "Run"}
            </Button>
          </div>
        </div>

        {/* Options row */}
        <div className="mt-3 flex items-center gap-6 text-xs text-fg-subtle">
          {tab === "scrape" && (
            <>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" defaultChecked className="accent-accent-500" />
                Headless
              </label>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" className="accent-accent-500" />
                Follow links
              </label>
              <label className="flex items-center gap-1.5">
                Limit:
                <input
                  type="number"
                  defaultValue={10}
                  className="ml-1 h-6 w-14 rounded border border-border bg-surface-0 px-2 text-xs text-fg-tertiary focus:border-accent-500 focus:outline-none"
                />
              </label>
            </>
          )}
          {tab === "test-rule" && (
            <>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" defaultChecked className="accent-accent-500" />
                Dry-run (1 page only)
              </label>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" className="accent-accent-500" />
                Include follow
              </label>
            </>
          )}
          {tab === "export-kit" && (
            <>
              <label className="flex items-center gap-1.5">
                <input type="radio" name="fmt" value="curl" defaultChecked className="accent-accent-500" />
                cURL
              </label>
              <label className="flex items-center gap-1.5">
                <input type="radio" name="fmt" value="httpx" className="accent-accent-500" />
                httpx
              </label>
              <label className="flex items-center gap-1.5">
                <input type="radio" name="fmt" value="cookies" className="accent-accent-500" />
                Raw Cookies
              </label>
              <label className="flex items-center gap-1.5">
                <input type="checkbox" defaultChecked className="accent-accent-500" />
                Minimal headers
              </label>
            </>
          )}
        </div>
      </Card>

      {/* Results area */}
      {(isRunning || hasResult) && (
        <div className="grid grid-cols-3 gap-4">
          {/* Left: Live log */}
          <Card className="col-span-1">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-fg-subtle">
                Live Log
              </h3>
              {isRunning && (
                <Loader2 size={14} className="animate-spin text-accent-fg" />
              )}
            </div>
            <div className="space-y-0.5 font-mono text-[11px] leading-5">
              {MOCK_LOG_LINES.map((l, i) => (
                <div
                  key={i}
                  className={clsx(
                    "flex gap-2",
                    isRunning && i >= MOCK_LOG_LINES.length - 2 && "opacity-40",
                  )}
                >
                  <span className="text-fg-faint">{l.time}</span>
                  <span
                    className={clsx(
                      l.level === "INFO" && "text-status-info",
                      l.level === "WARN" && "text-status-warning",
                      l.level === "ERROR" && "text-status-danger",
                    )}
                  >
                    {l.level}
                  </span>
                  <span className="text-fg-muted">{l.msg}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Right: Result */}
          <div className="col-span-2 space-y-4">
            {hasResult && (
              <>
                {/* Stats bar */}
                <div className="flex items-center gap-4">
                  <StatusBadge status="success" />
                  <span className="font-mono text-xs text-fg-muted">25 items</span>
                  <span className="font-mono text-xs text-fg-subtle">3420ms</span>
                  <span className="font-mono text-xs text-fg-subtle">status: 200</span>
                </div>
                <Card className="p-0">
                  <CodeBlock code={MOCK_RESULT} language="json" />
                </Card>
              </>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isRunning && !hasResult && (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="mb-4 rounded-2xl bg-surface-50 p-6">
            <FlaskConical size={40} className="text-fg-faint" strokeWidth={1.2} />
          </div>
          <h3 className="text-lg font-medium text-fg-tertiary">Ready to crawl</h3>
          <p className="mt-1 max-w-md text-sm text-fg-subtle">
            Enter a URL above and hit Run to scrape a page, test a rule against live data,
            or export a Request Kit for external use.
          </p>
        </div>
      )}
    </div>
  );
}
