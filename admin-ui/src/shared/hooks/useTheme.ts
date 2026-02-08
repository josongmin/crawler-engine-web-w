/* ── Theme Management ────────────────────────────────
 *
 * Manages dark / light / system theme with:
 *   - localStorage persistence (key: "wc-admin-theme")
 *   - prefers-color-scheme media query listener
 *   - Smooth transition class during switches
 *   - <html> class toggling (.dark)
 *
 * Usage:
 *   const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
 *
 * `theme`          → user's preference: "light" | "dark" | "system"
 * `resolvedTheme`  → actual applied theme: "light" | "dark"
 * ──────────────────────────────────────────────────── */

import { useCallback, useEffect, useSyncExternalStore } from "react";

// ── Constants ───────────────────────────────────────

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "wc-admin-theme";
const TRANSITION_CLASS = "theme-transition";
const TRANSITION_DURATION = 220; // ms — matches CSS

// ── External store ──────────────────────────────────

type Listener = () => void;

let listeners: Listener[] = [];

function subscribe(listener: Listener): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

function getSnapshot(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "dark"; // default for dev tools
}

function getServerSnapshot(): ThemePreference {
  return "dark";
}

// ── Helpers ─────────────────────────────────────────

function getSystemPreference(): ResolvedTheme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function resolveTheme(pref: ThemePreference): ResolvedTheme {
  return pref === "system" ? getSystemPreference() : pref;
}

function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement;
  if (resolved === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

function applyWithTransition(resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.add(TRANSITION_CLASS);
  applyTheme(resolved);
  // Remove transition class after animation completes
  setTimeout(() => {
    root.classList.remove(TRANSITION_CLASS);
  }, TRANSITION_DURATION);
}

// ── Hook ────────────────────────────────────────────

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const resolvedTheme = resolveTheme(theme);

  // Apply theme to DOM on mount and when preference changes
  useEffect(() => {
    applyTheme(resolvedTheme);
  }, [resolvedTheme]);

  // Listen for OS-level dark mode changes when mode is "system"
  useEffect(() => {
    if (theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      applyWithTransition(getSystemPreference());
      emitChange();
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [theme]);

  const setTheme = useCallback((next: ThemePreference) => {
    localStorage.setItem(STORAGE_KEY, next);
    const resolved = resolveTheme(next);
    applyWithTransition(resolved);
    emitChange();
  }, []);

  const toggleTheme = useCallback(() => {
    const current = getSnapshot();
    const resolved = resolveTheme(current);
    // Cycle: current resolved → opposite
    const next: ThemePreference = resolved === "dark" ? "light" : "dark";
    setTheme(next);
  }, [setTheme]);

  return { theme, resolvedTheme, setTheme, toggleTheme } as const;
}
