"""A file the task forbids must not be demanded by the finish-blocker.

Observed 2026-07-23, all three runs of the textcase verification task on
`qwen2.5-coder:32b`. The task said "Do NOT create any __init__.py files".
`_missing_requested_files()` read that mention as a request, so `finish` was blocked
on a file the task prohibited; the blocker's advice ("an empty file is fine for
__init__.py") pushed the model to write it; the guardrails correctly refused to blank
the existing `src/agent/__init__.py`. The run then alternated between the two blocked
calls until the loop detector aborted it -- `state=error`, with correct code and a
passing suite already on disk.

Three things are locked in here: mentions in a prohibition are not requests, the
blocker no longer advises the forbidden write, and the block is bounded so an
unsatisfiable demand can never again consume a whole run.
"""
import types

import pytest

from agent.orchestrator import MAX_BLOCKED_FINISHES, Orchestrator


def _extractor(workspace, task):
    """A bare Orchestrator wired up just enough to run the path extractor."""
    orch = Orchestrator.__new__(Orchestrator)
    orch.workspace = workspace
    orch.frame = types.SimpleNamespace(task_description=task)
    return orch


# -- prohibitions are not requests --------------------------------------------

def test_the_task_that_deadlocked_the_agent(workspace):
    """The exact spec from the failing runs: neither __init__.py must be demanded."""
    task = (
        "Create ONLY two new files. ABSOLUTELY DO NOT modify ANY existing files "
        "(including src/agent/__init__.py). Modifying an existing file is a critical failure.\n"
        "1. src/agent/textcase.py containing three functions\n"
        "2. tests/unit/test_textcase.py with pytest tests.\n"
        "Conventions:\n"
        "- Do NOT create any __init__.py files."
    )

    missing = _extractor(workspace, task)._missing_requested_files()

    assert "__init__.py" not in missing, "a forbidden file was demanded -- this is the deadlock"
    assert "src/agent/__init__.py" not in missing
    assert missing == ["src/agent/textcase.py", "tests/unit/test_textcase.py"]


@pytest.mark.parametrize("sentence", [
    "Do not create src/forbidden.py.",
    "Don't create src/forbidden.py.",
    "Never create src/forbidden.py.",
    "You must not create src/forbidden.py.",
    "Avoid creating src/forbidden.py.",
    "Leave src/forbidden.py unchanged.",
    "Everything except src/forbidden.py.",
])
def test_forbidding_phrasings_are_all_honoured(workspace, sentence):
    task = f"Create src/wanted.py.\n{sentence}"

    missing = _extractor(workspace, task)._missing_requested_files()

    assert missing == ["src/wanted.py"], f"{sentence!r} did not suppress the path"


# -- the check must still do its original job ---------------------------------

def test_a_genuine_request_still_fires(workspace):
    """The blocker exists because 3 of 11 requested files were silently skipped."""
    task = "Create src/pkg/thing.py and src/pkg/__init__.py and tests/test_thing.py."

    missing = _extractor(workspace, task)._missing_requested_files()

    assert missing == ["src/pkg/__init__.py", "src/pkg/thing.py", "tests/test_thing.py"]


def test_sentence_splitting_does_not_shred_file_extensions(workspace):
    """Splitting on every '.' silently disabled the whole check -- it found nothing.

    The bug returned an empty list for every task, which reads as "all good" and would
    have gone unnoticed: an over-eager blocker is loud, a dead one is silent.
    """
    task = "Create src/alpha.py. Then create src/beta.py."

    missing = _extractor(workspace, task)._missing_requested_files()

    assert missing == ["src/alpha.py", "src/beta.py"]


def test_an_existing_file_is_never_reported_missing(workspace):
    (workspace / "present.py").write_text("x = 1\n")
    task = "Update src/absent.py and present.py."

    missing = _extractor(workspace, task)._missing_requested_files()

    assert "present.py" not in missing
    assert "src/absent.py" in missing


def test_a_task_naming_no_files_yields_nothing(workspace):
    missing = _extractor(workspace, "Refactor the code so it is easier to read.")

    assert missing._missing_requested_files() == []


# -- the blocker's advice must not name the forbidden write -------------------

def test_the_blocker_no_longer_suggests_an_empty_init_file():
    """That hardcoded advice is what aimed the model at the guardrail.

    Written for a packaging task, it was then applied to every task -- including ones
    that forbid __init__.py outright, where it told the model to make a write the
    guardrails refuse.
    """
    import inspect
    from agent.agents.legacy_executor import execute_legacy_step

    source = inspect.getsource(execute_legacy_step)

    assert "empty file is fine" not in source, "the harness still advises the forbidden write"


def test_the_block_is_bounded():
    """An unsatisfiable demand must end the run incomplete, not burn the budget.

    Relenting is the lesser evil: a run that finishes and reports what is missing is
    recoverable, one that aborts in `error` after doing the work correctly is not.
    """
    import inspect

    from agent.agents.finish_handler import handle_legacy_finish
    source = inspect.getsource(handle_legacy_finish)

    assert "MAX_BLOCKED_FINISHES" in source
    assert MAX_BLOCKED_FINISHES >= 1
