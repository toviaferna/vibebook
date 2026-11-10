import json
from pathlib import Path


def _book_dir(client, book_id: str) -> Path:
    return client.app.state.library.get(book_id).path


def _make_stale(client, book_id: str) -> None:
    path = _book_dir(client, book_id) / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.pop("segmentation_version", None)
    manifest["chapters"][0]["segments"][0]["text"] = "Viejo texto roto"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def test_resegment_plan_for_a_current_import(client, imported):
    response = client.get(f"/api/books/{imported['id']}/resegment")

    assert response.status_code == 200
    plan = response.json()
    assert plan["can_repair"] is True
    assert plan["needs_repair"] is False
    assert plan["current_version"] == plan["target_version"]
    assert plan["changed_segments"] == 0


def test_resegment_plan_detects_an_old_manifest(client, imported):
    _make_stale(client, imported["id"])

    response = client.get(f"/api/books/{imported['id']}/resegment")

    assert response.status_code == 200
    plan = response.json()
    assert plan["needs_repair"] is True
    assert plan["current_version"] is None
    assert plan["changed_segments"] == 1
    assert plan["changed_chapters"] == [1]
    assert plan["chapters"][0]["changed"] is True


def test_resegment_dry_run_does_not_touch_the_manifest(client, imported):
    _make_stale(client, imported["id"])
    path = _book_dir(client, imported["id"]) / "manifest.json"
    before = path.read_text(encoding="utf-8")

    response = client.post(
        f"/api/books/{imported['id']}/resegment",
        json={"dry_run": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["changed"] is True
    assert payload["dry_run"] is True
    assert path.read_text(encoding="utf-8") == before


def test_resegment_applies_metadata_repair(client, imported):
    _make_stale(client, imported["id"])

    response = client.post(f"/api/books/{imported['id']}/resegment", json={})

    assert response.status_code == 200
    assert response.json()["changed"] is True
    manifest = json.loads(
        (_book_dir(client, imported["id"]) / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["segmentation_version"] == 2
    assert manifest["chapters"][0]["segments"][0]["text"] != "Viejo texto roto"
    assert client.get(f"/api/books/{imported['id']}").status_code == 200


def test_resegment_is_blocked_by_another_operation(client, imported):
    lease = client.app.state.activity.reserve(imported["id"], "convert")

    response = client.post(f"/api/books/{imported['id']}/resegment", json={})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "book_busy"
    client.app.state.activity.release(lease)


def test_resegment_refuses_a_book_that_is_not_ready(client, imported):
    path = _book_dir(client, imported["id"]) / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "converting"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    response = client.post(f"/api/books/{imported['id']}/resegment", json={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "resegment_failed"


def test_resegment_lists_no_backups_for_an_imported_book(client, imported):
    response = client.get(f"/api/books/{imported['id']}/resegment/backups")

    assert response.status_code == 200
    assert response.json() == []


def test_resegment_restore_rejects_a_bad_backup_id(client, imported):
    response = client.post(
        f"/api/books/{imported['id']}/resegment/restore",
        json={"backup_id": "../escape"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "resegment_failed"


def test_resegment_unknown_book(client):
    assert client.get("/api/books/nope/resegment").status_code == 404
    assert client.post("/api/books/nope/resegment", json={}).status_code == 404
