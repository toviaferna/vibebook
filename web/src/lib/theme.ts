export type ThemeMode = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";
export type ReaderPalette = "paper" | "sepia" | "night";

const THEME_STORAGE_KEY = "vibebook.theme-mode";
const PALETTE_STORAGE_KEY = "vibebook.reader-palette";

const VALID_THEME_MODES: ThemeMode[] = ["system", "light", "dark"];
const VALID_PALETTES: ReaderPalette[] = ["paper", "sepia", "night"];

export function resolveTheme(mode: ThemeMode, prefersDark: boolean): ResolvedTheme {
  if (mode === "system") {
    return prefersDark ? "dark" : "light";
  }
  return mode;
}

export function readStoredThemeMode(): ThemeMode {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return VALID_THEME_MODES.includes(stored as ThemeMode) ? (stored as ThemeMode) : "system";
}

export function storeThemeMode(mode: ThemeMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(THEME_STORAGE_KEY, mode);
}

export function readStoredReaderPalette(): ReaderPalette {
  if (typeof window === "undefined") return "paper";
  const stored = window.localStorage.getItem(PALETTE_STORAGE_KEY);
  return VALID_PALETTES.includes(stored as ReaderPalette) ? (stored as ReaderPalette) : "paper";
}

export function storeReaderPalette(palette: ReaderPalette): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PALETTE_STORAGE_KEY, palette);
}

export function prefersDarkScheme(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function applyTheme(mode: ThemeMode): ResolvedTheme {
  const resolved = resolveTheme(mode, prefersDarkScheme());
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
    const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
    if (meta) {
      meta.content = resolved === "dark" ? "#101613" : "#f1f2ec";
    }
  }
  return resolved;
}

export function applyReaderPalette(
  palette: ReaderPalette,
  element: HTMLElement | null = typeof document === "undefined" ? null : document.documentElement,
): void {
  if (!element) return;
  element.dataset.readerPalette = palette;
}

export function watchSystemTheme(onChange: (prefersDark: boolean) => void): () => void {
  if (typeof window === "undefined" || !window.matchMedia) return () => {};
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const listener = (event: MediaQueryListEvent) => onChange(event.matches);
  query.addEventListener?.("change", listener);
  return () => query.removeEventListener?.("change", listener);
}
