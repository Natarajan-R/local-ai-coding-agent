from agent.tools.parser import ToolParser


def test_parse_fenced_json():
    parser = ToolParser()
    text = """Sure, I'll read it.
```json
{"name": "read_file", "arguments": {"path": "a.py"}}
```
"""
    calls = parser.parse(text)
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments == {"path": "a.py"}


def test_parse_tool_call_tag():
    parser = ToolParser()
    text = '<tool_call>{"tool": "list_files", "args": {}}</tool_call>'
    calls = parser.parse(text)
    assert calls[0].name == "list_files"
    assert calls[0].arguments == {}


def test_parse_bare_object_fallback():
    parser = ToolParser()
    text = 'Let me write it {"name": "write_file", "arguments": {"path": "x", "content": "y"}} done'
    calls = parser.parse(text)
    assert calls[0].name == "write_file"
    assert calls[0].arguments["path"] == "x"


def test_parse_string_arguments_decoded():
    parser = ToolParser()
    text = '```json\n{"name": "read_file", "arguments": "{\\"path\\": \\"z.py\\"}"}\n```'
    calls = parser.parse(text)
    assert calls[0].arguments == {"path": "z.py"}


def test_parse_multiple_calls_in_array():
    parser = ToolParser()
    text = '```json\n[{"name":"list_files","arguments":{}},{"name":"finish","arguments":{"summary":"ok"}}]\n```'
    calls = parser.parse(text)
    assert [c.name for c in calls] == ["list_files", "finish"]


def test_parse_native_tool_calls():
    parser = ToolParser()
    native = [{"function": {"name": "write_file", "arguments": {"path": "a", "content": "b"}}}]
    calls = parser.parse_native(native)
    assert calls[0].name == "write_file"
    assert calls[0].arguments["content"] == "b"


def test_parse_empty_returns_nothing():
    assert ToolParser().parse("") == []
    assert ToolParser().parse("just some prose, no tools here") == []


# --- docstrings vs JSON -----------------------------------------------------
# A model asked to add a docstring hand-writes a tool call whose `replace` value
# contains a raw Python `"""`. That is illegal inside a JSON string: it closes
# the string early, json.loads raises, and the call was silently dropped. The
# agent looked like it "refused to write docstrings" while actually producing
# perfectly good ones every single time. Documenting a file was 0/9 because of
# this one thing.

DOCSTRING_CALL = (
    '{"name": "search_replace", "arguments": {"path": "shapes.py", '
    '"search": "def area_circle(r):", '
    '"replace": "def area_circle(r):\\n    """Return the area.\\n\\n'
    '    Args:\\n        r (float): radius.\\n    """"}}'
)


def test_raw_triple_quotes_do_not_lose_the_call():
    calls = ToolParser().parse(DOCSTRING_CALL)
    assert len(calls) == 1
    assert calls[0].name == "search_replace"
    assert '"""Return the area.' in calls[0].arguments["replace"]


def test_correctly_escaped_docstring_still_parses():
    # The repair must not fire on a payload that got the escaping right.
    payload = (
        '{"name": "search_replace", "arguments": {"path": "a.py", "search": "x", '
        '"replace": "def f():\\n    \\"\\"\\"Doc.\\"\\"\\"\\n"}}'
    )
    calls = ToolParser().parse(payload)
    assert len(calls) == 1
    assert '"""Doc."""' in calls[0].arguments["replace"]


def test_genuinely_broken_json_is_still_rejected(caplog):
    import logging
    parser = ToolParser()
    with caplog.at_level(logging.WARNING):
        # Matching braces but invalid JSON syntax inside fenced block
        calls = parser.parse('```json\n{"name": "read_file", "arguments": { "path": }}\n```')
        assert len(calls) == 0
        assert any("Parser dropped candidate chunk: JSON decoding failed" in record.message for record in caplog.records)


def test_invalid_tool_call_object_logs_warning(caplog):
    import logging
    parser = ToolParser()
    with caplog.at_level(logging.WARNING):
        # JSON is valid, matched by fence, but missing name/tool key
        calls = parser.parse('```json\n{"not_a_tool": "read_file", "arguments": {}}\n```')
        assert len(calls) == 0
        assert any("Parser ignored valid JSON object" in record.message for record in caplog.records)


def test_parse_truncated_bare_object_logs_warning(caplog):
    import logging
    parser = ToolParser()
    with caplog.at_level(logging.WARNING):
        calls = parser.parse('Here is the call: {"name": "read_file", "arguments": {"path"')
        assert len(calls) == 0
        assert any("Parser dropped truncated candidate chunk: JSON decoding failed" in record.message for record in caplog.records)


def test_parse_truncated_fence_logs_warning(caplog):
    import logging
    parser = ToolParser()
    with caplog.at_level(logging.WARNING):
        calls = parser.parse('```json\n{"name": "read_file", "arguments": {"path": "a.py"')
        assert len(calls) == 0
        assert any("Parser dropped truncated candidate chunk: JSON decoding failed" in record.message for record in caplog.records)



def test_saw_truncated_call_detects_cutoff_tool_call():
    # A tool call cut off mid-JSON (unbalanced) is dropped by parse(), but the
    # caller must be able to tell truncation apart from "no tool call at all" so
    # it can ask for a SMALLER edit rather than resending the oversized one.
    parser = ToolParser()
    truncated = ('{"name": "edit_lines", "arguments": {"path": "go.py", '
                 '"replace": "def f():\\n    return sum(itms')  # never closed
    assert parser.saw_truncated_call(truncated) is True
    # parse() still yields nothing for it (it is genuinely unusable)
    assert parser.parse(truncated) == []


def test_saw_truncated_call_false_on_complete_and_prose():
    parser = ToolParser()
    complete = ('{"name": "edit_lines", "arguments": {"path": "go.py", '
                '"start_line": 6, "end_line": 6, "search": "pass", "replace": "x=1"}}')
    assert parser.saw_truncated_call(complete) is False
    assert len(parser.parse(complete)) == 1          # the complete call still parses
    assert parser.saw_truncated_call("just some prose, no tool call") is False
    assert parser.saw_truncated_call("") is False
