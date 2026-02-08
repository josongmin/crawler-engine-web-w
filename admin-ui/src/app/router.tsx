import { Routes, Route, Navigate } from "react-router-dom";
import { OverviewPage } from "@/pages/overview/OverviewPage";
import { SitesPage } from "@/pages/sites/SitesPage";
import { WorkflowsPage } from "@/pages/workflows/WorkflowsPage";
import { WorkflowBuilderPage } from "@/pages/workflows/WorkflowBuilderPage";
import { JobsPage } from "@/pages/jobs/JobsPage";
import { RulesPage } from "@/pages/rules/RulesPage";
import { RuleEditorPage } from "@/pages/rules/RuleEditorPage";
import { PlaygroundPage } from "@/pages/playground/PlaygroundPage";
import { LogsPage } from "@/pages/logs/LogsPage";
import { SITES } from "@/shared/config/sites";

export function AppRouter() {
  return (
    <Routes>
      {/* Overview (cross-site dashboard) */}
      <Route path="/" element={<OverviewPage />} />

      {/* Site hub (per-site command center) */}
      <Route
        path="/sites"
        element={<Navigate to={`/sites/${SITES[0].id}`} replace />}
      />
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
  );
}
