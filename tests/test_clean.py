from audiol.clean import clean_paragraphs, clean_text


def test_clean_text_collapses_spaces():
    assert clean_text("  Hola   mundo  ") == "Hola mundo"


def test_clean_text_fixes_hyphenation():
    assert clean_text("dijo-\nlo") == "dijolo"


def test_clean_text_joins_word_split_by_space():
    assert clean_text("ulti- ma parte") == "ultima parte"


def test_clean_text_removes_soft_hyphen():
    assert clean_text("ulti\u00adma") == "ultima"


def test_clean_text_normalizes_unicode_hyphens():
    assert clean_text("ulti\u2010 ma") == "ultima"
    assert clean_text("ulti\u2011ma") == "ulti-ma"


def test_clean_text_keeps_a_real_compound():
    assert clean_text("bien-venido") == "bien-venido"


def test_clean_text_keeps_dialogue_dashes():
    assert clean_text("—Hola —dijo.") == "—Hola —dijo."


def test_clean_text_normalizes_ellipsis_and_punctuation_spacing():
    assert clean_text("Hola ... mundo .") == "Hola… mundo."


def test_clean_paragraphs_joins_a_word_split_across_blocks():
    assert clean_paragraphs(["ulti-", "ma parte."]) == ["ultima parte."]


def test_clean_paragraphs_joins_a_word_with_a_leading_hyphen():
    assert clean_paragraphs(["ulti-", "-ma parte."]) == ["ultima parte."]


def test_clean_paragraphs_does_not_join_a_dialogue_dash():
    assert clean_paragraphs(["—Hola", "—dijo."]) == ["—Hola", "—dijo."]


def test_clean_paragraphs_removes_page_numbers_and_boilerplate():
    paragraphs = [
        "12",
        "Project Gutenberg eBook",
        "Hola.",
        "Hola.",
        "Mundo.",
    ]
    assert clean_paragraphs(paragraphs) == ["Hola.", "Mundo."]


def test_clean_paragraphs_keeps_accents():
    assert clean_paragraphs(["Canción de cuna."]) == ["Canción de cuna."]


def test_clean_paragraphs_removes_watermark():
    assert clean_paragraphs(["Hola.", "OceanofPDF.com", "Mundo."]) == ["Hola.", "Mundo."]
