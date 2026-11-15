import { afterEach, describe, expect, it, vi } from "vitest";

import { defaultReaderView, isDesktopReader } from "./viewMode";

function stubViewport(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }));
}

describe("viewMode", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("abre el libro realista en escritorio", () => {
    stubViewport(true);
    expect(isDesktopReader()).toBe(true);
    expect(defaultReaderView()).toBe("book");
  });

  it("prefiere el texto cuando no cabe un pliego", () => {
    stubViewport(false);
    expect(isDesktopReader()).toBe(false);
    expect(defaultReaderView()).toBe("text");
  });

  it("cae en texto si el entorno no expone matchMedia", () => {
    expect(defaultReaderView()).toBe("text");
  });
});
