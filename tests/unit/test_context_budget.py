import pytest
from agent.orchestrator import Orchestrator


def test_compact_subtask_history_stays_under_budget_and_pins_anchors(workspace):
    """Bounded subtask history: under budget, anchors + recent kept, middle condensed."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local",
                        num_ctx=16384)
    coder = orch.coder_agent
    ctx = orch.context

    fat = "X" * 4000  # ~1000 tokens each
    msgs = [
        {"role": "system", "content": "SYSTEM RULES"},
        {"role": "user", "content": "INITIAL CONTEXT: file + spec + repo map"},
    ]
    for i in range(40):  # 40 rounds of accumulating feedback -> way over 16k
        msgs.append({"role": "assistant", "content": f"tool call {i}"})
        msgs.append({"role": "user", "content": f"Tool result {i}: {fat}"})

    assert ctx.total_tokens(msgs) > ctx.budget          # precondition: over budget
    out = coder._compact_subtask_history(msgs)

    # 1) under budget -> ContextManager.fit() will NOT trim (no log)
    assert ctx.total_tokens(out) <= ctx.budget - 2500
    # 2) anchors preserved (never lose the rules or the file/spec)
    assert out[0]["content"] == "SYSTEM RULES"
    assert "INITIAL CONTEXT" in out[1]["content"]
    # 3) most recent feedback preserved
    assert "Tool result 39" in out[-1]["content"]
    # 4) a condense marker replaces the dropped middle
    assert any("condensed to stay within" in str(m["content"]) for m in out)


def test_compact_subtask_history_noop_when_small(workspace):
    """Small histories are returned unchanged (no marker, no drops)."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local",
                        num_ctx=16384)
    coder = orch.coder_agent
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "ctx"},
        {"role": "assistant", "content": "a"},
        {"role": "user", "content": "r"},
    ]
    assert coder._compact_subtask_history(msgs) is msgs
