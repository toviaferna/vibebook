import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from audiol.studio.errors import ApiError
from audiol.studio.jobs import (
    TERMINAL_JOB_STATUSES,
    JobInProgress,
    JobNotActive,
    JobNotFound,
    JobOptions,
)
from audiol.studio.library import BookNotFound
from audiol.studio.models import ConvertRequest, JobResponse

router = APIRouter(tags=["jobs"])


def _job_response(job: dict) -> JobResponse:
    return JobResponse(**job)


def _job_or_404(request: Request, job_id: str) -> dict:
    try:
        return request.app.state.jobs.get(job_id)
    except JobNotFound as exc:
        raise ApiError(404, "job_not_found", "El trabajo no existe.") from exc


@router.post("/books/{book_id}/convert", status_code=202)
def start_conversion(request: Request, book_id: str, payload: ConvertRequest) -> dict:
    try:
        request.app.state.library.get(book_id)
    except BookNotFound as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc

    options = JobOptions(
        voice=payload.voice,
        engine=payload.engine,
        style=payload.style,
        rate=payload.rate,
        force=payload.force,
    )
    try:
        job_id = request.app.state.jobs.start(book_id, options)
    except JobInProgress as exc:
        raise ApiError(409, "job_in_progress", "Ya hay una conversión en curso.") from exc
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc
    return {"job_id": job_id}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(request: Request, job_id: str) -> JobResponse:
    return _job_response(_job_or_404(request, job_id))


@router.post("/jobs/{job_id}/cancel", status_code=202, response_model=JobResponse)
def cancel_job(request: Request, job_id: str) -> JobResponse:
    try:
        job = request.app.state.jobs.cancel(job_id)
    except JobNotFound as exc:
        raise ApiError(404, "job_not_found", "El trabajo no existe.") from exc
    except JobNotActive as exc:
        raise ApiError(409, "job_not_active", "El trabajo ya terminó o no está activo.") from exc
    return _job_response(job)


@router.post("/jobs/{job_id}/resume", status_code=202)
def resume_job(request: Request, job_id: str) -> dict:
    job = _job_or_404(request, job_id)
    if job["status"] not in {"cancelled", "interrupted", "failed"}:
        raise ApiError(
            409,
            "job_not_resumable",
            "Solo se pueden reanudar trabajos cancelados, interrumpidos o fallidos.",
        )
    options = JobOptions(**job["options"])
    try:
        new_job_id = request.app.state.jobs.start(job["book_id"], options)
    except JobInProgress as exc:
        raise ApiError(409, "job_in_progress", "Ya hay una conversión en curso.") from exc
    except BookNotFound as exc:
        raise ApiError(404, "book_not_found", "El libro no existe.") from exc
    except ValueError as exc:
        raise ApiError(422, "invalid_options", str(exc)) from exc
    return {"job_id": new_job_id}


@router.get("/jobs/{job_id}/events")
def job_events(request: Request, job_id: str) -> StreamingResponse:
    _job_or_404(request, job_id)

    async def event_stream():
        last_payload: str | None = None
        ticks = 0
        while True:
            job = request.app.state.db.get_job(job_id)
            if job is None:
                yield 'event: error\ndata: {"error":"job_not_found"}\n\n'
                break
            payload = json.dumps(job, ensure_ascii=False)
            if payload != last_payload:
                yield f"event: job\ndata: {payload}\n\n"
                last_payload = payload
                ticks = 0
            if job["status"] in TERMINAL_JOB_STATUSES:
                break
            if ticks >= 30:
                yield ": ping\n\n"
                ticks = 0
            ticks += 1
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
