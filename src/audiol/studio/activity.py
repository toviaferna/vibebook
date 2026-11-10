from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4


class BookBusy(RuntimeError):
    def __init__(self, book_id: str, kind: str) -> None:
        super().__init__(f"Book {book_id} is busy with {kind}")
        self.book_id = book_id
        self.kind = kind


@dataclass(frozen=True)
class BookLease:
    book_id: str
    kind: str
    token: str


class BookActivity:
    def __init__(self) -> None:
        self._leases: dict[str, BookLease] = {}
        self._lock = threading.Lock()

    def reserve(self, book_id: str, kind: str) -> BookLease:
        with self._lock:
            current = self._leases.get(book_id)
            if current is not None:
                raise BookBusy(book_id, current.kind)
            lease = BookLease(book_id=book_id, kind=kind, token=uuid4().hex)
            self._leases[book_id] = lease
            return lease

    def release(self, lease: BookLease) -> None:
        with self._lock:
            current = self._leases.get(lease.book_id)
            if current is not None and current.token == lease.token:
                del self._leases[lease.book_id]

    def active(self, book_id: str) -> str | None:
        with self._lock:
            lease = self._leases.get(book_id)
            return lease.kind if lease is not None else None

    @contextmanager
    def lease(self, book_id: str, kind: str):
        lease = self.reserve(book_id, kind)
        try:
            yield lease
        finally:
            self.release(lease)
