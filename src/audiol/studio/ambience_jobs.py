from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from audiol.ambience.library import AmbienceLibrary
from audiol.ambience.mix import render_ambient_book
from audiol.ambience.models import AmbiencePlan, AmbienceSettings
from audiol.ambience.plan import load_ambience
from audiol.studio.activity import BookActivity, BookLease
from audiol.studio.db import Database
from audiol.studio.library import Library


class AmbienceRenderError(RuntimeError):
    pass


class AmbienceJobManager:
    def __init__(
        self,
        db: Database,
        library: Library,
        ambience: AmbienceLibrary,
        activity: BookActivity | None = None,
    ) -> None:
        self.db = db
        self.library = library
        self.ambience = ambience
        self.activity = activity or BookActivity()
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def start(self, book_id: str) -> str:
        lease = self.activity.reserve(book_id, "ambience_render")
        try:
            with self._lock:
                if self._active_job_id is not None:
                    raise AmbienceRenderError("Ya hay un render de ambiente en curso.")
                record = self.library.get(book_id)
                settings, plan = load_ambience(record.path)
                if not any(chapter.bed is not None or chapter.effects for chapter in plan.chapters):
                    raise AmbienceRenderError("El libro no tiene un plan de ambiente con cues.")
                job_id = f"job_{uuid4().hex}"
                manifest = json.loads((record.path / "manifest.json").read_text(encoding="utf-8"))
                total = len(manifest.get("chapters", []))
                self.db.create_job(
                    {
                        "id": job_id,
                        "book_id": record.id,
                        "status": "queued",
                        "stage": "rendering",
                        "total_segments": total,
                        "options_json": json.dumps({"kind": "ambience_render"}),
                    }
                )
                self._active_job_id = job_id
                thread = threading.Thread(
                    target=self._run,
                    args=(job_id, record.id, settings, plan, total, lease),
                    name=f"vibebook-{job_id}",
                    daemon=True,
                )
                thread.start()
                return job_id
        except BaseException:
            self.activity.release(lease)
            raise

    def _run(
        self,
        job_id: str,
        book_id: str,
        settings: AmbienceSettings,
        plan: AmbiencePlan,
        total: int,
        lease: BookLease,
    ) -> None:
        try:
            record = self.library.get(book_id)
            now = datetime.now(UTC).isoformat()
            self.db.update_job(job_id, status="running", stage="assembling", started_at=now)

            def progress(done: int, total: int, title: str) -> None:
                self.db.update_job(
                    job_id,
                    completed_segments=done,
                    total_segments=total,
                    chapter_index=done,
                    chapter_title=title,
                    message=f"Mezclando {title}",
                )

            output = render_ambient_book(
                record.path,
                plan,
                settings,
                self.ambience,
                progress=progress,
            )
            attribution = _attribution_text(self.db, plan)
            if attribution:
                output.with_name("ambientado-attribution.txt").write_text(
                    attribution,
                    encoding="utf-8",
                )
            self.db.update_job(
                job_id,
                status="completed",
                stage="done",
                message=str(output),
                completed_segments=total,
                finished_at=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:  # noqa: BLE001
            self.db.update_job(
                job_id,
                status="failed",
                stage="error",
                error=str(exc),
                message="No se pudo exportar el ambiente.",
                finished_at=datetime.now(UTC).isoformat(),
            )
        finally:
            self.activity.release(lease)
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None


def _attribution_text(db: Database, plan: AmbiencePlan) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for chapter in plan.chapters:
        asset_ids = []
        if chapter.bed is not None:
            asset_ids.append(chapter.bed.asset_id)
        asset_ids.extend(effect.asset_id for effect in chapter.effects)
        for asset_id in asset_ids:
            if asset_id in seen:
                continue
            seen.add(asset_id)
            asset = db.get_sound_asset(asset_id)
            if asset is None:
                continue
            license_name = str(asset.get("license") or "")
            attribution = asset.get("attribution")
            if license_name.upper().startswith("CC-BY") and attribution:
                lines.append(f"{asset_id}: {attribution} ({license_name})")
    if not lines:
        return ""
    return "Ambientación — atribuciones\n\n" + "\n".join(lines) + "\n"


def ambient_output_path(book_dir: Path) -> Path:
    return book_dir / "audio" / "ambientado.m4b"
