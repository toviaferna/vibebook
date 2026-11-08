import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyReaderPalette,
  applyTheme,
  readStoredReaderPalette,
  readStoredThemeMode,
  resolveTheme,
  storeReaderPalette,
  storeThemeMode,
} from "./theme";

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.readerPalette;
});

describe("theme resolver", () => {
  it("resuelve system con la preferencia del sistema", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("aplica el tema resuelto al documento", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );

    expect(applyTheme("system")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("prioriza el modo explícito sobre el sistema", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    );

    expect(applyTheme("light")).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("theme storage", () => {
  it("lee y guarda el modo de tema", () => {
    storeThemeMode("dark");
    expect(readStoredThemeMode()).toBe("dark");
  });

  it("ignora valores inválidos", () => {
    window.localStorage.setItem("vibebook.theme-mode", "neon");
    window.localStorage.setItem("vibebook.reader-palette", "violet");
    expect(readStoredThemeMode()).toBe("system");
    expect(readStoredReaderPalette()).toBe("paper");
  });

  it("guarda la paleta del lector y la aplica a un elemento", () => {
    storeReaderPalette("night");
    expect(readStoredReaderPalette()).toBe("night");

    const shell = document.createElement("div");
    applyReaderPalette("sepia", shell);
    expect(shell.dataset.readerPalette).toBe("sepia");
  });
});
