import pytest
from agent.orchestrator import Orchestrator


def test_required_exports_extracts_test_imports(workspace):
    """#2 scaffolding: the names tests import from a module become its required interface."""
    (workspace / "src" / "models").mkdir(parents=True)
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_users.py").write_text(
        "from src.models.user import User, UserCreate, Token\n"
        "def test_u(): assert User\n"
    )
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    got = orch.coder_agent._required_exports("src/models/user.py")
    assert got == ["Token", "User", "UserCreate"]
    # a module nothing imports from -> no required interface
    assert orch.coder_agent._required_exports("src/unused.py") == []
    # non-python -> empty
    assert orch.coder_agent._required_exports("README.md") == []


def test_relevant_references_opt_in_and_keyword_matched(workspace):
    """#3 example-RAG: references under .agent/references/ are matched by keyword, opt-in."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", milestones=True)
    # No references dir -> empty (fully opt-in, no behavior change)
    assert orch.coder_agent._relevant_references("src/services/auth_service.py", "JWT auth service") == ""

    refs = workspace / ".agents" / "references"
    refs.mkdir(parents=True)
    (refs / "auth_service_example.py").write_text("class AuthService:\n    def authenticate(self): ...\n")
    (refs / "unrelated_math.py").write_text("def add(a, b): return a + b\n")

    out = orch.coder_agent._relevant_references("src/services/auth_service.py", "JWT auth service")
    assert "auth_service_example.py" in out          # keyword-matched reference injected
    assert "reference:" in out
    assert "unrelated_math" not in out               # irrelevant reference not injected
