"""Minimal Vibebook Engine Protocol (VEP) v1 server.

Run with:
    python server.py --port 9001
"""

from __future__ import annotations

import argparse
import base64
import io
import math
import os
import struct
import wave

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

PROTOCOL = "vep/1"
VOICES = [
    {
        "id": "es-MX-demo",
        "locale": "es-MX",
        "gender": "female",
        "styles": [],
    }
]
INFO = {
    "protocol": PROTOCOL,
    "id": "demo-sine",
    "name": "Demo Sine",
    "version": "1.0.0",
    "license": "MIT",
    "source": "https://example.com/demo-sine",
    "capabilities": {
        "languages": ["es"],
        "styles": [],
        "timings": "segment",
        "streaming": False,
    },
    "limits": {
        "max_chars": 400,
        "max_concurrency": 1,
        "timeout_seconds": 30,
    },
    "voices": VOICES,
}


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    voice: str
    style: str = "neutral"
    rate: str = "+0%"
    format: str = "wav"


def create_app() -> FastAPI:
    app = FastAPI(title="Demo VEP plugin", version="1.0.0")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            payload = detail
        else:
            payload = {"error": {"code": "http_error", "message": str(detail)}}
        return JSONResponse(status_code=exc.status_code, content=payload)

    def authorize(token: str | None) -> None:
        expected = os.environ.get("VEP_TOKEN")
        if expected and token != expected:
            raise HTTPException(
                status_code=401,
                detail={"error": {"code": "unauthorized", "message": "Invalid plugin token"}},
            )

    @app.get("/v1/info")
    def info(x_vibebook_plugin_token: str | None = Header(default=None)) -> dict:
        authorize(x_vibebook_plugin_token)
        return INFO

    @app.get("/v1/health")
    def health(x_vibebook_plugin_token: str | None = Header(default=None)) -> dict:
        authorize(x_vibebook_plugin_token)
        return {"ok": True}

    @app.get("/v1/voices")
    def voices(x_vibebook_plugin_token: str | None = Header(default=None)) -> dict:
        authorize(x_vibebook_plugin_token)
        return {"voices": VOICES}

    @app.post("/v1/synthesize")
    def synthesize(
        request: SynthesizeRequest,
        x_vibebook_plugin_token: str | None = Header(default=None),
    ) -> dict:
        authorize(x_vibebook_plugin_token)
        if request.format != "wav":
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "unsupported_format", "message": "Use wav"}},
            )
        if request.voice not in {voice["id"] for voice in VOICES}:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "unknown_voice", "message": "Unknown voice"}},
            )
        audio = _sine_wav(seconds=0.4)
        return {
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "format": "wav",
            "duration_ms": 400,
            "words": [],
        }

    return app


def _sine_wav(seconds: float, sample_rate: int = 22_050) -> bytes:
    frames = int(seconds * sample_rate)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        samples = (
            int(32767 * 0.15 * math.sin(2 * math.pi * 440 * index / sample_rate))
            for index in range(frames)
        )
        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return buffer.getvalue()


app = create_app()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the VEP demo plugin")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    args = parser.parse_args()
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
