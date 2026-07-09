import json
import logging

from agent.logging import JsonFormatter, _DefaultFieldsFilter
from agent.prompts import FEWSHOT_EXAMPLES, SYSTEM_PROMPT


def test_system_prompt_includes_fewshot_and_finish():
    assert "Example A" in FEWSHOT_EXAMPLES
    assert "Example B" in FEWSHOT_EXAMPLES
    assert FEWSHOT_EXAMPLES in SYSTEM_PROMPT
    assert "finish" in SYSTEM_PROMPT


def _record(**extra):
    rec = logging.LogRecord("agent", logging.INFO, __file__, 1, "hello world", None, None)
    for k, v in extra.items():
        setattr(rec, k, v)
    return rec


def test_json_formatter_emits_valid_json():
    rec = _record(run_id="abc123")
    out = JsonFormatter().format(rec)
    parsed = json.loads(out)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["run_id"] == "abc123"


def test_default_fields_filter_supplies_run_id():
    rec = _record()
    assert not hasattr(rec, "run_id")
    assert _DefaultFieldsFilter().filter(rec)
    assert rec.run_id == "-"
