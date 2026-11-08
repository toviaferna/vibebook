import type { Contents } from "epubjs";

import { sanitize } from "./OriginalEpubView";

describe("sanitize original EPUB content", () => {
  it("elimina scripts, handlers, formularios y recursos externos", () => {
    const document = window.document.implementation.createHTMLDocument("chapter");
    document.body.innerHTML = `
      <base href="https://evil.example/" />
      <meta http-equiv="refresh" content="0;url=https://evil.example" />
      <script>window.pwned = true;</script>
      <iframe src="https://evil.example"></iframe>
      <form action="https://evil.example"><input /></form>
      <p onclick="window.pwned = true">Hola</p>
      <img src="https://evil.example/pixel.gif" />
      <a href="javascript:alert(1)">malo</a>
      <a href="https://evil.example">externo</a>
      <a href="chapter_2.xhtml">interno</a>
    `;

    sanitize({ document } as unknown as Contents);

    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("iframe")).toBeNull();
    expect(document.querySelector("form")).toBeNull();
    expect(document.querySelector("base")).toBeNull();
    expect(document.querySelector("meta[http-equiv='refresh']")).toBeNull();
    expect(document.querySelector("p")?.hasAttribute("onclick")).toBe(false);
    expect(document.querySelector("img")?.hasAttribute("src")).toBe(false);
    expect(document.querySelector("a[href^='javascript']")).toBeNull();
    expect(document.querySelector("a[href^='https']")).toBeNull();
    expect(document.querySelector("a[href='chapter_2.xhtml']")).not.toBeNull();
    expect(
      document.head.querySelector("meta[http-equiv='Content-Security-Policy']"),
    ).not.toBeNull();
  });
});
