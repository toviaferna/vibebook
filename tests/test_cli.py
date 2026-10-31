from audiol.cli import main


def test_cli_voices(capsys):
    assert main(["voices", "--locale", "es-PY"]) == 0
    output = capsys.readouterr().out
    assert "es-PY-MarioNeural" in output
    assert "es-PY-TaniaNeural" in output
    assert "es-MX-JorgeNeural" not in output
