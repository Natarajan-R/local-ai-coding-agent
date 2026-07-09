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
