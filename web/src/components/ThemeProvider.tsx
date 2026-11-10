import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

import { useSettings, useUpdateSettings } from "../api/queries";
import {
  applyTheme,
  readStoredThemeMode,
  storeThemeMode,
  type ThemeMode,
  watchSystemTheme,
} from "../lib/theme";

interface ThemeContextValue {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const settings = useSettings();
  const updateSettings = useUpdateSettings();
  const [mode, setModeState] = useState<ThemeMode>(() => readStoredThemeMode());

  useEffect(() => {
    const stored = settings.data?.theme_mode;
    if (stored === "system" || stored === "light" || stored === "dark") {
      setModeState(stored);
    }
  }, [settings.data?.theme_mode]);

  useEffect(() => {
    applyTheme(mode);
    storeThemeMode(mode);
    return watchSystemTheme(() => {
      if (mode === "system") {
        applyTheme(mode);
      }
    });
  }, [mode]);

  const setMode = useCallback(
    (next: ThemeMode) => {
      setModeState(next);
      storeThemeMode(next);
      updateSettings.mutate({ theme_mode: next });
    },
    [updateSettings],
  );

  return <ThemeContext.Provider value={{ mode, setMode }}>{children}</ThemeContext.Provider>;
}

export function useThemeMode(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useThemeMode must be used inside ThemeProvider");
  }
  return value;
}
