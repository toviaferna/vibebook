from fastapi import APIRouter, Request

from audiol.studio.models import EngineListResponse, EngineResponse
from audiol.tts.registry import engine_available, list_engines

router = APIRouter(tags=["engines"])


@router.get("/engines", response_model=EngineListResponse)
def get_engines(request: Request) -> EngineListResponse:
    allow_fake = request.app.state.settings.allow_fake
    return EngineListResponse(
        items=[
            EngineResponse(
                id=engine.id,
                label=engine.label,
                kind=engine.kind,
                transport=engine.transport,
                requires_network=engine.requires_network,
                requires_key=engine.requires_key,
                supports_styles=engine.supports_styles,
                timing=engine.timing,
                max_chars=engine.max_chars,
                audio_suffix=engine.audio_suffix,
                license=engine.license,
                source_url=engine.source_url,
                description=engine.description,
                config_schema=engine.config_schema,
                legacy=engine.legacy,
                implemented=engine.implemented,
                test_only=engine.test_only,
                available=engine_available(engine.id, allow_fake=allow_fake),
            )
            for engine in list_engines()
        ]
    )
