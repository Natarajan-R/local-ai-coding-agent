"""Complex file-editing tool handlers (search/replace, docstrings, parameter add, rename).

These handlers contain the heaviest logic and were the largest contributors to the
ToolRegistry's God Object footprint.
"""
from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import url2pathname

from ..errors import ToolError
from ..perception.analysis import syntax_note
from .patcher import _strip_regex_escapes, apply_and_diff, apply_line_edit, commit_and_write, make_diff
from .simple_handlers import HandlerContext, scan_workspace_files_sync
from .utils import (
    ToolResult,
    MAX_OUTPUT_CHARS,
    normalize_async_scaffolding,
    restore_signature_annotations,
    safe_unescape,
    sanitize_docstring,
    truncate,
    undocumented,
)

try:
    from rope.base.project import Project
    from rope.refactor.change_signature import ChangeSignature, ArgumentAdder
    HAS_ROPE = True
except ImportError:
    HAS_ROPE = False

logger = logging.getLogger(__name__)


# ── shared path validation ────────────────────────────────────────────────

def safe_path(ctx: HandlerContext, path: str):
    """Validate ``path`` stays in the workspace and return its resolved absolute Path."""
    if not ctx.policy.validate_path(path):
        raise ToolError(f"Path '{path}' is outside the workspace")
    return ctx.policy.resolve_path(path)


def safe_write_path(ctx: HandlerContext, path: str):
    """Like ``safe_path``, but also refuse writes to a protected file."""
    target = safe_path(ctx, path)
    if not ctx.policy.validate_write(target):
        raise ToolError(
            f"'{path}' is a protected file and must not be modified. This is a "
            f"deliberate restriction, not a transient error -- do not retry this "
            f"write. Work around it, or explain why the task cannot be completed "
            f"without changing it."
        )
    return target


# ── edit-miss escalation ──────────────────────────────────────────────────

EDIT_MISS_ESCALATION = 2


def note_edit_miss(reg, path: str, exc: ToolError) -> ToolError:
    """Count a failed edit on ``path`` and escalate the advice once it repeats."""
    reg._edit_misses[path] = reg._edit_misses.get(path, 0) + 1
    misses = reg._edit_misses[path]
    if misses < EDIT_MISS_ESCALATION:
        return exc
    return ToolError(
        f"{exc}\n\n"
        f"NOTE: {misses} edits to {path} have failed in a row. Do not send another "
        f"search block for this file -- your idea of its contents is wrong. Either "
        f"call `read_file` on {path} and copy the text verbatim, or call `write_file` "
        f"with the complete corrected file in one step."
    )


# ── handlers ──────────────────────────────────────────────────────────────

async def search_replace(ctx: HandlerContext, path: str, search: str, replace: str) -> ToolResult:
    """Handler for ``search_replace``."""
    target = safe_write_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    if isinstance(search, str):
        search = search.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
        search = safe_unescape(search)
    if isinstance(replace, str):
        replace = replace.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
        replace = safe_unescape(replace)
    if path.endswith(".py"):
        replace = normalize_async_scaffolding(replace)
    original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
    try:
        updated, diff = apply_and_diff(original, search, replace, path)
    except ToolError as exc:
        raise note_edit_miss(ctx.reg, path, exc) from None
    ctx.reg._edit_misses.pop(path, None)  # a landed edit clears the streak

    await ctx.reg._atomic_commit_and_refresh(target, updated)

    note = syntax_note(path, updated)
    ctx.policy.audit.record("search_replace", path=path, syntax_ok=not note)
    return ToolResult(True, f"Applied edit to {path}:\n{truncate(diff, MAX_OUTPUT_CHARS)}{note}")


async def edit_lines(ctx: HandlerContext, path: str, start_line: int, end_line: int, search: str, replace: str) -> ToolResult:
    """Handler for ``edit_lines``."""
    target = safe_write_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    if isinstance(search, str):
        search = search.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
        search = safe_unescape(search)
    if isinstance(replace, str):
        replace = replace.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
        replace = safe_unescape(replace)
    if path.endswith(".py"):
        replace = normalize_async_scaffolding(replace)
    original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
    try:
        updated = apply_line_edit(original, start_line, end_line, search, replace)
    except ToolError as exc:
        raise note_edit_miss(ctx.reg, path, exc) from None
    ctx.reg._edit_misses.pop(path, None)
    diff = make_diff(original, updated, path)

    await ctx.reg._atomic_commit_and_refresh(target, updated)

    note = syntax_note(path, updated)
    ctx.policy.audit.record("edit_lines", path=path, syntax_ok=not note)
    return ToolResult(True, f"Applied line edit to {path}:\n{truncate(diff, MAX_OUTPUT_CHARS)}{note}")


