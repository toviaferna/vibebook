from audiol.chunk import chunk_text, split_sentences


def test_split_sentences_keeps_abbreviations():
    text = "Hola. ¿Qué tal? V.M. dijo que sí."
    assert split_sentences(text) == ["Hola.", "¿Qué tal?", "V.M. dijo que sí."]


def test_chunk_text_respects_max_chars():
    text = " ".join(["palabra"] * 200)
    chunks = chunk_text(text, max_chars=50)
    assert chunks
    assert all(len(chunk) <= 50 for chunk in chunks)


def test_chunk_text_does_not_return_empty_chunks():
    assert chunk_text("   ") == []
