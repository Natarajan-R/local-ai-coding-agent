from agent.memory import MemoryStore


def test_add_load_roundtrip(workspace):
    m = MemoryStore(workspace)
    e = m.add("Tests live in tests/ and use pytest fixtures", kind="convention")
    assert e is not None and e.kind == "convention"
    loaded = MemoryStore(workspace).load()  # a fresh store reads the same file
    assert len(loaded) == 1
    assert loaded[0].text.startswith("Tests live in")


def test_dedupe_and_empty(workspace):
    m = MemoryStore(workspace)
    assert m.add("Use black for formatting") is not None
    assert m.add("use   BLACK for  formatting") is None   # normalized duplicate
    assert m.add("   ") is None                            # empty
    assert m.count() == 1


def test_unknown_kind_becomes_note(workspace):
    m = MemoryStore(workspace)
    e = m.add("something", kind="banana")
    assert e.kind == "note"


def test_format_for_prompt_recent_first_and_capped(workspace):
    m = MemoryStore(workspace)
    for i in range(30):
        m.add(f"fact number {i}", kind="note")
    text = m.format_for_prompt(max_entries=5)
    assert "Project memory" in text
    assert "fact number 29" in text     # most recent included
    assert "fact number 0" not in text  # oldest trimmed
    assert text.count("\n- ") <= 5


def test_disabled_store_is_noop(workspace):
    m = MemoryStore(workspace, enabled=False)
    assert m.add("x") is None
    assert m.load() == []
    assert m.format_for_prompt() == ""


def test_clear(workspace):
    m = MemoryStore(workspace)
    m.add("a")
    m.add("b")
    assert m.clear() == 2
    assert m.count() == 0
