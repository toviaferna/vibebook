from audiol.language import detect_language

SPANISH = """
La casa de los Ferrer se levantaba sobre una loma que olía a sal y a romero.
Desde la ventana del norte se veía el puerto y una línea de barcos que entraban
y salían con la paciencia de las cosas que siempre vuelven. Lucía había heredado
la casa en marzo, junto con un mapa que no representaba ninguna costa conocida.
"""

ENGLISH = """
The house of the Ferrer family stood on a hill that smelled of salt and rosemary.
From the north window you could see the harbor and a line of boats that came and
went with the patience of things that always return. Lucia had inherited the
house in March, along with a map that did not represent any known coast.
"""


def test_detects_spanish_text():
    assert detect_language(SPANISH) == "es"


def test_detects_english_text():
    assert detect_language(ENGLISH) == "en"


def test_short_or_ambiguous_text_returns_none():
    assert detect_language("hola mundo") is None
    assert detect_language("1234 5678 9012") is None
