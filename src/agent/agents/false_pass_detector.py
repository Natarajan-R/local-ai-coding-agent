"""False-pass detection: analyse test assertions for structural bugs.

Tests can report ``pass`` even when they test the wrong thing.  This module
scans test ASTs for common assertion anti-patterns observed in the demo runs.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Optional, Set


def _py_files(workspace: Path) -> List[Path]:
    return [p for p in workspace.rglob("*.py") if "__pycache__" not in p.parts]


def _test_files(workspace: Path) -> List[Path]:
    return [
        p for p in _py_files(workspace)
        if "test" in p.stem or "test" in str(p.parent.relative_to(workspace))
    ]


def _parse(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return None


# ── check: .lower() compared against non-lowercase constant ──────────────

def _check_case_after_lower(tree: ast.AST, rel: str) -> List[str]:
    """Detect ``x.lower() == 'True'`` — impossible after .lower() does 'true'."""
    issues: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            continue
        left = node.left
        if not isinstance(left, ast.Call):
            continue
        if not isinstance(left.func, ast.Attribute) or left.func.attr != "lower":
            continue
        if not left.args and not left.keywords:  # .lower() has no args
            for comp in node.comparators:
                if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    if comp.value != comp.value.lower():
                        # .lower() always produces lowercase; comparing against
                        # a non-lower string means this assertion can NEVER be True.
                        issues.append(
                            f"{rel}:{node.lineno}: `.lower()` compared against "
                            f"'{comp.value}' — .lower() always produces lowercase, "
                            f"so '{comp.value}' can never match. "
                            f"Compare against '{comp.value.lower()}' instead."
                        )
    return issues


# ── check: exception test with patched input ─────────────────────────────

_EASY_INPUT_PATTERNS = [
    re.compile(r"<[a-z]+[^>]*>", re.IGNORECASE),          # <body> — well-formed
    re.compile(r"<[a-z]+/>", re.IGNORECASE),               # <br/> — self-closing
    re.compile(r"&\w+;", re.IGNORECASE),                   # &amp; — entity
    re.compile(r"^[A-Za-z0-9\s.,!?;:'\"-]+$"),            # plain text (no html)
]


def _is_likely_well_formed(s: str) -> bool:
    """Heuristic: if the string contains HTML-ish content that's well-formed."""
    s_stripped = s.strip()
    if not s_stripped.startswith("<"):
        return True  # No angle brackets = plain text, not malformed
    # Check common malformed-HTML signals
    if "<" in s_stripped and ">" not in s_stripped:
        return False  # e.g. "<bod" — unclosed opening tag
    if re.search(r"<[^>]*[^/]>", s_stripped) and not re.search(r"</", s_stripped):
        # Opening tag present but no closing tag and not self-closing
        if re.search(r"<[a-z]+\s", s_stripped) or re.search(r"<[a-z]+>", s_stripped):
            pass  # Could be well-formed if there's a closing tag somewhere
    return True


def _check_exception_test_mismatch(tree: ast.AST, rel: str) -> List[str]:
    """Detect tests that expect an exception but the input appears well-formed."""
    issues: List[str] = []
    # Walk With blocks, check if they use pytest.raises or context manager
    for with_node in ast.walk(tree):
        if not isinstance(with_node, ast.With):
            continue
        # Identify the context manager call
        exc_call = None
        exc_name = ""
        for item in with_node.items:
            expr = item.context_expr
            if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Attribute):
                continue
            if expr.func.attr not in ("raises", "pytest.raises"):
                continue
            exc_call = expr
            if expr.args and isinstance(expr.args[0], (ast.Name, ast.Attribute)):
                first = expr.args[0]
                if isinstance(first, ast.Name):
                    exc_name = first.id
                elif isinstance(first, ast.Attribute):
                    exc_name = first.attr
            break
        if exc_call is None:
            continue
        # Scan the body of the with block for calls with string arguments
        for stmt in with_node.body:
            for call_node in ast.walk(stmt):
                if not isinstance(call_node, ast.Call):
                    continue
                for arg in call_node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        val: str = arg.value
                        if not _is_likely_well_formed(val):
                            continue
                        issues.append(
                            f"{rel}:{exc_call.lineno}: test expects {exc_name} "
                            f"but input '{val[:60]}' appears well-formed. "
                            f"Use input the parser actually rejects."
                        )
    return issues


# ── check: always-true assertions ────────────────────────────────────────

