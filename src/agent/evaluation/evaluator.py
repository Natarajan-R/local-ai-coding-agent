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

# Cap on the failure detail fed back to the model. Small enough that it can never
# crowd out the rest of the context and get trimmed away.
FAILURE_DETAIL_LIMIT = 3000


def _extract_failures(output: str) -> str:
    if not output:
        return ""
    lines = output.splitlines()
    failures = []
    
    current_test = None
    current_error = []
    current_file_line = None
    
    in_failures = False
    
    for line in lines:
        if "FAILURES" in line and line.startswith("="):
            in_failures = True
            continue
        if in_failures and line.startswith("="):
            if any(word in line for word in ["FAILURES", "ERRORS"]):
                continue
            else:
                in_failures = False
                
        if in_failures:
            if line.startswith("___") and line.endswith("___"):
                if current_test:
                    failures.append((current_test, "\n".join(current_error), current_file_line))
                current_test = line.strip("_ ")
                current_error = []
                current_file_line = None
                continue
                
            if current_test:
                if line.startswith("E   "):
                    current_error.append(line)
                elif line.strip() and ":" in line and not line.startswith(" ") and not line.startswith("E") and not line.startswith(">"):
                    parts = line.strip().split(":")
                    if len(parts) >= 2 and parts[-2].strip().isdigit():
                        current_file_line = line.strip()
                        
    if current_test:
        failures.append((current_test, "\n".join(current_error), current_file_line))
        
    if not failures:
        return ""
        
    summary_lines = ["\n=== FAILURES SUMMARY ==="]
    for test, err, file_line in failures:
        summary_lines.append(f"FAILED TEST: {test}")
        if file_line:
            summary_lines.append(f"LOCATION: {file_line}")
        if err:
            summary_lines.append(f"ERROR DETAILS:\n{err}")
        summary_lines.append("")
    summary_lines.append("========================\n")
    return "\n".join(summary_lines)


def _condense_test_output(output: str, limit: int = FAILURE_DETAIL_LIMIT) -> str:
    """Keep the *diagnostic* part of a failed test run, drop the passing noise.

    A large suite dumps hundreds of lines of passing checks and framework headers
    into the result. Fed whole into the model's context, that noise pushes the
    real traceback toward the bottom — exactly where context trimming cuts — so
    the model sees only passing lines, believes its code is fine, and loops
    blindly. This keeps the pytest ``FAILURES``/``ERRORS`` section (which holds the
    ``E  assert ...`` lines and the short summary), and when it must cap, keeps the
    END, because pytest prints the summary last. Falls back to the failure-bearing
    lines, then the raw tail, for non-pytest runners.
    """
    if not output:
        return output
    
    summary = _extract_failures(output)
    
    lines = output.splitlines()
    start = next(
        (i for i, ln in enumerate(lines)
         if ln.startswith("=") and ("FAILURES" in ln or "ERRORS" in ln)),
        None,
    )
    if start is not None:
        condensed = "\n".join(lines[start:])
    else:
        keep = [
            ln for ln in lines
            if ln[:1] in ("E", ">")
            or ln.startswith(("FAILED", "ERROR", "Traceback"))
            or "Error" in ln or "assert" in ln
        ]
        condensed = "\n".join(keep) if keep else output
    if len(condensed) > limit:
        condensed = "...[earlier test output truncated]...\n" + condensed[-limit:]
        
    if summary:
        return summary + "\n" + condensed
    return condensed


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

    def __init__(
        self, sandbox, policy,
        test_command: Optional[str] = None,
        initial_test_files: Optional[List[str]] = None
    ) -> None:
        self.sandbox = sandbox
        self.policy = policy
        self.test_command = test_command
        self.initial_test_files = initial_test_files

    # -- detection -----------------------------------------------------------
    def _has_python_tests(self, workspace: Path) -> bool:
        if self.initial_test_files is not None:
            import os
            for f in self.initial_test_files:
                name = os.path.basename(f)
                if f.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")):
                    return True
            return False
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

        # Revert any modifications to initial test files to prevent tampering
        if self.initial_test_files is not None:
            for test_file in self.initial_test_files:
                self.sandbox.exec(f"git checkout -- {test_file}")

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
        # On failure, feed back the condensed diagnostic, not the whole scroll, so
        # the real traceback can't be crowded out and trimmed away downstream.
        if result.timed_out:
            return EvalResult(False, f"Tests timed out ({command})",
                              _condense_test_output(output), ran_tests=True)
        return EvalResult(False, f"Tests failed ({command})",
                          _condense_test_output(output), ran_tests=True)

    def _syntax_check(self, workspace: Path) -> EvalResult:
        result = self.sandbox.exec("python -m compileall -q .")
        output = self.policy.scrub(result.output)
        if result.ok:
            # Verify edits were actually made using git status.
            # Note: This check only applies inside Git repositories; non-Git workspaces fall back to passed.
            git_check = self.sandbox.exec("git status --porcelain")
            if git_check.exit_code == 0:
                git_lines = [
                    line for line in git_check.output.splitlines()
                    if "__pycache__" not in line and not line.strip().endswith(".pyc")
                ]
                if not git_lines:
                    return EvalResult(
                        False,
                        "No tests found, and no edits/mutations made to the workspace.",
                        "The original codebase compiles cleanly, but no modifications were detected. "
                        "An edit task requires modifying the codebase."
                    )
            return EvalResult(True, "No tests found; sources compile cleanly", output)
        return EvalResult(False, "Syntax errors detected", output)
