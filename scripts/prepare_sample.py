"""Extract the test chapter and build bake-off EPUBs.

This is a bake-off utility, not the product cleaner. It keeps the chapter text
and minimal one-chapter EPUBs so the engines can process a short sample fast.
"""

from __future__ import annotations

import html
import re
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "samples" / "lazarillo.epub"
CHAPTER = "OEBPS/9106994058927650652_320-h-2.htm.html"
OUT_TXT = ROOT / "samples" / "tratado_primero.txt"
OUT_EPUB = ROOT / "samples" / "tratado_primero.epub"
OUT_EXCERPT_TXT = ROOT / "samples" / "excerpt.txt"
OUT_EXCERPT_EPUB = ROOT / "samples" / "excerpt.epub"
EXCERPT_TARGET = 3300


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
    paragraphs = [clean_fragment(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", raw, re.S)]
    paragraphs = [p for p in paragraphs if p]

    deduped: list[str] = []
    for paragraph in paragraphs:
        if not deduped or paragraph != deduped[-1]:
            deduped.append(paragraph)
    return h2, h3, deduped


def build_epub(
    out_path: Path,
    title: str,
    subtitle: str,
    paragraphs: list[str],
    book_id: str | None = None,
) -> None:
    book_id = book_id or f"urn:uuid:{uuid.uuid4()}"
    body = [f"<h1>{html.escape(title)}</h1>", f"<h2>{html.escape(subtitle)}</h2>"]
    body.extend(f"<p>{html.escape(p)}</p>" for p in paragraphs)

    chapter = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es">
<head><title>{html.escape(title)}</title><meta charset="utf-8"/></head>
<body>
{chr(10).join(body)}
</body>
</html>
"""

    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{html.escape(title)}</dc:title>
    <dc:language>es</dc:language>
    <dc:identifier id="bookid">{book_id}</dc:identifier>
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
  <head><meta name="dtb:uid" content="{book_id}"/></head>
  <docTitle><text>{html.escape(title)}</text></docTitle>
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>{html.escape(title)}</text></navLabel>
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

    with zipfile.ZipFile(out_path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/chapter.xhtml", chapter, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing {SRC}; run scripts/fetch_sample.sh first.")

    h2, h3, paragraphs = extract_chapter()
    full_text = f"# {h2}\n\n## {h3}\n\n" + "\n\n".join(paragraphs) + "\n"
    OUT_TXT.write_text(full_text, encoding="utf-8")
    build_epub(OUT_EPUB, h2, h3, paragraphs, "audiol-sample-lazarillo-tratado-1")

    excerpt: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if size >= EXCERPT_TARGET and excerpt:
            break
        excerpt.append(paragraph)
        size += len(paragraph) + 2

    excerpt_text = f"{h2}\n\n{h3}\n\n" + "\n\n".join(excerpt) + "\n"
    OUT_EXCERPT_TXT.write_text(excerpt_text, encoding="utf-8")
    build_epub(OUT_EXCERPT_EPUB, h2, h3, excerpt, "audiol-sample-lazarillo-excerpt")

    print(f"Wrote {OUT_TXT} ({len(full_text)} chars)")
    print(f"Wrote {OUT_EPUB}")
    print(f"Wrote {OUT_EXCERPT_TXT} ({len(excerpt_text)} chars)")
    print(f"Wrote {OUT_EXCERPT_EPUB}")


if __name__ == "__main__":
    main()
