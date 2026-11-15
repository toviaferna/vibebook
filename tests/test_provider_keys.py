import os
from pathlib import Path

import pytest

from audiol.provider_keys import (
    delete_provider_key,
    get_provider_key,
    get_provider_region,
    provider_configured,
    provider_hint,
    provider_source,
    set_provider_key,
)


def test_save_and_read_provider_key():
    set_provider_key("gemini", "AQ.test-key-1234")

    assert get_provider_key("gemini") == "AQ.test-key-1234"
    assert provider_configured("gemini") is True
    assert provider_hint("gemini") == "•••• 1234"
    assert provider_source("gemini") == "file"


def test_environment_wins_over_file(monkeypatch):
    set_provider_key("elevenlabs", "sk-file-key-1234")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-env-key-5678")

    assert get_provider_key("elevenlabs") == "sk-env-key-5678"
    assert provider_source("elevenlabs") == "env"


def test_azure_needs_a_region():
    with pytest.raises(ValueError, match="región"):
        set_provider_key("azure", "azure-key-1234")

    set_provider_key("azure", "azure-key-1234", "eastus")

    assert get_provider_region("azure") == "eastus"
    assert provider_configured("azure") is True


def test_delete_provider_key():
    set_provider_key("gemini", "AQ.test-key-1234")
    delete_provider_key("gemini")

    assert get_provider_key("gemini") is None
    assert provider_source("gemini") is None


def test_short_key_is_rejected():
    with pytest.raises(ValueError, match="corta"):
        set_provider_key("gemini", "short")


def test_provider_file_is_private(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VIBEBOOK_PROVIDER_KEYS", str(tmp_path / "keys.json"))
    set_provider_key("gemini", "AQ.test-key-1234")

    path = tmp_path / "keys.json"
    assert path.is_file()
    if os.name != "nt":
        assert path.stat().st_mode & 0o077 == 0
