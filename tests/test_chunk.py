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


def test_chunk_text_packs_short_sentences():
    assert chunk_text("Hola. ¿Qué tal? Adiós.", max_chars=400) == ["Hola. ¿Qué tal? Adiós."]


def test_chunk_text_cleans_split_words():
    assert chunk_text("ulti- ma parte", max_chars=400) == ["ultima parte"]


def test_chunk_text_does_not_split_a_long_word():
    word = "palabra" * 20
    assert chunk_text(word, max_chars=50) == [word]


def test_split_sentences_keeps_more_abbreviations():
    text = "La Sra. García llegó. El Dr. Pérez la vio. EE. UU. es un país."
    assert split_sentences(text) == [
        "La Sra. García llegó.",
        "El Dr. Pérez la vio.",
        "EE. UU. es un país.",
    ]
