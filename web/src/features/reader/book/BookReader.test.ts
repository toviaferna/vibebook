import { bookLayout, lastPageIndex } from "./BookReader";

describe("book spread navigation", () => {
  it("no repite la última página en un pliego impar", () => {
    expect(lastPageIndex(5, true)).toBe(4);
    expect(lastPageIndex(7, true)).toBe(6);
  });

  it("mantiene el último pliego completo cuando el total es par", () => {
    expect(lastPageIndex(4, true)).toBe(2);
    expect(lastPageIndex(6, true)).toBe(4);
  });

  it("usa una sola página cuando no hay pliego", () => {
    expect(lastPageIndex(5, false)).toBe(4);
  });

  it("pasa a una sola página cuando el contenedor es angosto", () => {
    const narrow = bookLayout(346, 320);
    expect(narrow.orientation).toBe("portrait");
    expect(narrow.rect.pageWidth).toBeLessThanOrEqual(346);

    const wide = bookLayout(1000, 820);
    expect(wide.orientation).toBe("landscape");
    expect(wide.rect.pageWidth).toBeGreaterThan(300);
  });
});
