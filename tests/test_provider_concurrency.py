from audiol.tts.base import provider_concurrency


class _Provider:
    def __init__(self, max_concurrency: int) -> None:
        self.max_concurrency = max_concurrency


def test_provider_concurrency_uses_capability(monkeypatch):
    monkeypatch.delenv("VIBEBOOK_TTS_CONCURRENCY", raising=False)
    assert provider_concurrency(_Provider(4)) == 4


def test_provider_concurrency_defaults_to_one(monkeypatch):
    monkeypatch.delenv("VIBEBOOK_TTS_CONCURRENCY", raising=False)

    class NoCapability:
        pass

    assert provider_concurrency(NoCapability()) == 1


def test_provider_concurrency_env_can_only_reduce(monkeypatch):
    monkeypatch.setenv("VIBEBOOK_TTS_CONCURRENCY", "2")
    assert provider_concurrency(_Provider(8)) == 2

    monkeypatch.setenv("VIBEBOOK_TTS_CONCURRENCY", "32")
    assert provider_concurrency(_Provider(4)) == 4


def test_provider_concurrency_ignores_invalid_or_zero(monkeypatch):
    monkeypatch.setenv("VIBEBOOK_TTS_CONCURRENCY", "nope")
    assert provider_concurrency(_Provider(4)) == 4

    monkeypatch.setenv("VIBEBOOK_TTS_CONCURRENCY", "0")
    assert provider_concurrency(_Provider(4)) == 4
