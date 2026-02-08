import { create } from "zustand";
import type { Job, JobLog } from "@/shared/types";

interface JobState {
  jobs: Job[];
  activeJob: Job | null;
  logs: JobLog[];
  isStreaming: boolean;

  setJobs: (j: Job[]) => void;
  setActiveJob: (j: Job | null) => void;
  appendLog: (l: JobLog) => void;
  clearLogs: () => void;
  setStreaming: (v: boolean) => void;
  updateJob: (id: string, patch: Partial<Job>) => void;
}

export const useJobStore = create<JobState>((set) => ({
  jobs: [],
  activeJob: null,
  logs: [],
  isStreaming: false,

  setJobs: (jobs) => set({ jobs }),
  setActiveJob: (activeJob) => set({ activeJob }),
  appendLog: (l) => set((s) => ({ logs: [...s.logs, l] })),
  clearLogs: () => set({ logs: [] }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  updateJob: (id, patch) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, ...patch } : j)),
    })),
}));
