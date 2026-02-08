import { create } from "zustand";
import type { CrawlRule, RuleTestResult } from "@/shared/types";

interface RuleState {
  rules: CrawlRule[];
  activeRule: CrawlRule | null;
  testResult: RuleTestResult | null;
  editorMode: "form" | "json";
  isDirty: boolean;

  setRules: (r: CrawlRule[]) => void;
  setActiveRule: (r: CrawlRule | null) => void;
  setTestResult: (t: RuleTestResult | null) => void;
  setEditorMode: (m: "form" | "json") => void;
  setDirty: (d: boolean) => void;
}

export const useRuleStore = create<RuleState>((set) => ({
  rules: [],
  activeRule: null,
  testResult: null,
  editorMode: "form",
  isDirty: false,

  setRules: (rules) => set({ rules }),
  setActiveRule: (activeRule) => set({ activeRule }),
  setTestResult: (testResult) => set({ testResult }),
  setEditorMode: (editorMode) => set({ editorMode }),
  setDirty: (isDirty) => set({ isDirty }),
}));
