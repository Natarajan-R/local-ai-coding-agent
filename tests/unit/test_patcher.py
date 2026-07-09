import pytest

from agent.errors import ToolError
from agent.tools.patcher import apply_search_replace, make_diff


def test_apply_search_replace_basic():
    out = apply_search_replace("hello world", "world", "there")
    assert out == "hello there"


def test_apply_search_replace_missing():
    with pytest.raises(ToolError):
        apply_search_replace("abc", "xyz", "q")


def test_apply_search_replace_ambiguous():
    with pytest.raises(ToolError):
        apply_search_replace("a a a", "a", "b")


def test_apply_search_replace_empty_search():
    with pytest.raises(ToolError):
        apply_search_replace("abc", "", "q")


def test_make_diff_contains_changes():
    diff = make_diff("a\nb\n", "a\nc\n", "f.py")
    assert "-b" in diff and "+c" in diff


def test_fuzzy_match_tolerates_indentation():
    content = "def f():\n        return 1\n"  # over-indented body
    # Model supplies the block with "normal" 4-space indent.
    out = apply_search_replace(content, "    return 1", "    return 2")
    assert "return 2" in out
    assert "return 1" not in out


def test_fuzzy_match_tolerates_trailing_whitespace():
    content = "x = 1   \ny = 2\n"  # trailing spaces in file
    out = apply_search_replace(content, "x = 1", "x = 10")
    assert "x = 10" in out


def test_fuzzy_match_tolerates_tabs_vs_spaces():
    content = "def f():\n\treturn 1\n"  # tab-indented
    out = apply_search_replace(content, "    return 1", "    return 2")
    assert "return 2" in out


def test_fuzzy_ambiguous_is_rejected():
    content = "a = 1\nb = 0\na = 1\n"
    with pytest.raises(ToolError):
        apply_search_replace(content, "a = 1 ", "a = 2")  # matches two lines fuzzily


def test_fuzzy_replace_no_substring_collision():
    # The matched line ("foo bar") is also a substring of an earlier line
    # ("afoo bar"). The fuzzy path must splice the matched line range, not
    # replace the first substring occurrence in the whole file.
    content = "afoo bar\nfoo bar\n"
    out = apply_search_replace(content, "foo  bar", "baz")  # double space -> fuzzy
    assert out == "afoo bar\nbaz\n"


def test_fuzzy_can_be_disabled():
    content = "def f():\n\treturn 1\n"  # tab-indented; no exact space match
    with pytest.raises(ToolError):
        apply_search_replace(content, "    return 1", "    return 2", fuzzy=False)
