from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

STAGING_DIR = ".staging"
BACKUP_DIR = ".backup"
STATE_FILE = "state.json"
META_FILE = "meta.json"
PREVIOUS_MANIFEST = "manifest.previous.json"


def new_staging_dir(out_dir: Path, job_id: str) -> Path:
    staging = out_dir / STAGING_DIR / job_id
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "chapters").mkdir(parents=True)
    (staging / "timings").mkdir(parents=True)
    (staging / "m4b").mkdir(parents=True)
    previous = out_dir / "manifest.json"
    if previous.is_file():
        shutil.copy2(previous, staging / PREVIOUS_MANIFEST)
    _write_state(staging, "staging")
    return staging


def backup_book_state(out_dir: Path, job_id: str) -> Path:
    backup = out_dir / BACKUP_DIR / job_id
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir(parents=True)
    had_manifest = (out_dir / "manifest.json").is_file()
    _write_json(backup / META_FILE, {"had_manifest": had_manifest})
    if had_manifest:
        shutil.copy2(out_dir / "manifest.json", backup / "manifest.json")
    _copy_tree(out_dir / "audio" / "chapters", backup / "chapters")
    _copy_tree(out_dir / "timings", backup / "timings")
    for m4b in out_dir.glob("*.m4b"):
        if m4b.is_file():
            shutil.copy2(m4b, backup / m4b.name)
    return backup


def commit_staged_book(staging: Path, out_dir: Path, backup: Path) -> None:
    _write_state(staging, "committing")
    try:
        _merge_tree(staging / "chapters", out_dir / "audio" / "chapters")
        _merge_tree(staging / "timings", out_dir / "timings")
        for m4b in (staging / "m4b").glob("*"):
            if m4b.is_file():
                _replace_with_retry(m4b, out_dir / m4b.name)
        manifest = staging / "manifest.json"
        if not manifest.is_file():
            raise RuntimeError("Staged conversion has no manifest")
        _replace_with_retry(manifest, out_dir / "manifest.json")
    except BaseException:
        restore_book_state(backup, out_dir)
        raise
    _write_state(staging, "committed")


def restore_book_state(backup: Path, out_dir: Path) -> None:
    meta = _read_json(backup / META_FILE)
    had_manifest = bool(meta.get("had_manifest"))
    manifest = backup / "manifest.json"
    if had_manifest and manifest.is_file():
        _replace_with_retry(manifest, out_dir / "manifest.json")
    elif not had_manifest:
        (out_dir / "manifest.json").unlink(missing_ok=True)

    _restore_tree(backup / "chapters", out_dir / "audio" / "chapters", had_manifest)
    _restore_tree(backup / "timings", out_dir / "timings", had_manifest)

    backup_m4b = {path.name for path in backup.glob("*.m4b") if path.is_file()}
    for m4b in out_dir.glob("*.m4b"):
        if m4b.name not in backup_m4b:
            m4b.unlink(missing_ok=True)
    for m4b in backup.glob("*.m4b"):
        if m4b.is_file():
            _replace_with_retry(m4b, out_dir / m4b.name)


def cleanup_staging(out_dir: Path) -> None:
    staging_root = out_dir / STAGING_DIR
    backup_root = out_dir / BACKUP_DIR
    if staging_root.is_dir():
        shutil.rmtree(staging_root, ignore_errors=True)
    if backup_root.is_dir():
        shutil.rmtree(backup_root, ignore_errors=True)


def prune_book_state(out_dir: Path, manifest: dict[str, Any]) -> None:
    chapters = manifest.get("chapters", [])
    if not isinstance(chapters, list):
        return
    audio_names = {
        Path(str(chapter.get("audio"))).name
        for chapter in chapters
        if isinstance(chapter, dict) and isinstance(chapter.get("audio"), str)
    }
    timing_names = {
        Path(str(chapter.get("timing"))).name
        for chapter in chapters
        if isinstance(chapter, dict) and isinstance(chapter.get("timing"), str)
    }
    chapters_dir = out_dir / "audio" / "chapters"
    if chapters_dir.is_dir():
        for path in chapters_dir.glob("*.mp3"):
            if path.name not in audio_names:
                path.unlink(missing_ok=True)
    timings_dir = out_dir / "timings"
    if timings_dir.is_dir():
        for path in timings_dir.glob("chapter_*.json"):
            if path.name not in timing_names:
                path.unlink(missing_ok=True)
    keep_m4b = manifest.get("m4b")
    keep_name = Path(str(keep_m4b)).name if isinstance(keep_m4b, str) else None
    for m4b in out_dir.glob("*.m4b"):
        if m4b.name != keep_name:
            m4b.unlink(missing_ok=True)


def recover_incomplete_commit(out_dir: Path) -> None:
    staging_root = out_dir / STAGING_DIR
    if not staging_root.is_dir():
        return
    for staging in sorted(staging_root.iterdir()):
        if not staging.is_dir():
            continue
        state = _read_json(staging / STATE_FILE).get("state")
        if state == "committing":
            backup = out_dir / BACKUP_DIR / staging.name
            if backup.is_dir():
                restore_book_state(backup, out_dir)
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(out_dir / BACKUP_DIR / staging.name, ignore_errors=True)


def _merge_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    files = [path for path in source.iterdir() if path.is_file()]
    if not files:
        return
    target.mkdir(parents=True, exist_ok=True)
    for path in files:
        _replace_with_retry(path, target / path.name)


def _restore_tree(source: Path, target: Path, had_manifest: bool) -> None:
    expected = (
        {path.name for path in source.iterdir() if path.is_file()} if source.is_dir() else set()
    )
    if target.is_dir():
        for path in target.iterdir():
            if path.is_file() and path.name not in expected:
                path.unlink(missing_ok=True)
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        for path in source.iterdir():
            if path.is_file():
                _replace_with_retry(path, target / path.name)
    elif not had_manifest:
        shutil.rmtree(target, ignore_errors=True)


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)


def _replace_with_retry(source: Path, target: Path, attempts: int = 5) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.1 * (2**attempt))


def _write_state(staging: Path, state: str) -> None:
    _write_json(staging / STATE_FILE, {"state": state})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.part")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
