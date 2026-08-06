"""Semantic Diff: validate generated code against NL spec requirements.

Each :class:`SpecPattern` pairs a spec trigger (regex) with a structural AST
check.  The checker scans the workspace for patterns the spec explicitly
requires and reports discrepancies as issues.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple


# ── helpers ──────────────────────────────────────────────────────────────

def _py_files(workspace: Path) -> List[Path]:
    return [p for p in workspace.rglob("*.py") if "__pycache__" not in p.parts]


def _parse(path: Path) -> Optional[ast.AST]:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return None


def _find_calls(tree: ast.AST, target_attr: Optional[str] = None,
                target_func: Optional[str] = None) -> List[ast.Call]:
    """Find ``ast.Call`` nodes matching an attribute or function name."""
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if target_attr and isinstance(node.func, ast.Attribute) and node.func.attr == target_attr:
            results.append(node)
        if target_func and isinstance(node.func, ast.Name) and node.func.id == target_func:
            results.append(node)
    return results


def _has_import(tree: ast.AST, module: str, name: Optional[str] = None) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if name is None:
                return True
            if any(a.name == name for a in node.names):
                return True
        if isinstance(node, ast.Import):
            if any(a.name == module for a in node.names):
                return True
    return False


def _find_decorators(tree: ast.AST, attr: str) -> List[str]:
    """Return names of functions decorated with ``@<attr>``."""
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if isinstance(deco, ast.Attribute) and deco.attr == attr:
                names.append(node.name)
            elif isinstance(deco, ast.Name) and deco.id == attr:
                names.append(node.name)
    return names


# ── pattern definitions ──────────────────────────────────────────────────

CheckFn = Callable[[Path, str], List[str]]


@dataclass
class SpecPattern:
    trigger: re.Pattern
    check: CheckFn
    description: str = ""
    severity: str = "error"


def _check_404(spec_text: str, workspace: Path) -> List[str]:
    """Return 404 if not found → check for HTTPException(404) or status_code=404."""
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        has_404 = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "HTTPException":
                    for kw in node.keywords:
                        if kw.arg == "status_code" and _is_int(kw.value, 404):
                            has_404 = True
                        if kw.arg is None and _is_int(kw.value, 404):
                            has_404 = True
                if isinstance(func, ast.Attribute) and func.attr in ("Response", "JSONResponse"):
                    for kw in node.keywords:
                        if kw.arg == "status_code" and _is_int(kw.value, 404):
                            has_404 = True
            if isinstance(node, ast.Attribute) and node.attr == "HTTPException":
                # imported name reference
                pass
            # Check for raise HTTPException pattern
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                exc_func = node.exc.func
                if isinstance(exc_func, ast.Name) and exc_func.id == "HTTPException":
                    for kw in node.exc.keywords:
                        if kw.arg == "status_code" and _is_int(kw.value, 404):
                            has_404 = True
        if not has_404:
            # Check if this file deals with task lookup
            content = py.read_text(encoding="utf-8", errors="replace")
            if any(kw in content.lower() for kw in ("get_task", "task_id", "not found")):
                issues.append(f"{rel}: spec requires 404 response for missing resources but no `HTTPException(404)` found")
    return issues


def _is_int(node: ast.AST, val: int) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and node.value == val


def _check_status_code(spec_text: str, workspace: Path, code: int,
                       trigger_words: Tuple[str, ...]) -> List[str]:
    issues = []
    method_lines: List[str] = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        content = py.read_text(encoding="utf-8", errors="replace")
        if not any(w in content.lower() for w in trigger_words):
            continue
        rel = str(py.relative_to(workspace))
        has_code = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                exc_func = node.exc.func
                if isinstance(exc_func, ast.Name) and exc_func.id == "HTTPException":
                    for kw in node.exc.keywords:
                        if kw.arg == "status_code" and _is_int(kw.value, code):
                            has_code = True
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, (ast.Attribute, ast.Name)):
                    pass
                for kw in node.keywords:
                    if kw.arg == "status_code" and _is_int(kw.value, code):
                        has_code = True
                for arg in node.args:
                    if _is_int(arg, code) and isinstance(node.func, ast.Attribute) and node.func.attr in ("json", "Response", "JSONResponse", "HTMLResponse", "PlainTextResponse"):
                        has_code = True
        if not has_code:
            issues.append(f"{rel}: spec requires status code {code} for {', '.join(trigger_words)} but not found")
    return issues


def _check_201(spec_text: str, workspace: Path) -> List[str]:
    return _check_status_code(spec_text, workspace, 201, ("201", "created", "post"))


def _check_204(spec_text: str, workspace: Path) -> List[str]:
    return _check_status_code(spec_text, workspace, 204, ("204", "no content", "delete"))


def _check_403(spec_text: str, workspace: Path) -> List[str]:
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        content = py.read_text(encoding="utf-8", errors="replace")
        rel = str(py.relative_to(workspace))
        has_403 = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                exc_func = node.exc.func
                if isinstance(exc_func, ast.Name) and exc_func.id == "HTTPException":
                    for kw in node.exc.keywords:
                        if kw.arg == "status_code" and _is_int(kw.value, 403):
                            has_403 = True
                if isinstance(exc_func, ast.Attribute):
                    pass
        if "auth" in content.lower() or "forbidden" in content.lower() or "api_key" in content.lower() or "x-api-key" in content.lower():
            if not has_403:
                issues.append(f"{rel}: spec requires 403 Forbidden for auth failures but not found")
    return issues


def _check_route_prefix(spec_text: str, workspace: Path) -> List[str]:
    """Routes must use a specific prefix like /tasks."""
    m = re.search(r'under\s+(\/[\w/]+)\s+prefix|prefix\s+(\/[\w/]+)', spec_text, re.IGNORECASE)
    if not m:
        m = re.search(r'ALL under\s+(\/[\w/]+)', spec_text, re.IGNORECASE)
    if not m:
        return []
    prefix = m.group(1) or m.group(2)
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in ("get", "post", "put", "patch", "delete", "options", "head"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("/") and not arg.value.startswith(prefix):
                        issues.append(
                            f"{rel}: route '{node.func.attr.upper()} {arg.value}' "
                            f"does not start with required prefix '{prefix}'"
                        )
    return issues


def _check_skip_limit(spec_text: str, workspace: Path) -> List[str]:
    """Check for pagination params skip/limit in list endpoints."""
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name in ("list", "get_tasks", "get_items", "list_tasks", "search"):
                arg_names = {a.arg for a in node.args.args if isinstance(a, ast.arg)}
                if "skip" not in arg_names or "limit" not in arg_names:
                    issues.append(
                        f"{rel}: `{node.name}` should have `skip` and `limit` "
                        f"parameters for pagination"
                    )
    return issues


def _check_model_fields(spec_text: str, workspace: Path) -> List[str]:
    """Check that Pydantic/SQLAlchemy models define required fields."""
    # Extract field names from spec: "fields: id (int, ...), title (str, ...), ..."
    field_section = re.search(r'(?:fields?|columns?):\s*(.+?)(?:\.\s|$|\n\n)',
                              spec_text, re.IGNORECASE | re.DOTALL)
    if not field_section:
        return []
    required_fields: Set[str] = set()
    for m in re.finditer(r'(\w+)\s*\(', field_section.group(1)):
        required_fields.add(m.group(1))
    if not required_fields:
        return []

    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        content = py.read_text(encoding="utf-8", errors="replace").lower()
        if not any(c in content for c in ("model", "base", "declarative")):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # Check if it's a model (inherits from something with Model/Base)
            base_names = set()
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_names.add(base.id)
                elif isinstance(base, ast.Attribute):
                    base_names.add(base.attr)
            if not any("model" in b.lower() or "base" in b.lower() for b in base_names):
                continue
            class_fields: Set[str] = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    class_fields.add(item.target.id)
                if isinstance(item, ast.Assign):
                    for t in item.targets:
                        if isinstance(t, ast.Name):
                            class_fields.add(t.id)
                if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
                    call = item.value
                    if isinstance(call.func, ast.Name) and call.func.id in ("Column", "Field"):
                        for kw in call.keywords:
                            if kw.arg is None and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                class_fields.add(kw.value.value)
                        for arg in call.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                class_fields.add(arg.value)
            missing = required_fields - class_fields
            if missing:
                issues.append(
                    f"{rel}: model `{node.name}` missing spec-required fields: "
                    f"{', '.join(sorted(missing))}"
                )
    return issues


def _check_enum_values(spec_text: str, workspace: Path) -> List[str]:
    """Check enum has required values."""
    m = re.search(r'enum:\s*["\']([^"\']+)["\']', spec_text, re.IGNORECASE)
    if not m:
        m = re.search(r'enum[:\s]+([\w_,\s]+?)(?:,|\.|$)', spec_text, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    expected = {v.strip().strip('"').strip("'") for v in raw.replace('"', '').replace("'", '').split(",") if v.strip()}
    if not expected:
        return []
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
                if base_name not in ("Enum", "StrEnum", "IntEnum"):
                    continue
                defined = set()
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for t in item.targets:
                            if isinstance(t, ast.Name) and not t.id.startswith("_"):
                                defined.add(t.id)
                missing = expected - defined
                if missing:
                    issues.append(
                        f"{rel}: enum `{node.name}` missing spec-required values: "
                        f"{', '.join(sorted(missing))}"
                    )
    return issues


def _check_max_length(spec_text: str, workspace: Path) -> List[str]:
    """Check for max_length constraint on string fields."""
    m = re.search(r'max\s*(\d+)\s*char', spec_text, re.IGNORECASE)
    if not m:
        return []
    max_val = int(m.group(1))
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        has_maxlen = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name in ("String", "str", "Column", "Field", "Annotated"):
                    for kw in node.keywords:
                        if kw.arg in ("max_length", "length") and _is_int(kw.value, max_val):
                            has_maxlen = True
                    for arg in node.args:
                        if isinstance(arg, ast.Call):
                            pass
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "Field":
                    for kw in node.keywords:
                        if kw.arg == "max_length" and _is_int(kw.value, max_val):
                            has_maxlen = True
        if not has_maxlen:
            content = py.read_text(encoding="utf-8", errors="replace").lower()
            if "title" in content or "name" in content or "string" in content:
                issues.append(f"{rel}: spec requires max_length={max_val} on string fields but not found")
    return issues


def _check_async(spec_text: str, workspace: Path) -> List[str]:
    """Check that CRUD/database functions are async when spec requires it."""
    if not re.search(r'\basync\b', spec_text, re.IGNORECASE):
        return []
    issues = []
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        rel = str(py.relative_to(workspace))
        content = py.read_text(encoding="utf-8", errors="replace").lower()
        if not any(w in content for w in ("db", "session", "crud", "database", "engine", "select", "execute")):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            # Check functions that are likely DB operations
            if any(kw in node.name.lower() for kw in ("create", "get_", "update", "delete", "list", "db")):
                if not isinstance(node, ast.AsyncFunctionDef):
                    issues.append(
                        f"{rel}: `{node.name}` should be async (spec requires async SQLAlchemy)"
                    )
    return issues


def _check_auth_header(spec_text: str, workspace: Path) -> List[str]:
    """Check for X-API-Key header auth dependency."""
    if not re.search(r'x-api-key|x_api_key|api.key.header', spec_text, re.IGNORECASE):
        return []
    issues = []
    found = False
    for py in _py_files(workspace):
        content = py.read_text(encoding="utf-8", errors="replace")
        if "X-API-Key" in content or "x_api_key" in content or "api_key" in content.lower():
            found = True
        tree = _parse(py)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "Header":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "api" in arg.value.lower():
                            found = True
    if not found:
        issues.append("spec requires X-API-Key header authentication but no auth-by-header logic found in workspace")
    return issues


def _check_sqlite_file(spec_text: str, workspace: Path) -> List[str]:
    """Check DB is file-based SQLite, not in-memory."""
    if not re.search(r'file.based|not.*in.memory|sqlite.*file|sqlite.*//', spec_text, re.IGNORECASE):
        return []
    issues = []
    for py in _py_files(workspace):
        content = py.read_text(encoding="utf-8", errors="replace").lower()
        if "sqlite" not in content:
            continue
        rel = str(py.relative_to(workspace))
        if ":memory:" in content:
            issues.append(f"{rel}: spec requires file-based SQLite but found `:memory:` instead")
    return issues


def _check_cli_entry(spec_text: str, workspace: Path) -> List[str]:
    """Check for CLI entry point (argparse, typer, click, if __name__)."""
    if not re.search(r'\bcli\b|argparse|command.line|entry.point|console_scripts',
                     spec_text, re.IGNORECASE):
        return []
    issues = []
    found = False
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        content = py.read_text(encoding="utf-8", errors="replace")
        if "if __name__ == '__main__'" in content or "argparse" in content:
            found = True
            break
        if _has_import(tree, "argparse") or _has_import(tree, "typer") or _has_import(tree, "click"):
            found = True
            break
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "add_parser":
                    found = True
                    break
            if isinstance(node, ast.FunctionDef) and "main" in node.name.lower():
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Name) and deco.id in ("app", "click", "command"):
                        found = True
                        break
    if not found:
        issues.append("spec requires a CLI entry point but no argparse/typer/click or `if __name__` found")
    return issues


def _check_exception_handlers(spec_text: str, workspace: Path) -> List[str]:
    """Check for custom exception handlers."""
    if not re.search(r'exception.handl(?:er|ing)', spec_text, re.IGNORECASE):
        return []
    issues = []
    found = False
    for py in _py_files(workspace):
        tree = _parse(py)
        if tree is None:
            continue
        content = py.read_text(encoding="utf-8", errors="replace")
        if "exception_handler" in content or "add_exception_handler" in content:
            found = True
            break
    if not found:
        issues.append("spec requires exception handlers but no `exception_handler` found")
    return issues


def _check_db_engine_url(spec_text: str, workspace: Path) -> List[str]:
    """Check DATABASE_URL or similar config is loaded from env/.env."""
    if not re.search(r'database_url|DATABASE_URL|\.env|environment', spec_text, re.IGNORECASE):
        return []
    issues = []
    found = False
    for py in _py_files(workspace):
        content = py.read_text(encoding="utf-8", errors="replace")
        if "DATABASE_URL" in content or "database_url" in content:
            if "env" in content.lower() or "environ" in content or "settings" in content.lower():
                found = True
                break
    if not found:
        issues.append("spec requires DATABASE_URL loaded from environment/.env but not found")
    return issues


# ── registry ─────────────────────────────────────────────────────────────

PATTERNS: List[SpecPattern] = [
    SpecPattern(
        trigger=re.compile(r'404|not.?found', re.IGNORECASE),
        check=_check_404,
        description="404 response for missing resources",
    ),
    SpecPattern(
        trigger=re.compile(r'201|Return.*201|POST.*creates?', re.IGNORECASE),
        check=_check_201,
        description="201 Created for POST operations",
    ),
    SpecPattern(
        trigger=re.compile(r'204|no.?content|delete.*return', re.IGNORECASE),
        check=_check_204,
        description="204 No Content for DELETE operations",
    ),
    SpecPattern(
        trigger=re.compile(r'403|forbidden|unauthorized', re.IGNORECASE),
        check=_check_403,
        description="403 Forbidden for auth failures",
    ),
    SpecPattern(
        trigger=re.compile(r'prefix|all under', re.IGNORECASE),
        check=_check_route_prefix,
        description="Route prefix consistency",
    ),
    SpecPattern(
        trigger=re.compile(r'skip.*limit|pagination|paginate', re.IGNORECASE),
        check=_check_skip_limit,
        description="Pagination skip/limit parameters",
    ),
    SpecPattern(
        trigger=re.compile(r'model.*fields|fields?:|columns?:', re.IGNORECASE),
        check=_check_model_fields,
        description="Required model fields",
    ),
    SpecPattern(
        trigger=re.compile(r'enum', re.IGNORECASE),
        check=_check_enum_values,
        description="Enum values",
    ),
    SpecPattern(
        trigger=re.compile(r'max.*\d+.*char', re.IGNORECASE),
        check=_check_max_length,
        description="Max length constraint on string fields",
    ),
    SpecPattern(
        trigger=re.compile(r'\basync\b', re.IGNORECASE),
        check=_check_async,
        description="Async functions for DB operations",
    ),
    SpecPattern(
        trigger=re.compile(r'x-api-key|x_api_key|api.key.header', re.IGNORECASE),
        check=_check_auth_header,
        description="X-API-Key header authentication",
    ),
    SpecPattern(
        trigger=re.compile(r'file.based|not.*in.memory|sqlite.*file', re.IGNORECASE),
        check=_check_sqlite_file,
        description="File-based SQLite (not :memory:)",
    ),
    SpecPattern(
        trigger=re.compile(r'\bcli\b|argparse|command.line|entry.point', re.IGNORECASE),
        check=_check_cli_entry,
        description="CLI entry point",
    ),
    SpecPattern(
        trigger=re.compile(r'exception.handl(?:er|ing)', re.IGNORECASE),
        check=_check_exception_handlers,
        description="Exception handlers",
    ),
    SpecPattern(
        trigger=re.compile(r'database_url|\.env|environment', re.IGNORECASE),
        check=_check_db_engine_url,
        description="DATABASE_URL from environment",
    ),
]


# ── public API ───────────────────────────────────────────────────────────

def run_semantic_diff(spec_text: str, workspace: Path) -> List[str]:
    """Run all triggered semantic checks against the workspace."""
    issues: List[str] = []
    for pattern in PATTERNS:
        if pattern.trigger.search(spec_text):
            try:
                found = pattern.check(spec_text, workspace)
                issues.extend(found)
            except Exception as exc:
                issues.append(f"[semantic-diff] {pattern.description} check failed: {exc}")
    return issues


def format_semantic_issues(issues: List[str]) -> str:
    if not issues:
        return ""
    lines = [
        "SEMANTIC DIFF ISSUES (NL spec → code comparison):",
        "The following spec requirements were not matched structurally in the generated code:",
    ]
    for i, issue in enumerate(issues, 1):
        lines.append(f"  {i}. {issue}")
    lines.append(
        "Fix each issue so the code matches the spec's structural requirements."
    )
    return "\n".join(lines)
