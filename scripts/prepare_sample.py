"""Extract one chapter from the sample EPUB and build a one-chapter EPUB.

This is a bake-off utility, not the product cleaner. It keeps the chapter text
and a minimal EPUB container so Audiblez can process a single chapter quickly.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "samples" / "lazarillo.epub"
CHAPTER = "OEBPS/9106994058927650652_320-h-2.htm.html"
OUT_TXT = ROOT / "samples" / "tratado_primero.txt"
OUT_EPUB = ROOT / "samples" / "tratado_primero.epub"
BOOK_ID = "audiol-sample-lazarillo-tratado-1"
BOOK_TITLE = "Lazarillo de Tormes - Tratado Primero"


def clean_fragment(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment)
    return re.sub(r"\s+", " ", fragment).strip()


def extract_chapter() -> tuple[str, str, list[str]]:
    with zipfile.ZipFile(SRC) as z:
        raw = z.read(CHAPTER).decode("utf-8")

    h2 = clean_fragment(re.search(r"<h2[^>]*>(.*?)</h2>", raw, re.S).group(1))
    h3 = clean_fragment(re.search(r"<h3[^>]*>(.*?)</h3>", raw, re.S).group(1))
    paragraphs = [
        clean_fragment(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", raw, re.S)
    ]
    paragraphs = [p for p in paragraphs if p]

    deduped: list[str] = []
    for paragraph in paragraphs:
        if not deduped or paragraph != deduped[-1]:
            deduped.append(paragraph)
    return h2, h3, deduped


def xhtml_body(h2: str, h3: str, paragraphs: list[str]) -> str:
    body = [f"<h1>{html.escape(h2)}</h1>", f"<h2>{html.escape(h3)}</h2>"]
    body.extend(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    return "\n".join(body)


def build_epub(h2: str, h3: str, paragraphs: list[str]) -> None:
    chapter = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es">
<head><title>{html.escape(h2)}</title><meta charset="utf-8"/></head>
<body>
{xhtml_body(h2, h3, paragraphs)}
</body>
</html>
"""

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{html.escape(BOOK_TITLE)}</dc:title>
    <dc:language>es</dc:language>
    <dc:identifier id="bookid">{BOOK_ID}</dc:identifier>
    <dc:creator>Anonimo</dc:creator>
  </metadata>
  <manifest>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx"><itemref idref="chapter"/></spine>
</package>
"""

    ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="{BOOK_ID}"/></head>
  <docTitle><text>{html.escape(BOOK_TITLE)}</text></docTitle>
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>{html.escape(h2)}</text></navLabel>
      <content src="chapter.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
"""

    container = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    with zipfile.ZipFile(OUT_EPUB, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/chapter.xhtml", chapter, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing {SRC}; run scripts/fetch_sample.sh first.")
    h2, h3, paragraphs = extract_chapter()
    text = f"# {h2}\n\n## {h3}\n\n" + "\n\n".join(paragraphs) + "\n"
    OUT_TXT.write_text(text, encoding="utf-8")
    build_epub(h2, h3, paragraphs)
    print(f"Wrote {OUT_TXT} ({len(text)} chars)")
    print(f"Wrote {OUT_EPUB}")


if __name__ == "__main__":
    main()
