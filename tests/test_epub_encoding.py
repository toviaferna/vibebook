import zipfile
from pathlib import Path

from ebooklib import epub

from audiol.ingest.epub import _decode_document, read_epub

TEXT = "Capítulo ñandú, acción."


def _rewrite_document(path: Path, content: bytes) -> None:
    with zipfile.ZipFile(path) as source:
        items = [(info, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in items:
            if info.filename.endswith(".xhtml") and "nav" not in info.filename:
                data = content
            target.writestr(info, data)


def _write_epub(path: Path) -> None:
    book = epub.EpubBook()
    book.set_identifier("encoding-test")
    book.set_title("Codificación")
    book.set_language("es")
    chapter = epub.EpubHtml(title="Capítulo 1", file_name="cap1.xhtml", lang="es")
    chapter.content = f"<html><body><p>{TEXT}</p></body></html>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    epub.write_epub(str(path), book)


def test_decode_document_prefers_utf8_without_declaration():
    content = f"<html><body><p>{TEXT}</p></body></html>".encode()

    assert _decode_document(content) == f"<html><body><p>{TEXT}</p></body></html>"


def test_decode_document_falls_back_to_cp1252():
    content = f"<html><body><p>{TEXT}</p></body></html>".encode("cp1252")

    assert TEXT in _decode_document(content)


def test_decode_document_trusts_utf8_even_with_latin1_meta():
    content = (
        f"<html><head><meta charset='iso-8859-1'></head><body><p>{TEXT}</p></body></html>".encode()
    )

    assert TEXT in _decode_document(content)


def test_read_epub_preserves_cp1252_accents(tmp_path: Path):
    path = tmp_path / "cp1252.epub"
    _write_epub(path)
    _rewrite_document(
        path,
        f"<html><body><h1>Capítulo 1</h1><p>{TEXT}</p></body></html>".encode("cp1252"),
    )

    book = read_epub(path)
    texts = [segment.text for chapter in book.chapters for segment in chapter.segments]

    assert any(TEXT in text for text in texts), texts


def test_read_epub_preserves_utf8_accents(tmp_path: Path):
    path = tmp_path / "utf8.epub"
    _write_epub(path)
    _rewrite_document(
        path,
        f"<html><body><h1>Capítulo 1</h1><p>{TEXT}</p></body></html>".encode(),
    )

    book = read_epub(path)
    texts = [segment.text for chapter in book.chapters for segment in chapter.segments]

    assert any(TEXT in text for text in texts)