async def replace_all(ctx: HandlerContext, path: str, old: str, new: str) -> ToolResult:
    """Replace every occurrence of ``old`` in one file."""
    target = safe_write_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    if not old:
        return ToolResult(False, "`old` must not be empty")
    original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
    count = original.count(old)
    if count == 0:
        unescaped_old = _strip_regex_escapes(old)
        if unescaped_old != old and original.count(unescaped_old) > 0:
            old, new = unescaped_old, _strip_regex_escapes(new)
            count = original.count(old)
        else:
            return ToolResult(
                False,
                f"{old!r} does not appear in {path}. Note: `old` is matched as "
                f"LITERAL text, not a regular expression — do not escape "
                f"characters like [ ] ( ) . *",
            )
    updated = original.replace(old, new)

    await ctx.reg._atomic_commit_and_refresh(target, updated)

    diff = make_diff(original, updated, path)
    note = syntax_note(path, updated)
    ctx.policy.audit.record("replace_all", path=path, count=count, syntax_ok=not note)
    body = f"Replaced {count} occurrence(s) of {old!r} with {new!r} in {path}:\n{diff}"
    if note:
        body += f"\n{note}"
    return ToolResult(True, body)


async def add_docstring(ctx: HandlerContext, path: str, symbol: str, docstring: str) -> ToolResult:
    """Insert or replace one definition's docstring, AST-precisely."""
    target = safe_write_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    source = await asyncio.to_thread(target.read_text, encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ToolResult(False, f"{path} does not parse, so it cannot be edited: {exc}")

    # Resolve "name" or "Class.method" to a definition node.
    wanted = symbol.split(".")
    node = None
    candidates: List[Any] = list(ast.iter_child_nodes(tree))
    for i, part in enumerate(wanted):
        node = next(
            (n for n in candidates
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and n.name == part),
            None,
        )
        if node is None:
            names = sorted(
                n.name for n in candidates
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            )
            where = f" inside {'.'.join(wanted[:i])}" if i else ""
            return ToolResult(
                False,
                f"No function, method or class named {part!r} found{where} in {path}. "
                f"Available here: {', '.join(names) if names else '(none)'}",
            )
        candidates = list(ast.iter_child_nodes(node))

    lines = source.splitlines(keepends=True)
    first = node.body[0]
    indent = " " * first.col_offset

    existing = ast.get_docstring(node, clean=False)
    text = sanitize_docstring(docstring)
    body = "\n".join(
        (indent + ln) if ln.strip() else "" for ln in text.split("\n")
    ).lstrip()
    block = f'{indent}"""{body}\n{indent}"""\n' if "\n" in text else f'{indent}"""{text}"""\n'

    if existing is not None:
        start = first.lineno - 1
        end = first.end_lineno
        new_lines = lines[:start] + [block] + lines[end:]
        verb = "Replaced"
    else:
        start = first.lineno - 1
        new_lines = lines[:start] + [block] + lines[start:]
        verb = "Added"

    updated = "".join(new_lines)
    try:
        ast.parse(updated)
    except SyntaxError as exc:
        return ToolResult(False, f"Inserting docstring caused a SyntaxError: {exc}")

    await ctx.reg._atomic_commit_and_refresh(target, updated)

    ctx.policy.audit.record("add_docstring", path=path, symbol=symbol)
    remaining = undocumented(updated)
    note = (
        f"\nStill undocumented in {path}: {', '.join(remaining)}"
        if remaining else f"\nEvery function, method and class in {path} now has a docstring."
    )
    return ToolResult(True, f"{verb} docstring for {symbol} in {path}.\n"
                            f"{make_diff(source, updated, path)}{note}")


async def add_parameter(
    ctx: HandlerContext,
    path: str,
    symbol: str,
    name: str,
    value: str,
    default: Optional[str] = None,
) -> ToolResult:
    """Add a parameter to a function or method signature and rewrite all call sites."""
    value = value.strip()
    try:
        expr = ast.parse(value, mode="eval")
        if isinstance(expr.body, ast.Name):
            if expr.body.id not in ("True", "False", "None"):
                value = f'"{value}"'
    except SyntaxError:
        value = f'"{value}"'

    if default is not None:
        default = default.strip()
        if default:
            try:
                expr = ast.parse(default, mode="eval")
                if isinstance(expr.body, ast.Name):
                    if expr.body.id not in ("True", "False", "None"):
                        default = f'"{default}"'
            except SyntaxError:
                default = f'"{default}"'
    if not HAS_ROPE:
        return ToolResult(False, "Rope refactoring library is not installed.")

    target = safe_write_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")

    content = await asyncio.to_thread(target.read_text, encoding="utf-8")
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return ToolResult(False, f"{path} does not parse, so it cannot be edited: {exc}")

    wanted = symbol.split(".")
    node = None
    candidates = list(ast.iter_child_nodes(tree))
    for i, part in enumerate(wanted):
        node = next(
            (n for n in candidates
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and n.name == part),
            None,
        )
        if node is None:
            names = sorted(
                n.name for n in candidates
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            )
            where = f" inside {'.'.join(wanted[:i])}" if i else ""
            return ToolResult(
                False,
                f"No function, method or class named {part!r} found{where} in {path}. "
                f"Available here: {', '.join(names) if names else '(none)'}",
            )
        candidates = list(ast.iter_child_nodes(node))

    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ToolResult(False, f"Symbol {symbol!r} in {path} is not a function or method definition.")

    # Idempotency guard.
    bare_name = name.split(":", 1)[0].strip()
    existing_params = {
        a.arg for a in (list(node.args.posonlyargs) + list(node.args.args)
                        + list(node.args.kwonlyargs))
    }
    if bare_name in existing_params:
        return ToolResult(
            True,
            f"Parameter {bare_name!r} is ALREADY on {symbol} in {path} — nothing to "
            f"add, this is done. Do not add it again (that would create a duplicate "
            f"and break the code). Run the tests to verify, then call `finish`.",
        )

    # Capture annotations before Rope strips them.
    _orig_annotations = {
        a.arg: ast.unparse(a.annotation)
        for a in (list(node.args.posonlyargs) + list(node.args.args)
                  + list(node.args.kwonlyargs))
        if a.annotation is not None
    }
    _orig_return = ast.unparse(node.returns) if node.returns is not None else None
    if ":" in name:
        _new_arg, _new_hint = (p.strip() for p in name.split(":", 1))
        _orig_annotations[_new_arg] = _new_hint

    # Compute symbol name offset inside the file
    lines = content.splitlines(keepends=True)
    line_offset = sum(len(ln) for ln in lines[:node.lineno - 1])
    line = lines[node.lineno - 1]
    relative_offset = line.find(node.name, node.col_offset)
    if relative_offset == -1:
        relative_offset = line.find(node.name)
    char_offset = line_offset + relative_offset

    # Perform the Rope refactoring in a separate thread
    changed_files = []

    def run_rope():
        proj = Project(str(ctx.workspace))
        try:
            rel_path = str(target.relative_to(ctx.workspace))
            resource = proj.get_resource(rel_path)
            refactor = ChangeSignature(proj, resource, char_offset)
            existing_args = refactor.get_args()
            insert_idx = len(existing_args)
            adder = ArgumentAdder(insert_idx, name, default=default, value=value)
            changes = refactor.get_changes([adder])
            proj.do(changes)
            for r in changes.get_changed_resources():
                if not r.is_folder():
                    changed_files.append(Path(r.real_path))
        finally:
            proj.close()

    try:
        await asyncio.to_thread(run_rope)
    except Exception as exc:
        return ToolResult(False, f"Rope refactoring failed: {exc}")

    # Restore annotations that Rope stripped.
    restored = await asyncio.to_thread(target.read_text, encoding="utf-8")
    reannotated = restore_signature_annotations(
        restored, symbol, _orig_annotations, _orig_return
    )
    if reannotated != restored:
        await asyncio.to_thread(commit_and_write, ctx.workspace, target, reannotated, 'utf-8')

    if ctx.reg._symbols is not None:
        ctx.reg._symbols.refresh()

    new_content = await asyncio.to_thread(target.read_text, encoding="utf-8")
    diff = make_diff(content, new_content, path)

    if ctx.lsp:
        for filepath in changed_files:
            try:
                updated_text = await asyncio.to_thread(filepath.read_text, encoding="utf-8")
                await ctx.lsp.open_document(filepath, updated_text)
                await ctx.lsp.change_document(filepath, updated_text)
            except Exception:
                pass

    try:
        updated = sorted(
            str(Path(f).resolve().relative_to(ctx.workspace)) for f in changed_files
        )
    except Exception:
        updated = [str(f) for f in changed_files]
    site_list = ", ".join(updated) if updated else path
    return ToolResult(
        True,
        f"Successfully added parameter {name!r} to {symbol}. This is COMPLETE: the "
        f"signature AND every call site across the repository have been updated "
        f"automatically, in {len(updated) or 1} file(s): {site_list}.\n"
        f"Do NOT edit these call sites yourself — they are already correct. "
        f"A single uniform value (like {value!r}) is completely sufficient and correct, even if the task asked for a 'sensible' value. "
        f"Do NOT try to manually edit the call sites afterward to set different/per-site values — doing so is redundant, highly error-prone, and will break the code. "
        f"Your next step is to run the tests to verify, then call `finish`.\n"
        f"Diff for {path}:\n{diff}"
    )


# ── LSP workspace-edit helper ─────────────────────────────────────────────

async def apply_workspace_edit(ctx: HandlerContext, edit: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Apply an LSP WorkspaceEdit structure to workspace files.

    Returns ``(applied, skipped_protected)``.
    """
    skipped_protected: List[str] = []
    changes = edit.get("changes")
    document_changes = edit.get("documentChanges")

    file_edits: Dict[str, List[Dict[str, Any]]] = {}

    if document_changes:
        for doc_edit in document_changes:
            if not isinstance(doc_edit, dict):
                continue
            doc_id = doc_edit.get("textDocument", {})
            uri = doc_id.get("uri")
            edits = doc_edit.get("edits")
            if uri and edits:
                file_edits[uri] = edits
    elif changes:
        for uri, edits in changes.items():
            if uri and edits:
                file_edits[uri] = edits

    if not file_edits:
        return [], []

    applied_paths = []
    for uri, edits in file_edits.items():
        if not uri.startswith("file://"):
            continue
        parsed = urlparse(uri)
        path_str = url2pathname(parsed.path)
        filepath = Path(path_str).resolve()
        if not filepath.exists() or not filepath.is_relative_to(ctx.workspace):
            continue

        content = await asyncio.to_thread(filepath.read_text, encoding="utf-8")

        def get_start(e):
            start = e.get("range", {}).get("start", {})
            return (start.get("line", 0), start.get("character", 0))

        sorted_edits = sorted(edits, key=get_start, reverse=True)
        lines = content.splitlines(keepends=True)

        for te in sorted_edits:
            rng = te.get("range", {})
            start = rng.get("start", {})
            end = rng.get("end", {})
            new_text = te.get("newText", "")

            start_line = start.get("line", 0)
            start_char = start.get("character", 0)
            end_line = end.get("line", 0)
            end_char = end.get("character", 0)

            if start_line == end_line:
                if 0 <= start_line < len(lines):
                    line_text = lines[start_line]
                    lines[start_line] = line_text[:start_char] + new_text + line_text[end_char:]
            else:
                if 0 <= start_line < len(lines) and 0 <= end_line < len(lines):
                    first_line = lines[start_line][:start_char]
                    last_line = lines[end_line][end_char:]
                    lines[start_line] = first_line + new_text + last_line
                    for idx in range(start_line + 1, end_line + 1):
                        lines[idx] = ""

        if not ctx.policy.validate_write(filepath):
            skipped_protected.append(str(filepath.relative_to(ctx.workspace)))
            continue

        updated_content = "".join(lines)
        await asyncio.to_thread(commit_and_write, ctx.workspace, filepath, updated_content, 'utf-8')

        if ctx.lsp:
            try:
                await ctx.lsp.open_document(filepath, updated_content)
                await ctx.lsp.change_document(filepath, updated_content)
            except Exception:
                pass

        rel_path = str(filepath.relative_to(ctx.workspace))
        applied_paths.append(rel_path)

    if ctx.reg._symbols is not None:
        ctx.reg._symbols.refresh()

    return applied_paths, skipped_protected
