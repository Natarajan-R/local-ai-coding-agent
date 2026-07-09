from agent.perception.analysis import (
    is_python_file,
    python_syntax_errors,
    syntax_note,
)


def test_valid_python_has_no_errors():
    assert python_syntax_errors("def f():\n    return 1\n") == []


def test_invalid_python_reports_error_with_location():
    errors = python_syntax_errors("def f(:\n    pass\n")
    assert errors
    assert "line" in errors[0]


def test_is_python_file():
    assert is_python_file("x.py")
    assert is_python_file("Y.PYI")
    assert not is_python_file("z.java")
    assert not is_python_file("readme.md")


def test_syntax_note_skips_non_python():
    assert syntax_note("notes.txt", "def f(:") == ""


def test_syntax_note_empty_for_valid_python():
    assert syntax_note("m.py", "x = 1\n") == ""


def test_syntax_note_warns_for_invalid_python():
    note = syntax_note("m.py", "def broken(:\n")
    assert "syntax error" in note.lower()
