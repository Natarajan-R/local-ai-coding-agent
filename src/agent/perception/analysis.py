"""Static analysis of edits using Python's AST.

This gives the agent an immediate, dependency-free feedback signal: when it
writes or edits a Python file, we parse the result and surface any syntax error
right in the tool result, instead of waiting for the evaluation phase. This is
the lightweight, local-first cousin of an LSP "diagnostics" capability.
"""
from __future__ import annotations

import ast
from typing import List

# Extensions we can validate with the standard-library parser.
PYTHON_EXTENSIONS = (".py", ".pyi")


def python_syntax_errors(source: str, filename: str = "<edit>") -> List[str]:
    """Return a list of human-readable syntax errors (empty if valid)."""
    try:
        ast.parse(source, filename=filename)
        return []
    except SyntaxError as exc:
        where = f"line {exc.lineno}"
        if exc.offset:
            where += f", col {exc.offset}"
        return [f"{exc.msg} ({where})"]


def is_python_file(path: str) -> bool:
    return path.lower().endswith(PYTHON_EXTENSIONS)


def syntax_note(path: str, content: str) -> str:
    """Return a warning string for a Python file with a syntax error, else ''.

    Non-Python files are skipped. The message is written to be actionable for
    the model.
    """
    if not is_python_file(path):
        return ""
    errors = python_syntax_errors(content, filename=path)
    if not errors:
        return ""
    return "\n[warning] Python syntax error introduced: " + "; ".join(errors)
