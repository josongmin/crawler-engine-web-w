import { create } from "zustand";
import type { Session, Persona, Cookie } from "@/shared/types";

interface SessionState {
  sessions: Session[];
  activeSite: string | null;
  persona: Persona | null;
  cookies: Cookie[];

  setSessions: (s: Session[]) => void;
  setActiveSite: (site: string | null) => void;
  setPersona: (p: Persona | null) => void;
  setCookies: (c: Cookie[]) => void;
  updateSession: (site: string, patch: Partial<Session>) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  activeSite: null,
  persona: null,
  cookies: [],

  setSessions: (sessions) => set({ sessions }),
  setActiveSite: (activeSite) => set({ activeSite }),
  setPersona: (persona) => set({ persona }),
  setCookies: (cookies) => set({ cookies }),
  updateSession: (site, patch) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.site === site ? { ...s, ...patch } : s,
      ),
    })),
}));
