from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from audiol.studio.errors import ApiError
from audiol.studio.library import BookNotFound
from audiol.studio.media import issue_ticket, path_matches_kind

router = APIRouter()


class MediaTicketRequest(BaseModel):
    book_id: str = Field(default="", max_length=200)
    kind: str
    path: str


class MediaTicketResponse(BaseModel):
    url: str
    expires_at: str


@router.post("/media/ticket", response_model=MediaTicketResponse)
def create_media_ticket(request: Request, payload: MediaTicketRequest) -> MediaTicketResponse:
    if not path_matches_kind(payload.path, payload.kind):
        raise ApiError(422, "invalid_media", "La ruta no corresponde al tipo de medio solicitado.")
    if payload.book_id:
        try:
            request.app.state.library.get(payload.book_id)
        except BookNotFound as exc:
            raise ApiError(404, "book_not_found", "El libro no existe.") from exc
        if f"/books/{payload.book_id}/" not in payload.path:
            raise ApiError(422, "invalid_media", "La ruta no pertenece al libro solicitado.")
    ticket, expires_at = issue_ticket(payload.book_id, payload.kind, payload.path)
    return MediaTicketResponse(url=f"{payload.path}?ticket={ticket}", expires_at=expires_at)
