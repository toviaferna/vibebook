import { chapterDisplayTitle } from "./chapterTitle";

describe("chapterDisplayTitle", () => {
  it("conserva títulos reales", () => {
    expect(chapterDisplayTitle({ title: "La casa de los relojes", number: null })).toBe(
      "La casa de los relojes",
    );
  });

  it("muestra Capítulo N para títulos numéricos", () => {
    expect(chapterDisplayTitle({ title: "1", number: 1 })).toBe("Capítulo 1");
  });

  it("no duplica el prefijo si el título ya lo trae", () => {
    expect(chapterDisplayTitle({ title: "Capítulo 2", number: 2 })).toBe("Capítulo 2");
  });

  it("usa el número si el título está vacío", () => {
    expect(chapterDisplayTitle({ title: "", number: 3 })).toBe("Capítulo 3");
  });
});
