import sqlite3
from pathlib import Path

import pytest

import audiol.studio.db as db_module
from audiol.studio.db import Database
from audiol.studio.library import BookRecord


def make_record(
    book_id: str,
    title: str,
    *,
    path: Path | None = None,
    status: str = "imported",
    duration_ms: int | None = None,
) -> BookRecord:
    return BookRecord(
        id=book_id,
        title=title,
        author="Autora",
        language="es",
        path=path or Path("C:/books") / book_id,
        cover_path=None,
        status=status,
        voice="es-MX-JorgeNeural",
        engine="edge",
        style="neutral",
        rate="-10%",
        chapter_count=2,
        duration_ms=duration_ms,
        created_at="2026-11-07T10:00:00+00:00",
        updated_at="2026-11-07T10:00:00+00:00",
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "library" / ".vibebook.db")
    database.migrate()
    return database


def test_migrate_is_idempotent(db: Database):
    db.migrate()
    db.migrate()

    with sqlite3.connect(db.path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == db_module.SCHEMA_VERSION


def test_migration_2_adds_sequence_to_reading_state(db: Database):
    with sqlite3.connect(db.path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(reading_state)")}

    assert "sequence" in columns


def test_failed_migration_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "db.sqlite"
    database = Database(path)
    monkeypatch.setattr(db_module, "MIGRATIONS", db_module.MIGRATIONS[:1])
    database.migrate()

    monkeypatch.setattr(
        db_module,
        "MIGRATIONS",
        [
            *db_module.MIGRATIONS[:1],
            (2, "CREATE TABLE broken (id INTEGER); INSERT INTO missing VALUES (1);"),
        ],
    )
    with pytest.raises(sqlite3.OperationalError):
        database.migrate()

    with sqlite3.connect(path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert version == 1
    assert "broken" not in tables


def test_migration_backs_up_the_database_with_wal_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "db.sqlite"
    database = Database(path)
    monkeypatch.setattr(db_module, "MIGRATIONS", db_module.MIGRATIONS[:1])
    database.migrate()
    database.upsert_book(make_record("libro-1234", "Libro"))
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("INSERT INTO settings (key, value) VALUES ('clave', 'valor')")
        connection.commit()

    monkeypatch.setattr(
        db_module, "MIGRATIONS", [(1, db_module.SCHEMA_V1), (2, db_module.MIGRATION_2)]
    )
    database.migrate()

    backups = list(tmp_path.glob("db.sqlite.backup-*"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert (
            connection.execute("SELECT value FROM settings WHERE key = 'clave'").fetchone()[0]
            == "valor"
        )
        assert (
            connection.execute("SELECT title FROM books WHERE id = 'libro-1234'").fetchone()[0]
            == "Libro"
        )


def test_upsert_and_get_book(db: Database):
    record = make_record("libro-1234", "Libro")
    db.upsert_book(record)

    book = db.get_book("libro-1234")

    assert book is not None
    assert book["title"] == "Libro"
    assert book["status"] == "imported"
    assert book["position_ms"] == 0
    assert book["chapter_index"] == 1

    db.upsert_book(make_record("libro-1234", "Libro actualizado", status="ready"))
    updated = db.get_book("libro-1234")
    assert updated["title"] == "Libro actualizado"
    assert updated["status"] == "ready"


def test_list_books_searches_sorts_and_paginates(db: Database):
    db.upsert_book(make_record("a", "Zeta", duration_ms=300))
    db.upsert_book(make_record("b", "Alfa", duration_ms=100))
    db.upsert_book(make_record("c", "Beta", duration_ms=200))

    items, total = db.list_books("", "title", 2, 0)
    assert total == 3
    assert [item["title"] for item in items] == ["Alfa", "Beta"]

    items, total = db.list_books("be", "recent", 10, 0)
    assert total == 1
    assert items[0]["title"] == "Beta"

    items, _ = db.list_books("", "duration", 10, 0)
    assert [item["title"] for item in items] == ["Zeta", "Beta", "Alfa"]


def test_list_books_rejects_unknown_sort(db: Database):
    with pytest.raises(ValueError):
        db.list_books("", "hacker", 10, 0)


def test_reconcile_marks_missing(db: Database):
    db.upsert_book(make_record("a", "A"))
    db.upsert_book(make_record("b", "B"))

    db.reconcile([make_record("a", "A")])

    assert db.get_book("a")["status"] == "imported"
    assert db.get_book("b")["status"] == "missing"


def test_job_lifecycle(db: Database):
    db.upsert_book(make_record("a", "A"))
    db.create_job(
        {
            "id": "job_1",
            "book_id": "a",
            "status": "queued",
            "stage": "preparing",
            "options_json": (
                '{"voice":"v","engine":"edge","style":"neutral","rate":"-10%","force":false}'
            ),
        }
    )

    job = db.get_job("job_1")
    assert job is not None
    assert job["status"] == "queued"
    assert job["options"]["voice"] == "v"

    db.update_job(
        "job_1",
        status="running",
        stage="synthesizing",
        completed_segments=3,
        total_segments=10,
        current_text="Hola",
    )
    updated = db.get_job("job_1")
    assert updated["status"] == "running"
    assert updated["completed_segments"] == 3
    assert [job["id"] for job in db.list_active_jobs()] == ["job_1"]


def test_book_state_roundtrip(db: Database):
    db.upsert_book(make_record("a", "A"))

    assert db.get_book_state("a") is None
    db.set_book_state("a", 1234, 2, 1.25)
    state = db.get_book_state("a")
    assert state["position_ms"] == 1234
    assert state["chapter_index"] == 2
    assert state["playback_rate"] == 1.25


def test_settings_json_roundtrip(db: Database):
    db.set_setting("reader_theme", "night")
    db.set_setting("auto_scroll", False)
    db.set_setting("skip_seconds", 20)

    settings = db.get_settings()

    assert settings == {
        "reader_theme": "night",
        "auto_scroll": False,
        "skip_seconds": 20,
    }


def test_cascade_delete(db: Database):
    db.upsert_book(make_record("a", "A"))
    db.set_book_state("a", 1, 1, 1.0)
    db.create_job(
        {
            "id": "job_1",
            "book_id": "a",
            "status": "completed",
            "stage": "done",
            "options_json": "{}",
        }
    )

    db.delete_book("a")

    assert db.get_book("a") is None
    assert db.get_job("job_1") is None
    assert db.get_book_state("a") is None


def test_set_book_status_rejects_unknown_field(db: Database):
    db.upsert_book(make_record("a", "A"))

    with pytest.raises(ValueError):
        db.set_book_status("a", "ready", password="x")


def test_reconcile_preserves_interrupted_and_error_status(db: Database):
    db.upsert_book(make_record("a", "A", status="interrupted"))
    db.upsert_book(make_record("b", "B", status="error"))

    db.reconcile([make_record("a", "A"), make_record("b", "B")])

    assert db.get_book("a")["status"] == "interrupted"
    assert db.get_book("b")["status"] == "error"


def test_mark_interrupted(db: Database):
    db.upsert_book(make_record("a", "A", status="converting"))
    db.create_job(
        {
            "id": "job_1",
            "book_id": "a",
            "status": "running",
            "stage": "synthesizing",
            "options_json": "{}",
        }
    )

    db.mark_interrupted()

    assert db.get_job("job_1")["status"] == "interrupted"
    assert db.get_book("a")["status"] == "interrupted"
