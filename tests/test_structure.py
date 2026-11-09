from bs4 import BeautifulSoup

from audiol.ingest.structure import block_texts, extract_bare_text


def test_block_texts_does_not_insert_spaces_between_inline_spans():
    soup = BeautifulSoup("<p><span>ulti-</span><span>ma</span> parte.</p>", "lxml")

    assert block_texts([soup.p]) == ["ultima parte."]


def test_block_texts_keeps_a_real_hyphen_inside_a_word():
    soup = BeautifulSoup("<p>bien-venido.</p>", "lxml")

    assert block_texts([soup.p]) == ["bien-venido."]


def test_block_texts_keeps_source_spaces_between_inline_tags():
    soup = BeautifulSoup("<p>Hola <em>mundo</em>.</p>", "lxml")

    assert block_texts([soup.p]) == ["Hola mundo."]


def test_block_texts_turns_br_into_a_space():
    soup = BeautifulSoup("<p>Hola<br/>mundo.</p>", "lxml")

    assert block_texts([soup.p]) == ["Hola mundo."]


def test_extract_bare_text_does_not_join_inline_words_with_spaces():
    soup = BeautifulSoup(
        "<body><div><span>ulti-</span><span>ma</span> parte.</div></body>",
        "lxml",
    )

    assert extract_bare_text(soup) == ["ultima parte."]
