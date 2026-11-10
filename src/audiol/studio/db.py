import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from audiol.studio.library import BookRecord

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT NOT NULL,
  language TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  cover_path TEXT,
  status TEXT NOT NULL,
  voice TEXT,
  engine TEXT,
  style TEXT,
  rate TEXT,
  duration_ms INTEGER,
  chapter_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  stage TEXT NOT NULL,
  completed_segments INTEGER NOT NULL DEFAULT 0,
  total_segments INTEGER NOT NULL DEFAULT 0,
  chapter_index INTEGER,
  chapter_title TEXT,
  current_text TEXT,
  message TEXT,
  error TEXT,
  options_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS book_state (
  book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
  position_ms INTEGER NOT NULL DEFAULT 0,
  chapter_index INTEGER NOT NULL DEFAULT 1,
  playback_rate REAL NOT NULL DEFAULT 1.0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  chapter_index INTEGER NOT NULL,
  position_ms INTEGER NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reading_state (
  book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
  chapter_index INTEGER NOT NULL DEFAULT 1,
  char_offset INTEGER NOT NULL DEFAULT 0,
  page_index INTEGER NOT NULL DEFAULT 0,
  page_count INTEGER,
  percent REAL NOT NULL DEFAULT 0,
  cfi TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reading_bookmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  chapter_index INTEGER NOT NULL,
  char_offset INTEGER NOT NULL DEFAULT 0,
  page_index INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS book_preferences (
  book_id TEXT PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
  reader_mode TEXT,
  reader_palette TEXT,
  reader_font TEXT,
  reader_size INTEGER,
  page_turn INTEGER,
  ambience_enabled INTEGER,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sound_assets (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  prompt TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT,
  seed INTEGER,
  duration_ms INTEGER NOT NULL,
  loopable INTEGER NOT NULL DEFAULT 0,
  sample_rate INTEGER NOT NULL,
  channels INTEGER NOT NULL,
  loudness_lufs REAL,
  license TEXT NOT NULL,
  attribution TEXT,
  source_url TEXT,
  checksum TEXT NOT NULL UNIQUE,
  approved INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_used_at TEXT,
  usage_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sound_assets_kind ON sound_assets(kind, approved);
CREATE INDEX IF NOT EXISTS idx_sound_assets_license ON sound_assets(license);
CREATE INDEX IF NOT EXISTS idx_sound_assets_checksum ON sound_assets(checksum);
CREATE INDEX IF NOT EXISTS idx_jobs_book_created ON jobs(book_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
CREATE INDEX IF NOT EXISTS idx_books_created ON books(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_books_duration ON books(duration_ms DESC);
CREATE INDEX IF NOT EXISTS idx_bookmarks_book_position
  ON bookmarks(book_id, position_ms, created_at);
CREATE INDEX IF NOT EXISTS idx_reading_bookmarks_book_position
  ON reading_bookmarks(book_id, chapter_index, char_offset, created_at);
"""

MIGRATION_2 = """
ALTER TABLE reading_state ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0;
"""

MIGRATIONS: list[tuple[int, str]] = [
    (1, SCHEMA_V1),
    (2, MIGRATION_2),
]
SCHEMA_VERSION = MIGRATIONS[-1][0]

SORT_SQL = {
    "recent": "b.created_at DESC",
    "title": "b.title COLLATE NOCASE ASC",
    "duration": "b.duration_ms DESC",
    "progress": ("(CAST(COALESCE(s.position_ms, 0) AS REAL) / NULLIF(b.duration_ms, 0)) DESC"),
}
BOOK_FIELDS = {
    "duration_ms",
    "chapter_count",
    "voice",
    "engine",
    "style",
    "rate",
    "cover_path",
}
JOB_FIELDS = {
    "status",
    "stage",
    "completed_segments",
    "total_segments",
    "chapter_index",
    "chapter_title",
    "current_text",
    "message",
    "error",
    "started_at",
    "finished_at",
}


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def migrate(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            target = SCHEMA_VERSION
            if current >= target:
                return
            if current > 0 and self.path.exists():
                self._backup_database(current)
            for version, script in MIGRATIONS:
                if version <= current:
                    continue
                try:
                    connection.executescript(
                        f"BEGIN IMMEDIATE;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;"
                    )
                except BaseException:
                    connection.rollback()
                    raise

    def _backup_database(self, version: int) -> Path:
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        target = self.path.with_name(f"{self.path.name}.backup-{stamp}-v{version}")
        source = sqlite3.connect(self.path)
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        return target

    def upsert_book(self, record: BookRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO books (
                    id, title, author, language, path, cover_path, status,
                    voice, engine, style, rate, duration_ms, chapter_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    author=excluded.author,
                    language=excluded.language,
                    path=excluded.path,
                    cover_path=excluded.cover_path,
                    status=excluded.status,
                    voice=excluded.voice,
                    engine=excluded.engine,
                    style=excluded.style,
                    rate=excluded.rate,
                    duration_ms=excluded.duration_ms,
                    chapter_count=excluded.chapter_count,
                    updated_at=excluded.updated_at
                """,
                (
                    record.id,
                    record.title,
                    record.author,
                    record.language,
                    str(record.path),
                    str(record.cover_path) if record.cover_path is not None else None,
                    record.status,
                    record.voice,
                    record.engine,
                    record.style,
                    record.rate,
                    record.duration_ms,
                    record.chapter_count,
                    record.created_at,
                    record.updated_at,
                ),
            )

    def reconcile(self, records: list[BookRecord]) -> None:
        for record in records:
            existing = self.get_book(record.id)
            if (
                existing is not None
                and existing["status"] in {"interrupted", "error"}
                and record.status in {"imported", "ready", "converting"}
            ):
                record = replace(
                    record,
                    status=existing["status"],
                    updated_at=existing["updated_at"],
                )
            self.upsert_book(record)
        self._mark_missing_books({record.id for record in records})

    def list_books(self, query: str, sort: str, limit: int, offset: int) -> tuple[list[dict], int]:
        if sort not in SORT_SQL:
            raise ValueError(f"Unknown sort: {sort}")
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        where = ""
        params: list[Any] = []
        if query:
            where = (
                "WHERE instr(lower(b.title), lower(?)) > 0 OR instr(lower(b.author), lower(?)) > 0"
            )
            params = [query, query]

        with self._connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM books b {where}", params).fetchone()[
                0
            ]
            rows = connection.execute(
                f"""
                SELECT b.*,
                       COALESCE(s.position_ms, 0) AS position_ms,
                       COALESCE(s.chapter_index, 1) AS chapter_index,
                       COALESCE(s.playback_rate, 1.0) AS playback_rate,
                       COALESCE(r.percent, 0) AS reading_progress,
                       r.chapter_index AS reading_chapter_index,
                       r.updated_at AS reading_updated_at
                FROM books b
                LEFT JOIN book_state s ON s.book_id = b.id
                LEFT JOIN reading_state r ON r.book_id = b.id
                {where}
                ORDER BY {SORT_SQL[sort]}
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return [dict(row) for row in rows], int(total)

    def get_book(self, book_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT b.*,
                       COALESCE(s.position_ms, 0) AS position_ms,
                       COALESCE(s.chapter_index, 1) AS chapter_index,
                       COALESCE(s.playback_rate, 1.0) AS playback_rate,
                       COALESCE(r.percent, 0) AS reading_progress,
                       r.chapter_index AS reading_chapter_index,
                       r.updated_at AS reading_updated_at
                FROM books b
                LEFT JOIN book_state s ON s.book_id = b.id
                LEFT JOIN reading_state r ON r.book_id = b.id
                WHERE b.id = ?
                """,
                (book_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def set_book_status(self, book_id: str, status: str, **fields: object) -> None:
        unknown = set(fields) - BOOK_FIELDS
        if unknown:
            raise ValueError(f"Unknown book fields: {sorted(unknown)}")
        assignments = ["status = ?"] + [f"{field} = ?" for field in fields]
        values = [status, *fields.values()]
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE books SET {', '.join(assignments)}, updated_at = ? WHERE id = ?",
                [*values, _now(), book_id],
            )
            if cursor.rowcount == 0:
                raise KeyError(book_id)

    def delete_book(self, book_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
            if cursor.rowcount == 0:
                raise KeyError(book_id)

    def create_job(self, job: dict) -> None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, book_id, status, stage, completed_segments,
                    total_segments, chapter_index, chapter_title, current_text,
                    message, error, options_json, created_at, updated_at,
                    started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["id"],
                    job["book_id"],
                    job["status"],
                    job["stage"],
                    int(job.get("completed_segments", 0)),
                    int(job.get("total_segments", 0)),
                    job.get("chapter_index"),
                    job.get("chapter_title"),
                    job.get("current_text"),
                    job.get("message"),
                    job.get("error"),
                    job.get("options_json", "{}"),
                    job.get("created_at", now),
                    now,
                    job.get("started_at"),
                    job.get("finished_at"),
                ),
            )

    def update_job(self, job_id: str, **fields: object) -> None:
        unknown = set(fields) - JOB_FIELDS
        if unknown:
            raise ValueError(f"Unknown job fields: {sorted(unknown)}")
        if not fields:
            return
        assignments = [f"{field} = ?" for field in fields]
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE jobs SET {', '.join(assignments)}, updated_at = ? WHERE id = ?",
                [*fields.values(), _now(), job_id],
            )
            if cursor.rowcount == 0:
                raise KeyError(job_id)

    def get_job(self, job_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _job_dict(row) if row is not None else None

    def get_latest_job(self, book_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM jobs
                WHERE book_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (book_id,),
            ).fetchone()
        return _job_dict(row) if row is not None else None

    def list_active_jobs(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE status IN ('queued', 'running', 'cancelling')
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [_job_dict(row) for row in rows]

    def get_book_state(self, book_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM book_state WHERE book_id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def set_book_state(
        self, book_id: str, position_ms: int, chapter_index: int, playback_rate: float
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO book_state (
                    book_id, position_ms, chapter_index, playback_rate, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(book_id) DO UPDATE SET
                    position_ms=excluded.position_ms,
                    chapter_index=excluded.chapter_index,
                    playback_rate=excluded.playback_rate,
                    updated_at=excluded.updated_at
                """,
                (book_id, position_ms, chapter_index, playback_rate, _now()),
            )

    def list_bookmarks(self, book_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM bookmarks
                WHERE book_id = ?
                ORDER BY position_ms ASC, created_at ASC
                """,
                (book_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_bookmark(
        self,
        book_id: str,
        chapter_index: int,
        position_ms: int,
        note: str | None,
    ) -> dict:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO bookmarks (
                    book_id, chapter_index, position_ms, note, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (book_id, chapter_index, position_ms, note, now),
            )
            bookmark_id = int(cursor.lastrowid or 0)
            row = connection.execute(
                "SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,)
            ).fetchone()
        if row is None:
            raise KeyError(bookmark_id)
        return dict(row)

    def delete_bookmark(self, book_id: str, bookmark_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM bookmarks WHERE book_id = ? AND id = ?",
                (book_id, bookmark_id),
            )
        return cursor.rowcount > 0

    def get_reading_state(self, book_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reading_state WHERE book_id = ?", (book_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def set_reading_state(
        self,
        book_id: str,
        chapter_index: int,
        char_offset: int,
        page_index: int,
        page_count: int | None,
        percent: float,
        cfi: str | None,
        sequence: int | None = None,
    ) -> dict:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reading_state (
                    book_id, chapter_index, char_offset, page_index,
                    page_count, percent, cfi, sequence, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    COALESCE(?, (SELECT COALESCE(MAX(sequence), 0) + 1
                                  FROM reading_state WHERE book_id = ?)),
                    ?
                )
                ON CONFLICT(book_id) DO UPDATE SET
                    chapter_index=excluded.chapter_index,
                    char_offset=excluded.char_offset,
                    page_index=excluded.page_index,
                    page_count=excluded.page_count,
                    percent=excluded.percent,
                    cfi=excluded.cfi,
                    sequence=excluded.sequence,
                    updated_at=excluded.updated_at
                WHERE excluded.sequence > reading_state.sequence
                """,
                (
                    book_id,
                    chapter_index,
                    char_offset,
                    page_index,
                    page_count,
                    percent,
                    cfi,
                    sequence,
                    book_id,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM reading_state WHERE book_id = ?", (book_id,)
            ).fetchone()
        if row is None:
            raise KeyError(book_id)
        return dict(row)

    def list_reading_bookmarks(self, book_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM reading_bookmarks
                WHERE book_id = ?
                ORDER BY chapter_index ASC, char_offset ASC, created_at ASC
                """,
                (book_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_reading_bookmark(
        self,
        book_id: str,
        chapter_index: int,
        char_offset: int,
        page_index: int,
        note: str | None,
    ) -> dict:
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reading_bookmarks (
                    book_id, chapter_index, char_offset, page_index, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (book_id, chapter_index, char_offset, page_index, note, now),
            )
            bookmark_id = int(cursor.lastrowid or 0)
            row = connection.execute(
                "SELECT * FROM reading_bookmarks WHERE id = ?", (bookmark_id,)
            ).fetchone()
        if row is None:
            raise KeyError(bookmark_id)
        return dict(row)

    def delete_reading_bookmark(self, book_id: str, bookmark_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM reading_bookmarks WHERE book_id = ? AND id = ?",
                (book_id, bookmark_id),
            )
        return cursor.rowcount > 0

    def get_book_preferences(self, book_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM book_preferences WHERE book_id = ?", (book_id,)
            ).fetchone()
        if row is None:
            return None
        preferences = dict(row)
        for key in ("page_turn", "ambience_enabled"):
            value = preferences.get(key)
            if value is not None:
                preferences[key] = bool(value)
        return preferences

    def set_book_preferences(self, book_id: str, preferences: dict[str, object]) -> dict:
        allowed = {
            "reader_mode",
            "reader_palette",
            "reader_font",
            "reader_size",
            "page_turn",
            "ambience_enabled",
        }
        unknown = set(preferences) - allowed
        if unknown:
            raise ValueError(f"Unknown book preferences: {sorted(unknown)}")
        values = dict(preferences)
        for key in ("page_turn", "ambience_enabled"):
            if key in values and values[key] is not None:
                values[key] = int(bool(values[key]))
        now = _now()
        columns = ["book_id", *values, "updated_at"]
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(
            [f"{key}=excluded.{key}" for key in values] + ["updated_at=excluded.updated_at"]
        )
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO book_preferences ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(book_id) DO UPDATE SET {assignments}
                """,
                (book_id, *values.values(), now),
            )
            row = connection.execute(
                "SELECT * FROM book_preferences WHERE book_id = ?", (book_id,)
            ).fetchone()
        if row is None:
            raise KeyError(book_id)
        result = dict(row)
        for key in ("page_turn", "ambience_enabled"):
            value = result.get(key)
            if value is not None:
                result[key] = bool(value)
        return result

    def get_settings(self) -> dict[str, object]:
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        settings: dict[str, object] = {}
        for row in rows:
            try:
                settings[row["key"]] = json.loads(row["value"])
            except ValueError:
                settings[row["key"]] = row["value"]
        return settings

    def set_setting(self, key: str, value: object) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, json.dumps(value)),
            )

    def upsert_sound_asset(self, asset: dict) -> dict:
        created = str(asset.get("created_at") or _now())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO sound_assets (
                    id, kind, prompt, tags_json, provider, model, seed, duration_ms,
                    loopable, sample_rate, channels, loudness_lufs, license,
                    attribution, source_url, checksum, approved, created_at,
                    last_used_at, usage_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset["id"],
                    asset["kind"],
                    asset["prompt"],
                    json.dumps(asset.get("tags", []), ensure_ascii=False),
                    asset["provider"],
                    asset.get("model"),
                    asset.get("seed"),
                    asset["duration_ms"],
                    1 if asset.get("loopable") else 0,
                    asset["sample_rate"],
                    asset["channels"],
                    asset.get("loudness_lufs"),
                    asset["license"],
                    asset.get("attribution"),
                    asset.get("source_url"),
                    asset["checksum"],
                    1 if asset.get("approved") else 0,
                    created,
                    asset.get("last_used_at"),
                    int(asset.get("usage_count", 0)),
                ),
            )
            row = connection.execute(
                "SELECT * FROM sound_assets WHERE checksum = ?", (asset["checksum"],)
            ).fetchone()
        if row is None:
            raise ValueError(f"Could not store sound asset {asset['id']}")
        return _sound_asset_row(row)

    def get_sound_asset(self, asset_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sound_assets WHERE id = ?", (asset_id,)
            ).fetchone()
        return _sound_asset_row(row) if row is not None else None

    def get_sound_asset_by_checksum(self, checksum: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sound_assets WHERE checksum = ?", (checksum,)
            ).fetchone()
        return _sound_asset_row(row) if row is not None else None

    def list_sound_assets(
        self,
        query: str = "",
        kind: str | None = None,
        license_name: str | None = None,
        approved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            clauses.append(
                "(instr(lower(prompt), lower(?)) > 0 OR instr(lower(tags_json), lower(?)) > 0)"
            )
            params.extend([query, query])
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if license_name:
            clauses.append("license = ?")
            params.append(license_name)
        if approved is not None:
            clauses.append("approved = ?")
            params.append(1 if approved else 0)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM sound_assets {where}", params
            ).fetchone()[0]
            rows = connection.execute(
                f"""
                SELECT * FROM sound_assets
                {where}
                ORDER BY usage_count DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return [_sound_asset_row(row) for row in rows], int(total)

    def set_sound_asset_approved(self, asset_id: str, approved: bool) -> dict:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE sound_assets SET approved = ? WHERE id = ?",
                (1 if approved else 0, asset_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(asset_id)
            row = connection.execute(
                "SELECT * FROM sound_assets WHERE id = ?", (asset_id,)
            ).fetchone()
        if row is None:
            raise KeyError(asset_id)
        return _sound_asset_row(row)

    def record_sound_asset_use(self, asset_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE sound_assets
                SET usage_count = usage_count + 1, last_used_at = ?
                WHERE id = ?
                """,
                (_now(), asset_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(asset_id)

    def record_sound_asset_uses(self, asset_ids: list[str]) -> None:
        if not asset_ids:
            return
        now = _now()
        with self._connect() as connection:
            connection.executemany(
                """
                UPDATE sound_assets
                SET usage_count = usage_count + 1, last_used_at = ?
                WHERE id = ?
                """,
                [(now, asset_id) for asset_id in dict.fromkeys(asset_ids)],
            )

    def delete_sound_asset(self, asset_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM sound_assets WHERE id = ?", (asset_id,))
            if cursor.rowcount == 0:
                raise KeyError(asset_id)

    def mark_interrupted(self) -> None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'interrupted', updated_at = ?, finished_at = ?
                WHERE status IN ('queued', 'running', 'cancelling')
                """,
                (now, now),
            )
            connection.execute(
                """
                UPDATE books
                SET status = 'interrupted', updated_at = ?
                WHERE status = 'converting'
                """,
                (now,),
            )

    def _mark_missing_books(self, existing_ids: set[str]) -> None:
        with self._connect() as connection:
            if existing_ids:
                placeholders = ", ".join("?" for _ in existing_ids)
                connection.execute(
                    f"""
                    UPDATE books
                    SET status = 'missing', updated_at = ?
                    WHERE id NOT IN ({placeholders})
                    """,
                    [_now(), *existing_ids],
                )
            else:
                connection.execute(
                    "UPDATE books SET status = 'missing', updated_at = ?",
                    (_now(),),
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()


def _sound_asset_row(row: sqlite3.Row) -> dict:
    result = dict(row)
    try:
        result["tags"] = json.loads(result.pop("tags_json", "[]"))
    except ValueError:
        result["tags"] = []
    result["loopable"] = bool(result.get("loopable"))
    result["approved"] = bool(result.get("approved"))
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _job_dict(row: sqlite3.Row) -> dict:
    job = dict(row)
    options_json = job.pop("options_json", "{}")
    try:
        job["options"] = json.loads(options_json)
    except ValueError:
        job["options"] = {}
    return job
