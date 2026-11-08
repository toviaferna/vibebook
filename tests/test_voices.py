from audiol.voices import get_voice, list_voices


def test_list_mx_voices():
    ids = [voice.id for voice in list_voices("es-MX")]
    assert ids == ["es-MX-DaliaNeural", "es-MX-JorgeNeural", "es_MX-ald-medium"]


def test_list_py_voices():
    ids = [voice.id for voice in list_voices("es-PY")]
    assert ids == ["es-PY-MarioNeural", "es-PY-TaniaNeural"]


def test_mx_styles_are_available():
    voice = get_voice("es-MX-JorgeNeural")
    assert "cheerful" in voice.styles
    assert "sad" in voice.styles


def test_list_voices_by_engine():
    edge_ids = [voice.id for voice in list_voices(engine="edge")]
    azure_ids = [voice.id for voice in list_voices(engine="azure")]

    assert edge_ids == [
        "es-MX-DaliaNeural",
        "es-MX-JorgeNeural",
        "es-PY-MarioNeural",
        "es-PY-TaniaNeural",
    ]
    assert azure_ids == ["es-MX-DaliaNeural", "es-MX-JorgeNeural"]
    assert [voice.id for voice in list_voices(engine="piper")] == ["es_MX-ald-medium"]
    assert [voice.id for voice in list_voices(engine="espeak")] == ["es-419"]


def test_list_fake_voices_returns_catalog():
    assert len(list_voices(engine="fake")) == len(list_voices())


def test_unknown_voice_raises():
    try:
        get_voice("no-existe")
    except ValueError as exc:
        assert "no-existe" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
