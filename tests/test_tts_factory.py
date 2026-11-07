import pytest

from audiol.tts.edge import EdgeProvider
from audiol.tts.factory import make_provider
from audiol.tts.fake import FakeProvider


def test_make_provider_returns_edge():
    assert isinstance(make_provider("edge"), EdgeProvider)


def test_make_provider_rejects_fake_unless_allowed():
    with pytest.raises(ValueError):
        make_provider("fake")

    assert isinstance(make_provider("fake", allow_fake=True), FakeProvider)


def test_make_provider_rejects_unknown_engine():
    with pytest.raises(ValueError):
        make_provider("unknown")
