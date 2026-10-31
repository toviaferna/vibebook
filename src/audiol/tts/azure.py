import os
from pathlib import Path
from xml.sax.saxutils import escape

import requests

from audiol.tts.base import AudioResult

ALLOWED_STYLES = {
    "neutral",
    "chat",
    "cheerful",
    "excited",
    "sad",
    "whispering",
}


class AzureProvider:
    name = "azure"
    audio_suffix = ".mp3"

    def __init__(self, key: str | None = None, region: str | None = None) -> None:
        self.key = key or os.environ.get("AZURE_SPEECH_KEY")
        self.region = region or os.environ.get("AZURE_SPEECH_REGION")
        if not self.key or not self.region:
            raise ValueError(
                "Azure requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION"
            )

    def build_ssml(self, text: str, voice: str, style: str = "neutral") -> str:
        if style not in ALLOWED_STYLES:
            raise ValueError(f"Unsupported Azure style: {style}")
        locale = "-".join(voice.split("-")[:2])
        inner = escape(text)
        if style != "neutral":
            inner = (
                f'<mstts:express-as style="{style}" styledegree="1.2">'
                f"{inner}"
                "</mstts:express-as>"
            )
        return (
            '<speak version="1.0" '
            'xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="https://www.w3.org/2001/mstts" '
            f'xml:lang="{locale}">'
            f'<voice name="{escape(voice)}">{inner}</voice>'
            "</speak>"
        )

    def synthesize(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
    ) -> AudioResult:
        ssml = self.build_ssml(text, voice, style)
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "audiol",
        }
        response = requests.post(
            url,
            headers=headers,
            data=ssml.encode("utf-8"),
            timeout=60,
        )
        if response.status_code == 401:
            raise RuntimeError(
                "Azure TTS rejected the key (401). "
                "Check AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Azure TTS failed: {response.status_code} {response.text[:200]}"
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        return AudioResult(path=out_path)
