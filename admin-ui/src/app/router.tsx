import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { SITES } from "@/shared/config/sites";

// Lazy load pages for code splitting
const OverviewPage = lazy(() =>
  import("@/pages/overview/OverviewPage").then((m) => ({ default: m.OverviewPage })),
);
const SitesPage = lazy(() =>
  import("@/pages/sites/SitesPage").then((m) => ({ default: m.SitesPage })),
);
const WorkflowsPage = lazy(() =>
  import("@/pages/workflows/WorkflowsPage").then((m) => ({ default: m.WorkflowsPage })),
);
const WorkflowBuilderPage = lazy(() =>
  import("@/pages/workflows/WorkflowBuilderPage").then((m) => ({ default: m.WorkflowBuilderPage })),
);
const JobsPage = lazy(() => import("@/pages/jobs/JobsPage").then((m) => ({ default: m.JobsPage })));
const RulesPage = lazy(() =>
  import("@/pages/rules/RulesPage").then((m) => ({ default: m.RulesPage })),
);
const RuleEditorPage = lazy(() =>
  import("@/pages/rules/RuleEditorPage").then((m) => ({ default: m.RuleEditorPage })),
);
const PlaygroundPage = lazy(() =>
  import("@/pages/playground/PlaygroundPage").then((m) => ({ default: m.PlaygroundPage })),
);
const LogsPage = lazy(() => import("@/pages/logs/LogsPage").then((m) => ({ default: m.LogsPage })));

function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-fg-subtle text-sm">Loading...</div>
    </div>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Overview (cross-site dashboard) */}
        <Route path="/" element={<OverviewPage />} />

        {/* Site hub (per-site command center) */}
        <Route path="/sites" element={<Navigate to={`/sites/${SITES[0].id}`} replace />} />
        <Route path="/sites/:site" element={<SitesPage />} />

        {/* Workflows (visual pipeline builder) */}
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/new" element={<WorkflowBuilderPage />} />
        <Route path="/workflows/:id" element={<WorkflowBuilderPage />} />

        {/* Tools */}
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="/rules/:id" element={<RuleEditorPage />} />
        <Route path="/playground" element={<PlaygroundPage />} />
        <Route path="/logs" element={<LogsPage />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
