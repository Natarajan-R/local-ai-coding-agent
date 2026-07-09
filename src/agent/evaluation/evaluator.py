"""Evaluate the workspace by running its tests, detecting the project type.

Detection order (first match wins):
  1. An explicit ``test_command`` (from ``--test-command``).
  2. A recognized project marker file (package.json, go.mod, Cargo.toml, ...).
  3. Python test files (``test_*.py`` / ``*_test.py``) -> pytest.
  4. Otherwise a best-effort Python compile check.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# pytest exit code returned when no tests were collected.
PYTEST_NO_TESTS = 5

# (marker file, test command). Checked in order.
PROJECT_MARKERS: List[Tuple[str, str]] = [
    ("package.json", "npm test --silent"),
    ("go.mod", "go test ./..."),
    ("Cargo.toml", "cargo test"),
    ("pom.xml", "mvn -q test"),
    ("build.gradle", "gradle test"),
    ("build.gradle.kts", "gradle test"),
]


@dataclass
class EvalResult:
    passed: bool
    summary: str
    details: str = ""
    ran_tests: bool = False


class Evaluator:
    """Run tests inside the sandbox and interpret the outcome.

    ``test_command`` overrides all detection; when set it is always used.
    """

    def __init__(self, sandbox, policy, test_command: Optional[str] = None) -> None:
        self.sandbox = sandbox
        self.policy = policy
        self.test_command = test_command

    # -- detection -----------------------------------------------------------
    def _has_python_tests(self, workspace: Path) -> bool:
        for pattern in ("test_*.py", "*_test.py"):
            for p in workspace.rglob(pattern):
                if not {".venv", "venv"} & set(p.parts):
                    return True
        return False

    def _detect_command(self, workspace: Path) -> Optional[str]:
        if self.test_command:
            return self.test_command
        for marker, command in PROJECT_MARKERS:
            if (workspace / marker).exists():
                return command
        if self._has_python_tests(workspace):
            return "python -m pytest -q"
        return None

    # -- evaluation ----------------------------------------------------------
    def evaluate(self, workspace: Path) -> EvalResult:
        workspace = Path(workspace)
        command = self._detect_command(workspace)
        if command is None:
            return self._syntax_check(workspace)

        result = self.sandbox.exec(command)
        output = self.policy.scrub(result.output)

        # pytest exits 5 when no tests are collected; treat as "no tests".
        if command.startswith("python -m pytest") and result.exit_code == PYTEST_NO_TESTS:
            return self._syntax_check(workspace)

        if result.ok:
            return EvalResult(True, f"Tests passed ({command})", output, ran_tests=True)
        if result.timed_out:
            return EvalResult(False, f"Tests timed out ({command})", output, ran_tests=True)
        return EvalResult(False, f"Tests failed ({command})", output, ran_tests=True)

    def _syntax_check(self, workspace: Path) -> EvalResult:
        result = self.sandbox.exec("python -m compileall -q .")
        output = self.policy.scrub(result.output)
        if result.ok:
            return EvalResult(True, "No tests found; sources compile cleanly", output)
        return EvalResult(False, "Syntax errors detected", output)
