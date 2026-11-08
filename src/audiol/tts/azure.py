import logging
import os
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import requests

from audiol.models import WordTiming
from audiol.tts.base import AudioResult, validate_rate

logger = logging.getLogger(__name__)

ALLOWED_STYLES = {
    "neutral",
    "chat",
    "cheerful",
    "excited",
    "sad",
    "whispering",
}


def _load_speech_sdk() -> Any | None:
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        return None
    return speechsdk


class AzureProvider:
    name = "azure"
    audio_suffix = ".mp3"
    key: str
    region: str

    def __init__(
        self,
        key: str | None = None,
        region: str | None = None,
        use_sdk: bool | None = None,
    ) -> None:
        resolved_key = key or os.environ.get("AZURE_SPEECH_KEY")
        resolved_region = region or os.environ.get("AZURE_SPEECH_REGION")
        if not resolved_key or not resolved_region:
            raise ValueError("Azure requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
        self.key = resolved_key
        self.region = resolved_region
        self.use_sdk = use_sdk

    def build_ssml(
        self,
        text: str,
        voice: str,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> str:
        if style not in ALLOWED_STYLES:
            raise ValueError(f"Unsupported Azure style: {style}")
        rate = validate_rate(rate)
        locale = "-".join(voice.split("-")[:2])
        inner = f'<prosody rate="{rate}">{escape(text)}</prosody>'
        if style != "neutral":
            inner = (
                f'<mstts:express-as style="{style}" styledegree="1.2">{inner}</mstts:express-as>'
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
        rate: str = "+0%",
    ) -> AudioResult:
        if self._sdk_enabled():
            try:
                return self._synthesize_sdk(text, voice, out_path, style=style, rate=rate)
            except Exception as exc:
                logger.warning("Azure SDK synthesis failed; falling back to REST: %s", exc)
        return self._synthesize_rest(text, voice, out_path, style=style, rate=rate)

    def _sdk_enabled(self) -> bool:
        if self.use_sdk is not None:
            return self.use_sdk
        return _load_speech_sdk() is not None

    def _synthesize_sdk(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> AudioResult:
        speechsdk = _load_speech_sdk()
        if speechsdk is None:
            raise RuntimeError("Azure Speech SDK is not installed")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
        )
        request_timestamps = getattr(speech_config, "request_word_level_timestamps", None)
        if callable(request_timestamps):
            request_timestamps()

        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out_path))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        boundaries: list[tuple[str, int]] = []

        def on_word_boundary(event: Any) -> None:
            word = (getattr(event, "text", "") or "").strip()
            if not word:
                return
            offset = getattr(event, "audio_offset", 0)
            try:
                start_ms = max(0, int(offset) // 10_000)
            except (TypeError, ValueError):
                start_ms = 0
            boundaries.append((word, start_ms))

        synthesizer.synthesis_word_boundary.connect(on_word_boundary)
        ssml = self.build_ssml(text, voice, style=style, rate=rate)
        result = synthesizer.speak_ssml_async(ssml).get()
        reason = getattr(result, "reason", None)
        completed = getattr(speechsdk.ResultReason, "SynthesizingAudioCompleted", None)
        if completed is not None and reason != completed:
            details = getattr(result, "cancellation_details", None)
            error = getattr(details, "error_details", "") if details is not None else ""
            raise RuntimeError(f"Azure SDK synthesis failed: {reason} {error}".strip())
        if not out_path.is_file():
            raise RuntimeError("Azure SDK did not write the audio file")

        words: list[WordTiming] = []
        for index, (word, start_ms) in enumerate(boundaries):
            if index + 1 < len(boundaries):
                end_ms = boundaries[index + 1][1]
            else:
                end_ms = start_ms + max(1, len(word) * 80)
            if end_ms <= start_ms:
                end_ms = start_ms + 1
            words.append(WordTiming(text=word, start_ms=start_ms, end_ms=end_ms))
        return AudioResult(path=out_path, words=words)

    def _synthesize_rest(
        self,
        text: str,
        voice: str,
        out_path: Path,
        style: str = "neutral",
        rate: str = "+0%",
    ) -> AudioResult:
        ssml = self.build_ssml(text, voice, style, rate=rate)
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
                "Azure TTS rejected the key (401). Check AZURE_SPEECH_KEY and AZURE_SPEECH_REGION."
            )
        if response.status_code != 200:
            raise RuntimeError(f"Azure TTS failed: {response.status_code} {response.text[:200]}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(response.content)
        return AudioResult(path=out_path)
