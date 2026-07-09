"""Shared pytest fixtures."""
import sys
from pathlib import Path

import pytest

# Ensure `src` is importable even when the package isn't pip-installed.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def policy(workspace, tmp_path):
    from agent.guardrails.policy import SecurityPolicy

    return SecurityPolicy(workspace, interactive=False, log_dir=tmp_path / "logs")


@pytest.fixture
def local_sandbox(workspace):
    from agent.sandbox.config import SandboxConfig
    from agent.sandbox.manager import SandboxManager

    mgr = SandboxManager(SandboxConfig(workspace=workspace, backend="local"))
    mgr.start()
    yield mgr
    mgr.stop()