_TAUTOLOGIES = {
    "True", "False", "None",
}

_TRUTHY_LITERALS = {1, "True", "False", "None"}
_FALSY_LITERALS = {0, "", "''", '""', "[]", "{}", "None"}


def _check_always_true_assertions(tree: ast.AST, rel: str) -> List[str]:
    """Detect ``assert True`` or ``assert x == x`` — can never fail."""
    issues: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test

        # assert True / assert False / assert None
        if isinstance(test, ast.Constant):
            if test.value is True:
                issues.append(
                    f"{rel}:{node.lineno}: `assert True` always passes — "
                    f"this assertion tests nothing."
                )
            elif test.value is False:
                issues.append(
                    f"{rel}:{node.lineno}: `assert False` always fails — "
                    f"this assertion is dead code."
                )

        # assert x == x  (same Name on both sides)
        if isinstance(test, ast.Compare) and len(test.comparators) == 1:
            left = test.left
            right = test.comparators[0]
            if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                if left.id == right.id:
                    issues.append(
                        f"{rel}:{node.lineno}: `assert {left.id} == {right.id}` "
                        f"always passes — comparing a variable to itself."
                    )
            # assert literal == literal
            if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
                issues.append(
                    f"{rel}:{node.lineno}: `assert {left.value!r} == {right.value!r}` "
                    f"compares two literals — always the same result."
                )

        # assert "constant string" (truthy)
        if isinstance(test, ast.Constant) and isinstance(test.value, str) and test.value:
            # Check it's not being used as a message (assert 0, "msg")
            # If there's no msg, a bare string literal assertion is suspicious
            if node.msg is None:
                issues.append(
                    f"{rel}:{node.lineno}: assert on string literal "
                    f"'{test.value[:40]}' always passes (truthy). "
                    f"Use an actual condition."
                )

    return issues


# ── check: self-assert (assert x, where x is a function call that might fail) ──
# ── check: assert on a mutable that was just mutated in place ───────────


def _check_mutation_after_assert(tree: ast.AST, rel: str) -> List[str]:
    """Flag tests that mutate an object then assert the mutation had no effect.

    E.g. ``items.sort(); assert items == sorted(items)`` — sort is in-place.
    """
    issues: List[str] = []
    # Walk pairs of statements in each function body looking for
    # mutation-call followed by reverse-assertion
    for func_node in ast.walk(tree):
        if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = func_node.body
        for i in range(len(body) - 1):
            curr = body[i]
            next_st = body[i + 1]
            # Look for: x.method() then assert x == sorted(x) or similar
            if not isinstance(curr, ast.Expr):
                continue
            curr_call = curr.value
            if not isinstance(curr_call, ast.Call):
                continue
            if not isinstance(curr_call.func, ast.Attribute):
                continue
            mut_method = curr_call.func.attr
            # In-place mutation methods
            if mut_method not in ("sort", "reverse", "append", "extend", "clear",
                                  "pop", "remove", "insert", "add", "discard",
                                  "update", "difference_update"):
                continue
            if not isinstance(next_st, ast.Assert):
                continue
            # Extract the object being mutated
            if not isinstance(curr_call.func.value, ast.Name):
                continue
            obj_name = curr_call.func.value.id
            # Check the assert re-reads the same object
            for ass_node in ast.walk(next_st.test):
                if isinstance(ass_node, ast.Name) and ass_node.id == obj_name:
                    issues.append(
                        f"{rel}:{curr.lineno}: `{obj_name}.{mut_method}()` "
                        f"mutates in place on line {curr.lineno}, then "
                        f"`{obj_name}` is re-asserted on line {next_st.lineno}. "
                        f"If the assertion expects the original value it will "
                        f"fail; if it expects the mutated value the assertion "
                        f"is redundant."
                    )
                    break
    return issues


# ── main entry point ─────────────────────────────────────────────────────

def run_false_pass_detection(workspace: Path) -> List[str]:
    """Scan all test files for assertion anti-patterns."""
    issues: List[str] = []
    for tf in _test_files(workspace):
        tree = _parse(tf)
        if tree is None:
            continue
        try:
            rel = str(tf.relative_to(workspace))
        except ValueError:
            continue
        issues.extend(_check_case_after_lower(tree, rel))
        issues.extend(_check_exception_test_mismatch(tree, rel))
        issues.extend(_check_always_true_assertions(tree, rel))
        issues.extend(_check_mutation_after_assert(tree, rel))
    return issues
