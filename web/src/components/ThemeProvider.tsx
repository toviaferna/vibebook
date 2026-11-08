import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

import { useSettings } from "../api/queries";
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

  return (
    <ThemeContext.Provider value={{ mode, setMode: setModeState }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useThemeMode(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useThemeMode must be used inside ThemeProvider");
  }
  return value;
}
