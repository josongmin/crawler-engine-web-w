import { create } from "zustand";
import type { RequestKit } from "@/shared/types";

type ExportFormat = "curl" | "httpx" | "cookies" | "storage_state";

interface RequestKitState {
  kits: RequestKit[];
  activeKit: RequestKit | null;
  exportFormat: ExportFormat;
  minimalHeaders: boolean;
  baseUrl: string;

  setKits: (k: RequestKit[]) => void;
  setActiveKit: (k: RequestKit | null) => void;
  setExportFormat: (f: ExportFormat) => void;
  setMinimalHeaders: (v: boolean) => void;
  setBaseUrl: (u: string) => void;
}

export const useRequestKitStore = create<RequestKitState>((set) => ({
  kits: [],
  activeKit: null,
  exportFormat: "curl",
  minimalHeaders: true,
  baseUrl: "",

  setKits: (kits) => set({ kits }),
  setActiveKit: (activeKit) => set({ activeKit }),
  setExportFormat: (exportFormat) => set({ exportFormat }),
  setMinimalHeaders: (minimalHeaders) => set({ minimalHeaders }),
  setBaseUrl: (baseUrl) => set({ baseUrl }),
}));
