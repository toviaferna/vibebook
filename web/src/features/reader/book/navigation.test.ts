import { formatPageLabel, resolvePageMove } from "./navigation";

const base = {
  pageCount: 7,
  spread: false,
  hasNextChapter: true,
  hasPreviousChapter: true,
};

describe("resolvePageMove", () => {
  it("avanza una página dentro del capítulo", () => {
    expect(resolvePageMove({ ...base, pageIndex: 2, direction: "next" })).toEqual({
      kind: "page",
      index: 3,
    });
  });

  it("cruza al capítulo siguiente en la última página", () => {
    expect(resolvePageMove({ ...base, pageIndex: 6, direction: "next" })).toEqual({
      kind: "chapter",
      direction: "next",
    });
  });

  it("no cruza si no hay capítulo siguiente", () => {
    expect(
      resolvePageMove({
        ...base,
        pageIndex: 6,
        direction: "next",
        hasNextChapter: false,
      }),
    ).toEqual({ kind: "none" });
  });

  it("retrocede una página dentro del capítulo", () => {
    expect(resolvePageMove({ ...base, pageIndex: 3, direction: "prev" })).toEqual({
      kind: "page",
      index: 2,
    });
  });

  it("cruza al capítulo anterior en la primera página", () => {
    expect(resolvePageMove({ ...base, pageIndex: 0, direction: "prev" })).toEqual({
      kind: "chapter",
      direction: "prev",
    });
  });

  it("no cruza si no hay capítulo anterior", () => {
    expect(
      resolvePageMove({
        ...base,
        pageIndex: 0,
        direction: "prev",
        hasPreviousChapter: false,
      }),
    ).toEqual({ kind: "none" });
  });

  it("en spread avanza dos páginas y se detiene en el último par", () => {
    const spread = { ...base, spread: true, pageCount: 7 };
    expect(resolvePageMove({ ...spread, pageIndex: 0, direction: "next" })).toEqual({
      kind: "page",
      index: 2,
    });
    expect(resolvePageMove({ ...spread, pageIndex: 4, direction: "next" })).toEqual({
      kind: "page",
      index: 5,
    });
    expect(resolvePageMove({ ...spread, pageIndex: 5, direction: "next" })).toEqual({
      kind: "chapter",
      direction: "next",
    });
  });

  it("con una sola página en spread cruza de capítulo", () => {
    expect(
      resolvePageMove({
        ...base,
        spread: true,
        pageCount: 1,
        pageIndex: 0,
        direction: "next",
      }),
    ).toEqual({ kind: "chapter", direction: "next" });
    expect(
      resolvePageMove({
        ...base,
        spread: true,
        pageCount: 1,
        pageIndex: 0,
        direction: "prev",
      }),
    ).toEqual({ kind: "chapter", direction: "prev" });
  });

  it("no mueve si no hay páginas", () => {
    expect(resolvePageMove({ ...base, pageCount: 0, pageIndex: 0, direction: "next" })).toEqual({
      kind: "none",
    });
  });
});

describe("formatPageLabel", () => {
  it("muestra una página en modo simple", () => {
    expect(formatPageLabel(2, 7, false)).toBe("Página 3 de 7");
  });

  it("muestra dos páginas en spread", () => {
    expect(formatPageLabel(2, 7, true)).toBe("Páginas 3–4 de 7");
  });

  it("no muestra rango si solo queda una página", () => {
    expect(formatPageLabel(6, 7, true)).toBe("Página 7 de 7");
  });

  it("tolera cero páginas", () => {
    expect(formatPageLabel(0, 0, false)).toBe("—");
  });
});
