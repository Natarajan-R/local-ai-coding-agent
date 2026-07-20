from agent.context import ContextManager


def _msg(role, content):
    return {"role": role, "content": content}


def test_under_budget_is_unchanged():
    cm = ContextManager(max_tokens=8192)
    msgs = [_msg("system", "rules"), _msg("user", "task"), _msg("assistant", "ok")]
    result = cm.fit(msgs)
    assert result.trimmed is False
    assert result.messages == msgs


def test_estimate_scales_with_length():
    cm = ContextManager()
    assert cm.estimate("x" * 400) > cm.estimate("x" * 40)


def test_trims_and_pins_system_and_recent():
    # Small budget forces trimming.
    cm = ContextManager(max_tokens=400, response_reserve=100, keep_recent=2)
    big = "y" * 4000  # ~1000 tokens each
    msgs = [
        _msg("system", "SYSTEM RULES"),
        _msg("user", "PRIMER: the task and plan"),
        _msg("assistant", big + " old1"),
        _msg("tool", big + " old2"),
        _msg("assistant", big + " old3"),
        _msg("tool", "RECENT tool output"),
        _msg("assistant", "RECENT assistant"),
    ]
    result = cm.fit(msgs)
    assert result.trimmed is True
    assert result.dropped >= 1

    contents = [m["content"] for m in result.messages]
    # System prompt and the primer are always kept (pinned head).
    assert "SYSTEM RULES" in contents[0]
    assert any("PRIMER" in c for c in contents)
    # The two most recent messages are preserved.
    assert "RECENT assistant" in contents[-1]
    assert any("RECENT tool output" in c for c in contents)
    # An elision marker records what was dropped.
    assert any("omitted to fit" in c for c in contents)
    # And the result actually fits the budget.
    assert cm.total_tokens(result.messages) <= cm.budget


def test_hard_truncate_when_head_and_tail_too_big():
    cm = ContextManager(max_tokens=300, response_reserve=50, keep_recent=1)
    huge = "z" * 20000
    msgs = [_msg("system", huge), _msg("user", huge), _msg("assistant", huge)]
    result = cm.fit(msgs)
    assert result.trimmed is True
    assert cm.total_tokens(result.messages) <= cm.budget


def test_budget_floor():
    cm = ContextManager(max_tokens=100, response_reserve=1000)
    assert cm.budget == 512  # never goes below the floor


def test_pins_memories_and_lessons_learned():
    cm = ContextManager(max_tokens=400, response_reserve=100, keep_recent=1)
    big = "y" * 4000
    msgs = [
        _msg("system", "SYSTEM RULES"),
        _msg("user", "PRIMER: task description"),
        _msg("user", "# Project memory (facts learned in previous runs — honor these):\n1. Do X"),
        _msg("user", "Lesson from a previous attempt: Do Y"),
        _msg("user", "The change failed evaluation. Lesson: Do Z"),
        _msg("assistant", big + " old_step"),
        _msg("assistant", "RECENT assistant"),
    ]
    result = cm.fit(msgs)
    assert result.trimmed is True
    
    contents = [m["content"] for m in result.messages]
    assert any("Project memory (facts learned" in c for c in contents)
    assert any("Lesson from a previous attempt:" in c for c in contents)
    assert any("The change failed evaluation." in c for c in contents)
    assert not any("old_step" in c for c in contents)

