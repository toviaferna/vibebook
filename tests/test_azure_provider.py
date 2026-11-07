from pathlib import Path
from types import SimpleNamespace

import pytest

from audiol.models import WordTiming
from audiol.tts.azure import AzureProvider


def test_build_ssml_escapes_text_and_adds_style():
    provider = AzureProvider(key="test-key", region="eastus")
    ssml = provider.build_ssml(
        "Hola & adiós",
        "es-MX-JorgeNeural",
        style="cheerful",
        rate="-6%",
    )
    assert 'name="es-MX-JorgeNeural"' in ssml
    assert 'style="cheerful"' in ssml
    assert '<prosody rate="-6%">' in ssml
    assert "Hola &amp; adiós" in ssml
    assert 'xml:lang="es-MX"' in ssml


def test_build_ssml_rejects_invalid_rate():
    provider = AzureProvider(key="test-key", region="eastus")
    with pytest.raises(ValueError):
        provider.build_ssml("Hola", "es-MX-JorgeNeural", rate="fast")


def test_synthesize_writes_audio(monkeypatch, tmp_path: Path):
    class FakeResponse:
        status_code = 200
        content = b"ID3azure"
        text = ""

    captured = {}

    def fake_post(url, headers, data, timeout):
        captured["body"] = data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr("audiol.tts.azure.requests.post", fake_post)
    output = tmp_path / "azure.mp3"
    provider = AzureProvider(key="test-key", region="eastus", use_sdk=False)

    result = provider.synthesize("Hola", "es-MX-JorgeNeural", output, style="cheerful", rate="-6%")

    assert result.path == output
    assert output.read_bytes() == b"ID3azure"
    assert result.words == []
    assert '<prosody rate="-6%">' in captured["body"]


def test_sdk_captures_word_boundaries(monkeypatch, tmp_path: Path):
    captured = {}

    class FakeAudioConfig:
        def __init__(self, filename):
            self.filename = filename

    class FakeSpeechConfig:
        def __init__(self, subscription, region):
            self.subscription = subscription
            self.region = region

        def set_speech_synthesis_output_format(self, output_format):
            self.output_format = output_format

        def request_word_level_timestamps(self):
            self.timestamps = True

    class FakeSynthesizer:
        def __init__(self, speech_config, audio_config):
            self.speech_config = speech_config
            self.audio_config = audio_config
            self.callback = None
            self.synthesis_word_boundary = SimpleNamespace(connect=self.connect)

        def connect(self, callback):
            self.callback = callback

        def speak_ssml_async(self, ssml):
            captured["ssml"] = ssml
            return SimpleNamespace(get=self.get)

        def get(self):
            self.callback(SimpleNamespace(text="Hola", audio_offset=0))
            self.callback(SimpleNamespace(text="mundo", audio_offset=5_000_000))
            Path(self.audio_config.filename).write_bytes(b"ID3sdk")
            return SimpleNamespace(reason="completed")

    fake_sdk = SimpleNamespace(
        SpeechConfig=FakeSpeechConfig,
        audio=SimpleNamespace(AudioOutputConfig=FakeAudioConfig),
        SpeechSynthesizer=FakeSynthesizer,
        SpeechSynthesisOutputFormat=SimpleNamespace(Audio24Khz48KBitRateMonoMp3="mp3"),
        ResultReason=SimpleNamespace(SynthesizingAudioCompleted="completed"),
    )
    monkeypatch.setattr("audiol.tts.azure._load_speech_sdk", lambda: fake_sdk)
    output = tmp_path / "azure-sdk.mp3"
    provider = AzureProvider(key="test-key", region="eastus", use_sdk=True)

    result = provider.synthesize(
        "Hola mundo",
        "es-MX-JorgeNeural",
        output,
        style="cheerful",
        rate="-6%",
    )

    assert output.read_bytes() == b"ID3sdk"
    assert result.words == [
        WordTiming(text="Hola", start_ms=0, end_ms=500),
        WordTiming(text="mundo", start_ms=500, end_ms=900),
    ]
    assert 'style="cheerful"' in captured["ssml"]


def test_sdk_failure_falls_back_to_rest(monkeypatch, tmp_path: Path):
    class FailingSynthesizer:
        def __init__(self, speech_config, audio_config):
            self.synthesis_word_boundary = SimpleNamespace(connect=lambda callback: None)

        def speak_ssml_async(self, ssml):
            raise RuntimeError("sdk unavailable")

    fake_sdk = SimpleNamespace(
        SpeechConfig=lambda subscription, region: SimpleNamespace(
            set_speech_synthesis_output_format=lambda output_format: None
        ),
        audio=SimpleNamespace(
            AudioOutputConfig=lambda filename: SimpleNamespace(filename=filename)
        ),
        SpeechSynthesizer=FailingSynthesizer,
        SpeechSynthesisOutputFormat=SimpleNamespace(Audio24Khz48KBitRateMonoMp3="mp3"),
        ResultReason=SimpleNamespace(SynthesizingAudioCompleted="completed"),
    )

    class FakeResponse:
        status_code = 200
        content = b"ID3rest"
        text = ""

    monkeypatch.setattr("audiol.tts.azure._load_speech_sdk", lambda: fake_sdk)
    monkeypatch.setattr("audiol.tts.azure.requests.post", lambda *args, **kwargs: FakeResponse())
    output = tmp_path / "azure-rest.mp3"
    provider = AzureProvider(key="test-key", region="eastus", use_sdk=True)

    result = provider.synthesize("Hola", "es-MX-JorgeNeural", output)

    assert output.read_bytes() == b"ID3rest"
    assert result.words == []


def test_missing_credentials_raise(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    with pytest.raises(ValueError):
        AzureProvider()
