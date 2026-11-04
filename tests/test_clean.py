from audiol.clean import clean_paragraphs, clean_text


def test_clean_text_collapses_spaces():
    assert clean_text("  Hola   mundo  ") == "Hola mundo"


def test_clean_text_fixes_hyphenation():
    assert clean_text("dijo-\nlo") == "dijolo"


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
