"""Simple tool handlers with no cross-cutting concerns.

All handlers accept a :class:`HandlerContext` instead of a ToolRegistry reference,
breaking the circular dependency on the registry class.
"""
from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from ..errors import ToolError
from ..perception.indexer import IGNORE_DIRS
from .utils import ToolResult, truncate, MAX_OUTPUT_CHARS

if TYPE_CHECKING:
    from .registry import ToolRegistry


@dataclass
class HandlerContext:
    """Shared state that all handler functions need, extracted from ToolRegistry."""
    workspace: Path
    policy: Any
    sandbox: Any
    indexer: Any
    lsp: Any = None
    approval_callback: Any = None
    memory: Any = None
    symbols: Any = None
    reg: Any = None  # back-reference for _symbol_index() and _scan_workspace_files_sync

    @staticmethod
    def from_registry(reg: "ToolRegistry") -> "HandlerContext":
        return HandlerContext(
            workspace=reg.workspace,
            policy=reg.policy,
            sandbox=reg.sandbox,
            indexer=reg.indexer,
            lsp=reg.lsp,
            approval_callback=reg.approval_callback,
            memory=reg.memory,
            symbols=reg._symbols,
            reg=reg,
        )


# ── workspace file scanner (shared by multiple handlers) ─────────────────

_MODULE_SUFFIXES = (".py", ".pyi", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go",
                    ".rs", ".java", ".rb", ".c", ".h", ".cpp", ".cs")


def scan_workspace_files_sync(ctx: HandlerContext, pattern: str = "*", must_be_source: bool = False) -> List[Path]:
    """Synchronously scan and filter workspace files (run off-thread)."""
    valid_files = []
    for path in sorted(ctx.workspace.rglob(pattern)):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ctx.workspace).parts):
            continue
        if must_be_source and path.suffix not in _MODULE_SUFFIXES:
            continue
        valid_files.append(path)
    return valid_files


def as_module_name(name: str) -> str:
    """Turn whatever the caller has in hand into a module name."""
    stem = Path(name.strip()).name
    for ext in _MODULE_SUFFIXES:
        if stem.endswith(ext) and len(stem) > len(ext):
            return stem[: -len(ext)]
    return name.strip()


# ── simple handlers ──────────────────────────────────────────────────────

