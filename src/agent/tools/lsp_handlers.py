"""LSP-backed tool handlers (find_definition, find_references, get_diagnostics)."""
from __future__ import annotations

from pathlib import Path

from .file_edit_handlers import safe_path
from .simple_handlers import HandlerContext
from .utils import ToolResult


async def find_definition(ctx: HandlerContext, path: str, line: int, character: int) -> ToolResult:
    """Handler for ``find_definition``."""
    if not ctx.lsp:
        return ToolResult(False, "LSP client not initialized")
    target = safe_path(ctx, path)
    res = await ctx.lsp.get_definition(target, line, character)
    if not res:
        return ToolResult(True, "No definition found.")

    out = []
    for loc in res:
        uri = loc.get("uri", "")
        rng = loc.get("range", {})
        start = rng.get("start", {})
        end = rng.get("end", {})

        path_str = uri
        if uri.startswith("file://"):
            try:
                p = Path(uri[7:])
                if p.is_relative_to(ctx.workspace):
                    path_str = str(p.relative_to(ctx.workspace))
                else:
                    path_str = str(p)
            except Exception:
                pass
        out.append(
            f"File: {path_str}\n"
            f"  Start: Line {start.get('line', 0) + 1}, Col {start.get('character', 0) + 1}\n"
            f"  End: Line {end.get('line', 0) + 1}, Col {end.get('character', 0) + 1}"
        )
    return ToolResult(True, "\n\n".join(out))


async def find_references(ctx: HandlerContext, path: str, line: int, character: int) -> ToolResult:
    """Handler for ``find_references``."""
    if not ctx.lsp:
        return ToolResult(False, "LSP client not initialized")
    target = safe_path(ctx, path)
    res = await ctx.lsp.get_references(target, line, character)
    if not res:
        return ToolResult(True, "No references found.")

    out = []
    for loc in res:
        uri = loc.get("uri", "")
        rng = loc.get("range", {})
        start = rng.get("start", {})

        path_str = uri
        if uri.startswith("file://"):
            try:
                p = Path(uri[7:])
                if p.is_relative_to(ctx.workspace):
                    path_str = str(p.relative_to(ctx.workspace))
                else:
                    path_str = str(p)
            except Exception:
                pass
        out.append(f"File: {path_str}, Line {start.get('line', 0) + 1}, Col {start.get('character', 0) + 1}")
    return ToolResult(True, "\n".join(out))


async def get_diagnostics(ctx: HandlerContext) -> ToolResult:
    """Handler for ``get_diagnostics``."""
    if not ctx.lsp:
        return ToolResult(False, "LSP client not initialized")
    await ctx.lsp.await_diagnostics()
    res = ctx.lsp.get_all_diagnostics()
    return ToolResult(True, res)
