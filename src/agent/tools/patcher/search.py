"""Fuzzy search and mismatch diagnosis for the patcher."""
import difflib
from typing import List, Optional, Tuple

from ...errors import AmbiguousMatchError, ToolError
from .core import _normalize


_CLOSEST_MATCH_FLOOR = 0.5
_CLOSEST_MATCH_MAX_LINES = 20
_CLOSEST_MATCH_CANDIDATES = 8
_DRIFT_MAX_CHARS = 1500


def _fuzzy_replace(content: str, search: str, replace: str) -> Optional[str]:
    """Whitespace-tolerant line-block replacement."""
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
    if len(matches) == 0:
        return None
    if len(matches) > 1:
        raise AmbiguousMatchError(
            f"Multiple identical blocks found ({len(matches)} matches). "
            "Please provide 3-5 additional lines of surrounding context above and below the target block to disambiguate."
        )

    i = matches[0]
    matched_text = "".join(file_lines[i:i + n])
    repl = replace
    if matched_text.endswith("\n") and not repl.endswith("\n"):
        repl += "\n"
    new_lines = file_lines[:i] + [repl] + file_lines[i + n:]
    return "".join(new_lines)


def _closest_block(content: str, search: str) -> Optional[Tuple[int, int, float, str]]:
    """Find the text in ``content`` most like ``search``."""
    file_lines = content.splitlines()
    search_lines = search.splitlines()
    n = len(search_lines)
    if not n or not file_lines:
        return None

    norm_search = "\n".join(_normalize(ln) for ln in search_lines)
    norm_file = [_normalize(ln) for ln in file_lines]

    wanted = {ln for ln in (_normalize(x) for x in search_lines) if ln}
    hits = [1 if ln in wanted else 0 for ln in norm_file]

    candidates: List[Tuple[int, int]] = []
    running = sum(hits[:n])
    candidates.append((running, 0))
    for i in range(1, len(file_lines) - n + 1):
        running += hits[i + n - 1] - hits[i - 1]
        candidates.append((running, i))

    candidates.sort(key=lambda c: -c[0])
    best: Optional[Tuple[int, int, float, str]] = None
    for _, i in candidates[:_CLOSEST_MATCH_CANDIDATES]:
        for width in {max(1, n - 1), n, n + 1}:
            if i + width > len(file_lines):
                continue
            ratio = difflib.SequenceMatcher(
                None, norm_search, "\n".join(norm_file[i:i + width])
            ).ratio()
            if best is None or ratio > best[2]:
                best = (i + 1, i + width, ratio, "\n".join(file_lines[i:i + width]))

    if best is None or best[2] < _CLOSEST_MATCH_FLOOR:
        return None
    return best


def _outline(content: str, limit: int = 12) -> str:
    """List the file's def/class lines, for when nothing resembles the search block."""
    found = [
        f"  line {i}: {ln.strip()}"
        for i, ln in enumerate(content.splitlines(), 1)
        if ln.lstrip().startswith(("def ", "async def ", "class "))
    ]
    if not found:
        return ""
    shown = found[:limit]
    more = f"\n  ... and {len(found) - limit} more" if len(found) > limit else ""
    return "\n".join(shown) + more


def _not_found_error(content: str, search: str) -> ToolError:
    """Build a search-miss error that shows what IS in the file."""
    head = (
        "search block not found in file. `search` is matched as LITERAL text, not a "
        "regular expression -- do not escape characters like [ ] ( ) . *"
    )
    closest = _closest_block(content, search)
    if closest is None:
        outline = _outline(content)
        body = (
            "\n\nNothing in the file resembles that block, so it is not a small "
            "mismatch -- you are editing the wrong file, or the text was never there."
        )
        if outline:
            body += f"\nThe file actually defines:\n{outline}"
        body += "\nRe-read the file before editing it again."
        return ToolError(head + body)

    start, end, ratio, actual = closest
    quoted = actual.splitlines()
    if len(quoted) > _CLOSEST_MATCH_MAX_LINES:
        quoted = quoted[:_CLOSEST_MATCH_MAX_LINES] + ["  ... (truncated)"]
    numbered = "\n".join(
        f"{start + i:>5} | {ln}" for i, ln in enumerate(quoted) if not ln.startswith("  ...")
    )
    drift = "".join(
        difflib.unified_diff(
            [ln + "\n" for ln in search.splitlines()],
            [ln + "\n" for ln in actual.splitlines()],
            fromfile="what you sent",
            tofile=f"what is at lines {start}-{end}",
            n=1,
        )
    )
    if len(drift) > _DRIFT_MAX_CHARS:
        drift = drift[:_DRIFT_MAX_CHARS] + "\n... (diff truncated)"
    return ToolError(
        f"{head}\n\nThe closest text in the file is lines {start}-{end} "
        f"({ratio:.0%} similar):\n{numbered}\n\n"
        f"Difference between your search block and that text:\n{drift}\n"
        f"Copy the text above EXACTLY into `search`, or use `edit_lines` with "
        f"start_line={start}, end_line={end}."
    )