async def read_file(ctx: HandlerContext, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
    """Handler for ``read_file``."""
    from .file_edit_handlers import safe_path
    target = safe_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    if not target.is_file():
        return ToolResult(False, f"Not a file: {path}")
    text = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")

    if start_line is None and end_line is None:
        return ToolResult(True, truncate(text, 20_000))

    lines = text.splitlines()
    start = max(1, start_line or 1)
    end = min(len(lines), end_line or len(lines))
    if start > end:
        return ToolResult(False, f"Invalid range: start_line {start} > end_line {end}")
    numbered = [f"{i}\t{lines[i - 1]}" for i in range(start, end + 1)]
    header = f"[{path} lines {start}-{end} of {len(lines)}]\n"
    return ToolResult(True, header + truncate("\n".join(numbered), 20_000))


async def solve_constraints(
    ctx: HandlerContext,
    variables: Any,
    constraints: Any,
    all_different: Any = None,
    minimize: Optional[str] = None,
    maximize: Optional[str] = None,
) -> ToolResult:
    """Handler for ``solve_constraints``."""
    from ..solver import solve, SolverError
    try:
        solution = await asyncio.to_thread(
            solve, variables, constraints, all_different, minimize, maximize
        )
    except SolverError as exc:
        return ToolResult(False, f"Could not solve: {exc}")
    except Exception as exc:
        return ToolResult(False, f"Solver failed: {type(exc).__name__}: {exc}")

    if solution.status == "sat":
        lines = "\n".join(f"  {k} = {v}" for k, v in sorted(solution.assignments.items()))
        return ToolResult(True, f"Solved. Use these values:\n{lines}")
    if solution.status == "unsat":
        return ToolResult(
            True,
            "No solution exists -- these constraints contradict each other. "
            "This is a definite answer: do not retry the same problem. Relax or "
            "correct a constraint, or report that the requirement is impossible.",
        )
    return ToolResult(False, solution.message)


async def write_file(ctx: HandlerContext, path: str, content: str) -> ToolResult:
    """Handler for ``write_file``."""
    from .utils import normalize_async_scaffolding
    from ..perception.analysis import syntax_note
    if path.endswith(".py"):
        content = normalize_async_scaffolding(content)
    # Use safe_write_path which validates path containment + write protection in one step.
    from .file_edit_handlers import safe_write_path
    target = safe_write_path(ctx, path)

    if not content.strip() and target.exists() and target.stat().st_size > 0:
        return ToolResult(
            False,
            f"Refused to overwrite {path} with empty content: it currently has "
            f"{target.stat().st_size} bytes. If you meant to clear it, say so "
            f"explicitly; otherwise resend the call with the full file content.",
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    await ctx.reg._atomic_commit_and_refresh(target, content)

    note = syntax_note(path, content)
    ctx.reg._edit_misses.pop(path, None)
    ctx.policy.audit.record("write_file", path=path, bytes=len(content), syntax_ok=not note)
    return ToolResult(True, f"Wrote {len(content)} bytes to {path}{note}")


def list_files(ctx: HandlerContext, directory: Optional[str] = None) -> ToolResult:
    """Handler for ``list_files``."""
    if directory and not ctx.policy.validate_path(directory):
        return ToolResult(False, f"Path '{directory}' is outside the workspace")
    files = ctx.indexer.list_files(directory)
    rows = [str(f.relative_to(ctx.workspace)) for f in files]
    if not rows:
        scope = f" under {directory}" if directory else ""
        return ToolResult(True, f"(no files{scope})")
    return ToolResult(True, truncate("\n".join(rows), 8_000))


def search_text(ctx: HandlerContext, query: str, max_results: int = 50) -> ToolResult:
    """Handler for ``search_text``."""
    try:
        max_results = max(1, min(int(max_results), 200))
    except (TypeError, ValueError):
        max_results = 50
    matches = ctx.indexer.search_text(query, max_results=max_results)
    if not matches:
        return ToolResult(True, f"No matches for {query!r}.")
    rows = [f"{rel}:{lineno}: {line}" for rel, lineno, line in matches]
    header = f"{len(matches)} match(es) for {query!r}:\n"
    return ToolResult(True, header + truncate("\n".join(rows), 8_000))


def outline(ctx: HandlerContext, path: str) -> ToolResult:
    """Handler for ``outline``."""
    from .file_edit_handlers import safe_path
    target = safe_path(ctx, path)
    if not target.exists():
        return ToolResult(False, f"File not found: {path}")
    if not target.is_file():
        return ToolResult(False, f"Not a file: {path}")
    text = ctx.indexer.outline(target)
    if not text:
        return ToolResult(True, f"(no symbols found in {path}; use read_file to view it)")
    return ToolResult(True, f"# Outline of {path}\n{text}")


async def run_command(ctx: HandlerContext, command: str) -> ToolResult:
    """Handler for ``run_command``."""
    if ctx.approval_callback is not None:
        approved = await ctx.policy.approve_command_async(command, ctx.approval_callback)
    else:
        approved = ctx.policy.approve_command(command)
    if not approved:
        return ToolResult(False, f"Command blocked or not approved: {command}")
    if hasattr(ctx.sandbox, "aexec"):
        result = await ctx.sandbox.aexec(command)
    else:
        result = ctx.sandbox.exec(command)
    body = ctx.policy.scrub(result.output) or "(no output)"
    status = "ok" if result.ok else f"exit={result.exit_code}"
    return ToolResult(result.ok, f"[{status}]\n{truncate(body, 8_000)}")


def finish(ctx: HandlerContext, summary: str = "") -> ToolResult:
    """Handler for ``finish``."""
    return ToolResult(True, summary or "Task finished.", is_final=True)


def remember(ctx: HandlerContext, text: str, kind: str = "note") -> ToolResult:
    """Handler for ``remember``."""
    if ctx.memory is None:
        return ToolResult(False, "Memory is disabled.")
    entry = ctx.memory.add(text, kind=kind)
    if entry is None:
        return ToolResult(True, "Already remembered (or empty) — nothing added.")
    return ToolResult(True, f"Remembered [{entry.kind}]: {entry.text}")


def find_symbol(ctx: HandlerContext, name: str) -> ToolResult:
    """Handler for ``find_symbol``."""
    index = ctx.reg._symbol_index()
    hits = index.find_definition(name)
    if not hits:
        hits = index.search(name)  # fall back to substring
    if not hits:
        return ToolResult(True, f"No symbol matching {name!r} found.")
    rows = [f"{h.path}:{h.line}: {h.kind} {h.name}" for h in hits]
    return ToolResult(True, f"{len(hits)} definition(s) for {name!r}:\n" + "\n".join(rows))


def find_importers(ctx: HandlerContext, name: str) -> ToolResult:
    """Handler for ``find_importers``."""
    module = as_module_name(name)
    rows = ctx.reg._symbol_index().importers(module)
    if not rows:
        return ToolResult(True, f"No files import {module!r}.")
    out = [f"{path}:{line}: imports {module_name}" for path, line, module_name in rows]
    return ToolResult(True, f"{len(rows)} importer(s) of {module!r}:\n" + "\n".join(out))


async def read_symbol(ctx: HandlerContext, symbol: str, path: Optional[str] = None) -> ToolResult:
    """Return the exact source of ONE function, method or class (non-blocking)."""
    target_path = None
    if path:
        if not ctx.policy.validate_path(path):
            raise ToolError(f"Path '{path}' is outside the workspace")
        target_path = ctx.policy.resolve_path(path)

    def _search_symbol_worker():
        """Worker function executed in a background thread."""
        targets = [target_path] if target_path else scan_workspace_files_sync(ctx, "*.py")
        wanted = symbol.split(".")

        for file in targets:
            if not file.is_file():
                continue
            try:
                source = file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue

            node, scope = None, tree
            for part in wanted:
                node = next(
                    (n for n in ast.iter_child_nodes(scope)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                     and n.name == part),
                    None,
                )
                if node is None:
                    break
                scope = node

            if node is not None:
                lines = source.splitlines()[node.lineno - 1: node.end_lineno]
                return file, node.lineno, node.end_lineno, lines
        return None

    import asyncio as _asyncio
    result = await _asyncio.to_thread(_search_symbol_worker)

    if result is not None:
        file, start_line, end_line, lines = result
        rel = file.relative_to(ctx.workspace)
        return ToolResult(
            True,
            f"{rel}:{start_line}-{end_line}  {symbol}\n"
            + truncate("\n".join(lines), 20_000),
        )

    where = f" in {path}" if path else " anywhere in the workspace"
    return ToolResult(False, f"No function, method or class named {symbol!r} found{where}. "
                             f"For a method inside a class, use Class.method.")
