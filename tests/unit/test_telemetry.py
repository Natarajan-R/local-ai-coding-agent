from agent.telemetry import RunStats


def test_record_accumulates_across_calls():
    stats = RunStats()
    stats.record({"prompt_eval_count": 100, "eval_count": 20, "total_duration": 1_000_000_000})
    stats.record({"prompt_eval_count": 50, "eval_count": 10, "total_duration": 1_000_000_000})
    assert stats.model_calls == 2
    assert stats.prompt_tokens == 150
    assert stats.completion_tokens == 30
    assert stats.total_tokens == 180
    assert stats.total_seconds == 2.0
    assert stats.tokens_per_second == 15.0  # 30 completion tokens / 2s


def test_record_ignores_empty_and_missing_fields():
    stats = RunStats()
    stats.record(None)
    stats.record({})  # counts as a call but adds no tokens
    assert stats.model_calls == 1
    assert stats.total_tokens == 0
    assert stats.tokens_per_second == 0.0


def test_as_dict_shape():
    stats = RunStats()
    stats.record({"prompt_eval_count": 10, "eval_count": 5, "total_duration": 500_000_000})
    d = stats.as_dict()
    assert d["total_tokens"] == 15
    assert set(d) == {
        "model_calls", "prompt_tokens", "completion_tokens",
        "total_tokens", "total_seconds", "tokens_per_second",
    }
