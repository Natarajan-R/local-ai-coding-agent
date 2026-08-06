import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from agent.orchestrator import Orchestrator
from agent.fsm import AgentState
from agent import prompts
from agent.model.client import ChatResponse


def test_milestone_planner_prompt_shape():
    msgs = prompts.milestone_planner_messages("build X", "skeleton here")
    assert any("milestone" in str(m.get("content")).lower() for m in msgs)
    assert any("build X" in str(m.get("content")) for m in msgs)


def test_parse_milestones_validates_and_dedupes(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    planner = orch.planner_agent
    raw = json.dumps([
        {"name": "models",
         "files": [{"path": "src/models/user.py", "change_description": "User", "is_new": True},
                   {"path": "src/models/user.py", "change_description": "dup", "is_new": True},   # dup dropped
                   {"path": None, "change_description": "invalid"}],                               # invalid dropped
         "tests": ["tests/test_users.py"]},
        {"name": "services",
         "files": [{"path": "src/services/user_service.py", "change_description": "svc", "is_new": True}],
         "tests": []},
        {"name": "empty", "files": [], "tests": ["x"]},                                            # no files -> skipped
    ])
    ms = planner._parse_milestones(raw, workspace)
    assert [m["name"] for m in ms] == ["models", "services"]
    assert [f["path"] for f in ms[0]["files"]] == ["src/models/user.py"]   # deduped + validated
    assert ms[0]["tests"] == ["tests/test_users.py"]


@pytest.mark.asyncio
async def test_milestone_planning_stores_milestones_and_flat_checklist(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.fsm.state = AgentState.PLANNING
    milestones = [
        {"name": "models", "files": [{"path": "m.py", "change_description": "c", "is_new": True}], "tests": ["t.py"]},
    ]
    resp = ChatResponse(content=f"```json\n{json.dumps(milestones)}\n```", raw={})
    orch._chat = AsyncMock(return_value=resp)
    orch._chat_stream = AsyncMock(return_value=resp)
    await orch.planner_agent.execute()
    assert orch.frame.metadata["milestones"][0]["name"] == "models"
    # flat checklist derived for missing-files / refinement compatibility
    assert [c["path"] for c in orch.frame.metadata["checklist"]] == ["m.py"]
    assert orch.fsm.state == AgentState.EXECUTING


@pytest.mark.asyncio
async def test_milestone_execution_builds_then_verifies_scope(workspace):
    """Each milestone's files are built, then ONLY its tests run; retry stops once green."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.fsm.state = AgentState.EXECUTING
    (workspace / "tests").mkdir(exist_ok=True)
    (workspace / "tests" / "test_a.py").write_text("def test_a(): assert True\n")
    orch.frame.metadata["milestones"] = [
        {"name": "layer A", "files": [{"path": "a.py", "change_description": "make a", "is_new": True}],
         "tests": ["tests/test_a.py"]},
    ]

    built = []
    async def fake_build(item, lesson, max_steps=None):
        built.append(item["path"])
        (orch.workspace / item["path"]).write_text("x = 1\n")
    orch.coder_agent._build_file = fake_build

    # scoped verify passes on first attempt -> no retry
    orch.coder_agent._verify_scope = AsyncMock(return_value=(True, "1 passed, 0 failed, 0 skipped", [], False))

    await orch.coder_agent.execute()
    assert built == ["a.py"]                                   # milestone file built
    orch.coder_agent._verify_scope.assert_awaited()           # scoped verification ran
    assert orch.fsm.state == AgentState.EVALUATING            # advanced after milestones


@pytest.mark.asyncio
async def test_milestone_retries_on_scoped_failure(workspace):
    """A milestone whose scoped tests fail is rebuilt up to MAX_MILESTONE_RETRIES."""
    from agent.agents.coder import AgentConfig
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.fsm.state = AgentState.EXECUTING
    orch.frame.metadata["milestones"] = [
        {"name": "L", "files": [{"path": "a.py", "change_description": "c", "is_new": True}], "tests": ["tests/t.py"]},
    ]
    calls = {"build": 0}
    async def fake_build(item, lesson, max_steps=None): calls["build"] += 1
    orch.coder_agent._build_file = fake_build
    # A real assertion failure (not a collection error) -> retried up to the max.
    orch.coder_agent._verify_scope = AsyncMock(
        return_value=(False, "0 passed, 1 failed, 0 skipped", ["t::x"], False))

    await orch.coder_agent.execute()
    # built once per attempt, MAX_MILESTONE_RETRIES attempts (1 file each)
    assert calls["build"] == AgentConfig.MAX_MILESTONE_RETRIES
    assert orch.fsm.state == AgentState.EVALUATING           # still advances (honest, full-suite eval follows)


@pytest.mark.asyncio
async def test_milestone_collection_error_defers_instead_of_retrying(workspace):
    """A collection/import error is not layer-local -> build once, then defer to reflexion."""
    from agent.agents.coder import AgentConfig
    assert AgentConfig.MAX_MILESTONE_RETRIES >= 2   # otherwise this test proves nothing
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.fsm.state = AgentState.EXECUTING
    orch.frame.metadata["milestones"] = [
        {"name": "L", "files": [{"path": "a.py", "change_description": "c", "is_new": True}], "tests": ["tests/t.py"]},
    ]
    calls = {"build": 0}
    async def fake_build(item, lesson, max_steps=None): calls["build"] += 1
    orch.coder_agent._build_file = fake_build
    orch.coder_agent._verify_scope = AsyncMock(return_value=(
        False, "tests could not be collected (import/collection error):\nE ImportError", [], True))

    await orch.coder_agent.execute()
    # Broke out after the FIRST failed attempt instead of exhausting the retry budget.
    assert calls["build"] == 1
    assert orch.fsm.state == AgentState.EVALUATING


def test_attach_tests_by_name_maps_layers_to_tests(workspace):
    """Auto-attach: a layer's test files are matched by shared name-stems."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    planner = orch.planner_agent
    milestones = [
        {"name": "models", "files": [{"path": "src/models/user.py"}, {"path": "src/models/product.py"}], "tests": []},
        {"name": "routes", "files": [{"path": "src/routes/orders.py"}], "tests": []},
        {"name": "tests", "files": [
            {"path": "tests/test_users.py"}, {"path": "tests/test_products.py"}, {"path": "tests/test_orders.py"}
        ], "tests": []},
    ]
    out = planner._attach_tests_by_name(milestones)
    models_tests = set(out[0]["tests"])
    assert "tests/test_users.py" in models_tests and "tests/test_products.py" in models_tests
    assert "tests/test_orders.py" not in models_tests          # not a models test
    assert out[1]["tests"] == ["tests/test_orders.py"]          # routes/orders -> test_orders


def test_ensure_requested_files_planned_appends_missing_deliverables(workspace):
    """Files the task named but the model omitted become a final build milestone."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.frame.task_description = (
        "Build the API. Create exactly these files: src/routes/auth.py, "
        "test_auth.py, setup.py."
    )
    planner = orch.planner_agent
    # Model planned only the source layer, dropping the required test + setup files.
    milestones = [
        {"name": "routes", "files": [{"path": "src/routes/auth.py", "change_description": "auth"}],
         "tests": []},
    ]
    out = planner._ensure_requested_files_planned(milestones, workspace)
    assert out[-1]["name"] == "required deliverables"
    added = {f["path"] for f in out[-1]["files"]}
    assert "test_auth.py" in added and "setup.py" in added
    assert "src/routes/auth.py" not in added          # already planned -> not duplicated
    assert out[-1]["tests"] == ["test_auth.py"]        # the test file becomes scoped verification


def test_ensure_requested_files_planned_dedupes_tree_basenames(workspace):
    """Bare filenames from a tree diagram are covered by their planned src/ home."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    # Task lists files as a tree, so the extractor sees basenames: user.py, auth.py, ...
    orch.frame.task_description = (
        "Build it. Files:\n"
        "  src/\n    models/\n      user.py\n    routes/\n      auth.py\n"
        "  test_auth.py\n  setup.py\n"
    )
    planner = orch.planner_agent
    milestones = [
        {"name": "models", "files": [{"path": "src/models/user.py", "change_description": "u"}], "tests": []},
        {"name": "routes", "files": [{"path": "src/routes/auth.py", "change_description": "a"}], "tests": []},
    ]
    out = planner._ensure_requested_files_planned(milestones, workspace)
    added = {f["path"] for f in out[-1]["files"]}
    # user.py / auth.py are basenames of already-planned files -> NOT re-created at root.
    assert "user.py" not in added and "auth.py" not in added
    # setup.py / test_auth.py have no planned counterpart -> genuinely added.
    assert added == {"test_auth.py", "setup.py"}


def test_ensure_requested_files_planned_noop_when_all_covered(workspace):
    """No extra milestone when every requested file is already a build target."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.frame.task_description = "Create exactly these files: src/app.py."
    planner = orch.planner_agent
    milestones = [{"name": "app", "files": [{"path": "src/app.py", "change_description": "app"}], "tests": []}]
    out = planner._ensure_requested_files_planned(milestones, workspace)
    assert [m["name"] for m in out] == ["app"]


def test_milestone_uses_tighter_step_budget():
    """Milestone mode must use the smaller per-file step budget."""
    from agent.agents.coder import AgentConfig
    assert AgentConfig.MILESTONE_SUBTASK_STEPS < AgentConfig.MAX_SUBTASK_STEPS


@pytest.mark.asyncio
async def test_milestone_skips_already_satisfied_on_retry(workspace):
    """A milestone whose files exist AND scoped tests pass is skipped (not rebuilt)."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    orch.fsm.state = AgentState.EXECUTING
    # Two milestones: 'done' (files already on disk, tests pass) and 'todo' (must build).
    (workspace / "done.py").write_text("x = 1\n")
    orch.frame.metadata["milestones"] = [
        {"name": "done", "files": [{"path": "done.py", "change_description": "c", "is_new": False}],
         "tests": ["tests/test_done.py"]},
        {"name": "todo", "files": [{"path": "todo.py", "change_description": "c", "is_new": True}],
         "tests": ["tests/test_todo.py"]},
    ]
    built = []
    async def fake_build(item, lesson, max_steps=None):
        built.append(item["path"])
        (orch.workspace / item["path"]).write_text("y = 1\n")
    orch.coder_agent._build_file = fake_build

    # 'done' pre-verify passes -> skipped; 'todo' has no file yet -> built then verified ok.
    async def fake_verify(tests):
        return (tests == ["tests/test_done.py"], "1 passed, 0 failed, 0 skipped", [], False)
    orch.coder_agent._verify_scope = fake_verify

    await orch.coder_agent.execute()
    assert "done.py" not in built            # already satisfied -> skipped
    assert "todo.py" in built                # not satisfied -> built
    assert orch.fsm.state == AgentState.EVALUATING
