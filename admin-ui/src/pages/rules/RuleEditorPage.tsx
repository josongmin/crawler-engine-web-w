import { useState } from "react";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { CodeBlock } from "@/shared/ui/CodeBlock";
import { StatusBadge } from "@/shared/ui/StatusBadge";
import { Play, Save, Download, History, Code2, FormInput } from "lucide-react";
import { clsx } from "clsx";

const MOCK_RULE_JSON = `{
  "name": "search-results",
  "page_type": "search",
  "url_pattern": "tnsearch/tasting_notes\\\\.php",
  "extract": {
    "container": "table#results tbody tr",
    "fields": {
      "producer": {
        "selector": ["td:nth-child(1)", "td.producer"],
        "type": "text",
        "transform": { "name": "trim" }
      },
      "wine": {
        "selector": "td:nth-child(2)",
        "type": "text"
      },
      "vintage": {
        "selector": "td:nth-child(3)",
        "type": "text",
        "post_process": "int"
      },
      "score": {
        "selector": "td:nth-child(4)",
        "type": "text"
      },
      "detail_url": {
        "selector": "td:nth-child(2) a",
        "type": "attr",
        "attr": "href",
        "transform": {
          "name": "absolute_url",
          "base": "https://www.burghound.com"
        }
      }
    }
  },
  "pagination": {
    "type": "click",
    "next_selector": "a.next-page",
    "has_next": "a.next-page:not(.disabled)",
    "max_pages": 100,
    "delay_between_ms": { "min": 1500, "max": 3000 }
  },
  "throttle": {
    "requests_per_minute": 20,
    "delay_ms": { "min": 800, "max": 2000 }
  }
}`;

const mockExtracted = [
  { producer: "DRC", wine: "La Tache", vintage: 2019, score: "96-98" },
  { producer: "DRC", wine: "Romanee-Conti", vintage: 2019, score: "98-100" },
  { producer: "Leroy", wine: "Musigny", vintage: 2018, score: "95-97" },
  { producer: "Rousseau", wine: "Chambertin", vintage: 2020, score: "94-96" },
  { producer: "Coche-Dury", wine: "Corton-Charlemagne", vintage: 2019, score: "96-98" },
];

const fields = [
  { name: "producer", selector: "td:nth-child(1)", matched: 25, total: 25 },
  { name: "wine", selector: "td:nth-child(2)", matched: 25, total: 25 },
  { name: "vintage", selector: "td:nth-child(3)", matched: 25, total: 25 },
  { name: "score", selector: "td:nth-child(4)", matched: 25, total: 25 },
  { name: "detail_url", selector: "td:nth-child(2) a", matched: 25, total: 25 },
];

