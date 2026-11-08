import time

from audiol.studio import ambience_jobs


def _asset(db):
    return db.upsert_sound_asset(
        {
            "id": "bed-1",
            "kind": "ambience",
            "prompt": "rain bed",
            "tags": ["rain"],
            "provider": "import",
            "model": None,
            "seed": None,
            "duration_ms": 1_000,
            "loopable": True,
            "sample_rate": 48_000,
            "channels": 1,
            "loudness_lufs": None,
            "license": "CC0-1.0",
            "attribution": None,
            "source_url": None,
            "checksum": "a" * 64,
            "approved": True,
            "created_at": "2026-11-08T00:00:00+00:00",
            "last_used_at": None,
            "usage_count": 0,
        }
    )


def _put_plan(client, book_id):
    return client.put(
        f"/api/books/{book_id}/ambience",
        json={
            "settings": {"enabled": True, "master_gain_db": -18, "ducking_db": -12},
            "plan": {
                "version": 1,
                "chapters": [
                    {
                        "chapter_index": 1,
                        "bed": {
                            "asset_id": "bed-1",
                            "kind": "ambience",
                            "start_ms": 0,
                            "end_ms": None,
                            "loop": True,
                            "gain_db": -24,
                            "fade_in_ms": 1500,
                            "fade_out_ms": 2000,
                            "confidence": 0.8,
                            "reason": "lluvia",
                        },
                        "effects": [],
                    }
                ],
            },
        },
    )


def test_render_ambience_creates_job_and_audio(client, imported, monkeypatch):
    _asset(client.app.state.db)
    assert _put_plan(client, imported["id"]).status_code == 200

    def fake_render(book_dir, plan, settings, library, progress=None, **kwargs):
        output = book_dir / "audio" / "ambientado.m4b"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake m4b")
        if progress is not None:
            progress(1, 1, "Uno")
        return output

    monkeypatch.setattr(ambience_jobs, "render_ambient_book", fake_render)

    started = client.post(f"/api/books/{imported['id']}/ambience/render")
    assert started.status_code == 202
    job_id = started.json()["job_id"]

    status = "queued"
    for _ in range(50):
        job = client.get(f"/api/jobs/{job_id}").json()
        status = job["status"]
        if status in {"completed", "failed"}:
            break
        time.sleep(0.02)

    assert status == "completed"
    audio = client.get(f"/api/books/{imported['id']}/ambience/audio")
    assert audio.status_code == 200
    assert audio.content == b"fake m4b"


def test_render_rejects_empty_plan(client, imported):
    response = client.post(f"/api/books/{imported['id']}/ambience/render")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_ambience"
