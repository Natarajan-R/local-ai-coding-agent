"""Rename handler — LSP rename with regex fallback, plus workspace-edit applier."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple

from .file_edit_handlers import apply_workspace_edit
from .simple_handlers import HandlerContext, scan_workspace_files_sync
from .utils import ToolResult

logger = logging.getLogger(__name__)


async def rename_symbol(ctx: HandlerContext, old: str, new: str) -> ToolResult:
    """Rename an identifier across every file in the workspace, in one call."""
    if not old:
        return ToolResult(False, "`old` must not be empty")
    if not new:
        return ToolResult(False, "`new` must not be empty")
    if old == new:
        return ToolResult(False, "`old` and `new` are identical — nothing to do")

    # 1. Try LSP rename first
    if ctx.lsp:
        hits = []
        if ctx.reg._symbols is not None:
            hits = ctx.reg._symbols.find_definition(old)

        if hits:
            hit = hits[0]
            target_path = ctx.workspace / hit.path
            if target_path.exists():
                try:
                    content = await asyncio.to_thread(target_path.read_text, encoding="utf-8")
                    lines = content.splitlines()
                    line_idx = hit.line - 1
                    if 0 <= line_idx < len(lines):
                        line_text = lines[line_idx]
                        col_offset = line_text.find(old)
                        if col_offset != -1:
                            workspace_edit = await ctx.lsp.rename(target_path, line_idx, col_offset, new)
                            if workspace_edit:
                                applied, skipped = await apply_workspace_edit(ctx, workspace_edit)
                                if applied:
                                    note = ""
                                    if skipped:
                                        note = (
                                            f"\nSkipped {len(skipped)} protected file(s), which still "
                                            f"reference {old!r}:\n"
                                            + "\n".join(f"  {f}" for f in skipped)
                                        )
                                    return ToolResult(
                                        True,
                                        f"Semantically renamed {old!r} to {new!r} via LSP across "
                                        f"{len(applied)} file(s):\n"
                                        + "\n".join(f"  {f}" for f in applied) + note
                                    )
                except Exception as exc:
                    logger.warning("LSP rename failed, falling back to regex: %s", exc)

    # 2. Fall back to regex word-boundary replacement
    pattern = re.compile(rf"\b{re.escape(old)}\b")
    changed: List[Any] = []
    skipped_protected: List[str] = []
    total = 0

    candidate_files = await asyncio.to_thread(
        scan_workspace_files_sync, ctx, "*", must_be_source=False
    )

    for path in candidate_files:
        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        count = len(pattern.findall(content))
        if not count:
            continue

        if not ctx.policy.validate_write(path):
            skipped_protected.append(str(path.relative_to(ctx.workspace)))
            continue

        new_content = pattern.sub(new, content)
        await ctx.reg._atomic_commit_and_refresh(path, new_content)
        changed.append((str(path.relative_to(ctx.workspace)), count))
        total += count

    if not total:
        if skipped_protected:
            return ToolResult(
                False,
                f"{old!r} appears only in protected file(s), which must not be "
                f"modified:\n" + "\n".join(f"  {f}" for f in skipped_protected)
                + "\nNothing was renamed.",
            )
        return ToolResult(
            False,
            f"No whole-word occurrences of {old!r} found in the workspace. Check the "
            f"spelling — `old` is a literal identifier, not a regex or a substring.",
        )

    lines = "\n".join(f"  {p}: {c}" for p, c in changed)
    note = ""
    if skipped_protected:
        note = (
            f"\nSkipped {len(skipped_protected)} protected file(s), which still "
            f"reference {old!r}:\n"
            + "\n".join(f"  {f}" for f in skipped_protected)
        )
    return ToolResult(
        True,
        f"Renamed {old!r} to {new!r}: {total} occurrence(s) across "
        f"{len(changed)} file(s).\n{lines}{note}",
    )