export function RuleEditorPage() {
  const [mode, setMode] = useState<"form" | "json">("form");
  const [testUrl, setTestUrl] = useState(
    "https://www.burghound.com/tnsearch/tasting_notes.php?search=romanee",
  );

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-fg text-lg font-semibold">search-results</h2>
          <span className="bg-surface-200 text-fg-subtle rounded px-1.5 py-0.5 font-mono text-[10px]">
            v3
          </span>
          <StatusBadge status="active" />
        </div>
        <div className="flex items-center gap-2">
          <div className="border-border bg-surface-50 flex rounded-lg border p-0.5">
            <button
              onClick={() => setMode("form")}
              className={clsx(
                "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "form"
                  ? "bg-surface-200 text-fg-secondary"
                  : "text-fg-subtle hover:text-fg-tertiary",
              )}
            >
              <FormInput size={12} /> Form
            </button>
            <button
              onClick={() => setMode("json")}
              className={clsx(
                "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "json"
                  ? "bg-surface-200 text-fg-secondary"
                  : "text-fg-subtle hover:text-fg-tertiary",
              )}
            >
              <Code2 size={12} /> JSON
            </button>
          </div>
          <Button size="sm" icon={<Play size={14} />} variant="primary">
            Test Rule
          </Button>
          <Button size="sm" icon={<Save size={14} />}>
            Save as v4
          </Button>
          <Button size="sm" icon={<Download size={14} />}>
            Export
          </Button>
          <Button size="sm" icon={<History size={14} />}>
            History
          </Button>
        </div>
      </div>

      {/* Split pane */}
      <div className="grid grid-cols-2 gap-4">
        {/* Left: Rule Definition */}
        <div className="space-y-4">
          {mode === "json" ? (
            <Card className="p-0">
              <CodeBlock code={MOCK_RULE_JSON} language="json" showCopy={false} />
            </Card>
          ) : (
            <>
              <Card>
                <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
                  Container
                </h3>
                <Input defaultValue="table#results tbody tr" className="font-mono text-xs" />
              </Card>

              <Card>
                <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
                  Fields
                </h3>
                <div className="space-y-2">
                  {fields.map((f) => (
                    <div
                      key={f.name}
                      className="bg-surface-0 flex items-center justify-between rounded-lg px-3 py-2.5"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-fg-secondary w-24 text-sm font-medium">{f.name}</span>
                        <code className="text-fg-muted text-xs">{f.selector}</code>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={clsx(
                            "font-mono text-xs",
                            f.matched === f.total ? "text-status-success" : "text-status-danger",
                          )}
                        >
                          {f.matched}/{f.total}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <Button size="sm" variant="ghost" className="mt-3">
                  + Add Field
                </Button>
              </Card>

              <Card>
                <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
                  Pagination
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Type" defaultValue="click" className="font-mono text-xs" />
                  <Input
                    label="Next Selector"
                    defaultValue="a.next-page"
                    className="font-mono text-xs"
                  />
                  <Input label="Max Pages" defaultValue="100" type="number" />
                  <Input label="Delay (ms)" defaultValue="1500-3000" />
                </div>
              </Card>

              <Card>
                <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
                  Throttle
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <Input label="Requests/min" defaultValue="20" type="number" />
                  <Input label="Delay (ms)" defaultValue="800-2000" />
                </div>
              </Card>
            </>
          )}
        </div>

        {/* Right: Live Preview */}
        <div className="space-y-4">
          <Card>
            <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
              Test URL
            </h3>
            <div className="flex gap-2">
              <Input
                value={testUrl}
                onChange={(e) => setTestUrl(e.target.value)}
                className="flex-1 font-mono text-xs"
              />
              <Button variant="primary" size="sm" icon={<Play size={14} />}>
                Load & Preview
              </Button>
            </div>
          </Card>

          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-fg-subtle text-xs font-semibold tracking-wider uppercase">
                Extracted Data
              </h3>
              <span className="bg-status-success-muted text-status-success rounded px-2 py-0.5 text-xs font-medium">
                Matched: {mockExtracted.length} rows
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-border text-fg-subtle border-b">
                    <th className="py-2 pr-4 font-medium">producer</th>
                    <th className="py-2 pr-4 font-medium">wine</th>
                    <th className="py-2 pr-4 font-medium">vintage</th>
                    <th className="py-2 font-medium">score</th>
                  </tr>
                </thead>
                <tbody>
                  {mockExtracted.map((row, i) => (
                    <tr key={i} className="border-border/50 text-fg-tertiary border-b">
                      <td className="py-2 pr-4">{row.producer}</td>
                      <td className="py-2 pr-4">{row.wine}</td>
                      <td className="py-2 pr-4 font-mono">{row.vintage}</td>
                      <td className="py-2 font-mono">{row.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
              Selector Validation
            </h3>
            <div className="space-y-1.5">
              {fields.map((f) => (
                <div key={f.name} className="flex items-center justify-between text-xs">
                  <code className="text-fg-muted">{f.selector}</code>
                  <span className="text-status-success font-mono">{f.matched} matched</span>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="text-fg-subtle mb-3 text-xs font-semibold tracking-wider uppercase">
              Raw JSON
            </h3>
            <CodeBlock code={JSON.stringify(mockExtracted[0], null, 2)} language="json" />
          </Card>
        </div>
      </div>
    </div>
  );
}
