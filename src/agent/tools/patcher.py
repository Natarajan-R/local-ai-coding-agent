"""Deterministic search/replace patching for file edits."""
from __future__ import annotations

import difflib
from typing import List, Optional, Tuple

from ..errors import ToolError


def _normalize(line: str) -> str:
    """Collapse all runs of whitespace and strip ends (tab/space/trailing-agnostic)."""
    return " ".join(line.split())


def _fuzzy_replace(content: str, search: str, replace: str) -> Optional[str]:
    """Whitespace-tolerant line-block replacement.

    Local models frequently reproduce a block with slightly different indentation
    or trailing whitespace, so an exact match fails. This matches on a
    whitespace-normalized, line-by-line basis and, only when the match is unique,
    replaces the real (un-normalized) file text with ``replace``.
    Returns None if there is no match or the match is ambiguous.
    """
    file_lines: List[str] = content.splitlines(keepends=True)
    search_lines = search.splitlines()
    n = len(search_lines)
    if n == 0:
        return None

    norm_search = [_normalize(ln) for ln in search_lines]
    norm_file = [_normalize(ln) for ln in file_lines]

    matches = [
        i for i in range(len(file_lines) - n + 1)
        if norm_file[i:i + n] == norm_search
    ]
    if len(matches) != 1:
        return None  # 0 matches or ambiguous

    i = matches[0]
    matched_text = "".join(file_lines[i:i + n])
    repl = replace
    if matched_text.endswith("\n") and not repl.endswith("\n"):
        repl += "\n"
    # Splice the matched line range directly — do NOT use content.replace(), which
    # would hit the first substring occurrence anywhere in the file (a matched line
    # like "foo\n" can appear inside an earlier line like "barfoo\n").
    new_lines = file_lines[:i] + [repl] + file_lines[i + n:]
    return "".join(new_lines)


def apply_search_replace(content: str, search: str, replace: str, fuzzy: bool = True) -> str:
    """Replace the single occurrence of ``search`` in ``content`` with ``replace``.

    Tries an exact, unique match first. If that is not found and ``fuzzy`` is on,
    falls back to a whitespace-tolerant line-block match. Raises :class:`ToolError`
    if the block is missing or ambiguous, keeping edits precise and reviewable.
    """
    if search == "":
        raise ToolError("search block must not be empty")

    count = content.count(search)
    if count == 1:
        return content.replace(search, replace, 1)
    if count > 1:
        raise ToolError(
            f"search block is ambiguous (found {count} times); add more context"
        )

    # count == 0: try the whitespace-tolerant fallback.
    if fuzzy:
        fuzzy_result = _fuzzy_replace(content, search, replace)
        if fuzzy_result is not None:
            return fuzzy_result

    raise ToolError("search block not found in file")


def make_diff(before: str, after: str, path: str = "file") -> str:
    """Return a unified diff between ``before`` and ``after``."""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff)


def apply_and_diff(content: str, search: str, replace: str, path: str = "file") -> Tuple[str, str]:
    """Apply a search/replace edit and also return the unified diff."""
    updated = apply_search_replace(content, search, replace)
    return updated, make_diff(content, updated, path)
