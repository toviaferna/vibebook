from pathlib import Path


class UnsafePathError(ValueError):
    pass


def safe_book_path(book_dir: Path, relative: str) -> Path:
    if not relative or "\x00" in relative:
        raise UnsafePathError(f"Invalid relative path: {relative!r}")
    root = book_dir.resolve()
    candidate = (book_dir / relative).resolve()
    if candidate == root or not candidate.is_relative_to(root):
        raise UnsafePathError(f"Path escapes the book: {relative}")
    return candidate
