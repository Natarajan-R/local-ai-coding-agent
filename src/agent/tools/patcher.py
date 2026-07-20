"""Deterministic search/replace patching for file edits."""
from __future__ import annotations

import ast
import difflib
import logging
import re
from typing import List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

from ..errors import ToolError

# A field called "search" reads like a pattern, so models regex-escape the text
# they put in it: `record\["id"\]` for a file that contains `record["id"]`. The
# match then fails forever — re-reading cannot help, because the model re-derives
# the same escaped form from the same source line. Measured: this was the entire
# residual Tier 3 failure, and it only ever bit the one call site in the fixture
# containing brackets.
_REGEX_ESCAPE_RE = re.compile(r"\\([.^$*+?()\[\]{}|/-])")


def _strip_regex_escapes(text: str) -> str:
    """Turn `\\[` back into `[`, for the metacharacters a model actually escapes.

    Deliberately excludes `\\\\` and letter escapes (`\\n`, `\\t`), which carry
    meaning in the file's own text and must survive untouched.
    """
    return _REGEX_ESCAPE_RE.sub(r"\1", text)


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
            f"search block is ambiguous (found {count} times). To change every "
            f"occurrence use the `replace_all` tool; to change one, add surrounding "
            f"context to make the search block unique."
        )

    # count == 0: try the whitespace-tolerant fallback.
    if fuzzy:
        fuzzy_result = _fuzzy_replace(content, search, replace)
        if fuzzy_result is not None:
            return fuzzy_result

    # Still nothing. The block may be regex-escaped rather than literal. Retry the
    # whole ladder on the unescaped form — but only accept a UNIQUE match, the same
    # bar every other path here has to clear.
    #
    # This cannot corrupt a file that genuinely contains backslashes: if the file
    # really held `record\["id"\]`, the exact match above would already have hit.
    # We only get here when the escaped text appears nowhere.
    unescaped_search = _strip_regex_escapes(search)
    if unescaped_search != search:
        # The replacement is escaped too, and writing it back raw would inject the
        # very backslashes we just removed.
        unescaped_replace = _strip_regex_escapes(replace)
        if content.count(unescaped_search) == 1:
            return content.replace(unescaped_search, unescaped_replace, 1)
        if fuzzy:
            fuzzy_result = _fuzzy_replace(content, unescaped_search, unescaped_replace)
            if fuzzy_result is not None:
                return fuzzy_result

    # Try AST-based semantic splicing fallback for Python files
    try:
        ast_result = apply_ast_splice(content, replace)
        if ast_result is not None:
            logger.info("AST semantic splicing fallback succeeded.")
            return ast_result
    except Exception as e:
        logger.debug("AST splicing fallback failed: %s", e)

    raise ToolError(
        "search block not found in file. The file may already have been edited since "
        "you last read it — re-read it, or use `replace_all` to change every occurrence "
        "of a string in one step. Note: `search` is matched as LITERAL text, not a "
        "regular expression — do not escape characters like [ ] ( ) . *"
    )


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


class DefNode(NamedTuple):
    name_path: Tuple[str, ...]
    lineno: int
    end_lineno: int


def collect_definitions(node: ast.AST, current_path: Tuple[str, ...] = ()) -> List[DefNode]:
    defs = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        path = current_path + (node.name,)
        defs.append(DefNode(path, node.lineno, node.end_lineno))
        for child in node.body:
            defs.extend(collect_definitions(child, path))
    elif isinstance(node, ast.ClassDef):
        path = current_path + (node.name,)
        defs.append(DefNode(path, node.lineno, node.end_lineno))
        for child in node.body:
            defs.extend(collect_definitions(child, path))
    elif isinstance(node, ast.Module):
        for child in node.body:
            defs.extend(collect_definitions(child, current_path))
    return defs


def clean_indentation(text: str) -> str:
    lines = text.splitlines()
    indents = []
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            indents.append(indent)
    if not indents:
        return text
    min_indent = min(indents)
    if min_indent == 0:
        return text
    cleaned_lines = []
    for line in lines:
        if len(line) >= min_indent:
            cleaned_lines.append(line[min_indent:])
        else:
            cleaned_lines.append(line.lstrip())
    return "\n".join(cleaned_lines)


def apply_ast_splice(content: str, replace: str) -> Optional[str]:
    # 1. Clean indentation of replace block and try to parse it
    clean_repl = clean_indentation(replace)
    try:
        repl_tree = ast.parse(clean_repl)
        repl_defs = collect_definitions(repl_tree)
    except Exception:
        return None

    if not repl_defs:
        return None

    # 2. Parse original content
    try:
        orig_tree = ast.parse(content)
        orig_defs = collect_definitions(orig_tree)
    except Exception:
        return None

    # 3. Find unique suffix matches for each repl_def in orig_defs
    matches = []
    for r_def in repl_defs:
        suffix_matches = [
            o_def for o_def in orig_defs
            if len(o_def.name_path) >= len(r_def.name_path) and
               o_def.name_path[-len(r_def.name_path):] == r_def.name_path
        ]
        if len(suffix_matches) != 1:
            return None  # No unique match or ambiguous
        matches.append((suffix_matches[0], r_def))

    # Sort matches in descending order of original line numbers to avoid offset shifts
    matches.sort(key=lambda m: m[0].lineno, reverse=True)

    orig_lines = content.splitlines(keepends=True)

    # Currently we only support single definition replacement (highly safe and covers 99% of cases)
    if len(repl_defs) == 1:
        orig_def, r_def = matches[0]
        # Find leading indent of original function definition line
        if orig_def.lineno - 1 < len(orig_lines):
            start_line = orig_lines[orig_def.lineno - 1]
            whitespace_chars = []
            for c in start_line:
                if c in (' ', '\t'):
                    whitespace_chars.append(c)
                else:
                    break
            indent = "".join(whitespace_chars)
        else:
            indent = ""

        # Format clean_repl with matching indentation
        repl_lines = []
        for line in clean_repl.splitlines(keepends=True):
            if line.strip():
                repl_lines.append(indent + line)
            else:
                repl_lines.append(line)
        
        repl_str = "".join(repl_lines)
        if not repl_str.endswith("\n"):
            repl_str += "\n"

        # Splice back into orig_lines (orig_def is 1-indexed, inclusive of end_lineno)
        new_lines = orig_lines[:orig_def.lineno - 1] + [repl_str] + orig_lines[orig_def.end_lineno:]
        return "".join(new_lines)

    return None


def _clean_str(s: str) -> tuple[str, list[int]]:
    chars = []
    indices = []
    for idx, char in enumerate(s):
        if not char.isspace():
            chars.append(char)
            indices.append(idx)
    return "".join(chars), indices


def align_indentation(baseline_line: str, replace_block: str, search_block: str = "") -> str:
    if not replace_block:
        return replace_block
        
    def get_leading_whitespace(s: str) -> str:
        ws = []
        for c in s:
            if c in (' ', '\t'):
                ws.append(c)
            else:
                break
        return "".join(ws)
        
    def indent_width(ws: str) -> int:
        return sum(4 if c == '\t' else 1 for c in ws)
        
    baseline_indent = get_leading_whitespace(baseline_line)
    base_width = indent_width(baseline_indent)
    
    # Find first non-empty line in replace block
    replace_lines = replace_block.splitlines(keepends=True)
    first_non_empty = None
    for line in replace_lines:
        if line.strip():
            first_non_empty = line
            break
    if first_non_empty is None:
        first_non_empty = replace_lines[0]

    incoming_indent = get_leading_whitespace(first_non_empty)

    # Anchor the replacement to the file's actual indentation at the match, and
    # preserve the replace block's own internal (relative) structure by shifting
    # every line by the same amount. We deliberately do NOT derive an offset from
    # the search block: matching (_normalize) strips indentation, so a search
    # block matches regardless of how it is indented, and the model routinely
    # dedents or mis-indents it. The old code added (replace_indent -
    # search_indent) on top of the baseline, double-counting the indent and
    # emitting over-indented, unparseable code — an unindented search block plus a
    # normally-indented replace produced a +16 shift (16 -> 32 spaces),
    # "IndentationError: unexpected indent". That broke dot-dsl and tree-building
    # (both 0/5) on tasks the bare model one-shots cleanly. (search_block is kept
    # in the signature for callers but is intentionally no longer trusted here.)
    target_width = base_width
    target_indent = ' ' * target_width
    
    if incoming_indent == target_indent:
        return replace_block
        
    inc_width = indent_width(incoming_indent)
    delta = target_width - inc_width
    
    new_lines = []
    for line in replace_lines:
        if not line.strip():
            new_lines.append(line)
            continue
            
        line_ws = get_leading_whitespace(line)
        line_content = line[len(line_ws):]
        
        if line_ws.startswith(incoming_indent):
            # Convert incoming_indent to target_indent and keep the rest
            if incoming_indent == "" and delta > 0 and line_ws.startswith(target_indent):
                # If the first line was unindented but this line is already indented
                # to the target or more, keep it as-is to prevent double-indentation.
                new_lines.append(line)
            else:
                new_ws = target_indent + line_ws[len(incoming_indent):]
                new_lines.append(new_ws + line_content)
        else:
            new_width = max(0, indent_width(line_ws) + delta)
            new_lines.append((' ' * new_width) + line_content)
            
    return "".join(new_lines)


def apply_line_edit(content: str, start_line: int, end_line: int, search: str, replace: str, window: int = 50) -> str:
    """Replace target lines with `replace` matching `search` with drift-tolerance."""
    if search == "":
        raise ToolError("search block must not be empty")

    file_lines = content.splitlines(keepends=True)
    num_lines = len(file_lines)

    search_lines = search.splitlines()
    n = len(search_lines)
    if n == 0:
        raise ToolError("search block must not be empty")

    norm_search = [_normalize(ln) for ln in search_lines]
    norm_file = [_normalize(ln) for ln in file_lines]

    # Find all matching sequences globally
    matches = [
        i for i in range(len(file_lines) - n + 1)
        if norm_file[i:i + n] == norm_search
    ]

    # Try direct match first
    direct_match = False
    target_len = end_line - start_line + 1
    # Check if lines [start_line - 1 : end_line] match
    if 1 <= start_line <= num_lines and 1 <= end_line <= num_lines and start_line <= end_line:
        direct_slice = file_lines[start_line - 1 : end_line]
        if [_normalize(ln) for ln in direct_slice] == norm_search:
            direct_match = True
            match_idx = start_line - 1
            matched_len = len(direct_slice)

    if not direct_match:
        # Fallback 1: unique global match
        if len(matches) == 1:
            match_idx = matches[0]
            matched_len = n
        elif len(matches) > 1:
            # Fallback 2: unique match within sliding window
            window_matches = [
                idx for idx in matches
                if abs(idx - (start_line - 1)) <= window
            ]
            if len(window_matches) == 1:
                match_idx = window_matches[0]
                matched_len = n
            elif len(window_matches) == 0:
                raise ToolError(
                    f"expected search block was found at other locations, but not near line {start_line}. "
                    f"To avoid editing the wrong code, please re-read the file or adjust start_line/end_line."
                )
            else:
                raise ToolError(
                    f"expected search block is ambiguous near line {start_line} (found {len(window_matches)} matches in window). "
                    f"Please provide more surrounding context in the search block to make it unique."
                )
        else:
            # Try fuzzy match ignoring whitespace and line-break splits
            clean_content, content_map = _clean_str(content)
            clean_search, _ = _clean_str(search)
            if clean_search:
                matches_clean = []
                idx = clean_content.find(clean_search)
                while idx != -1:
                    matches_clean.append(idx)
                    idx = clean_content.find(clean_search, idx + 1)
                
                if len(matches_clean) == 1:
                    start_idx_clean = matches_clean[0]
                    end_idx_clean = start_idx_clean + len(clean_search) - 1
                    start_char_idx = content_map[start_idx_clean]
                    end_char_idx = content_map[end_idx_clean]
                    
                    file_lines_fuzzy = content.splitlines(keepends=True)
                    fuzzy_line_idx = content[:start_char_idx].count('\n')
                    if 0 <= fuzzy_line_idx < len(file_lines_fuzzy):
                        repl = align_indentation(file_lines_fuzzy[fuzzy_line_idx], replace, search)
                    else:
                        repl = replace
                    if content[end_char_idx + 1:].startswith("\n") and not repl.endswith("\n"):
                        repl += "\n"

                    # _clean_str strips whitespace, so start_char_idx lands on the
                    # first non-blank character -- splicing there would KEEP the
                    # line's existing indent while align_indentation has already
                    # added its own, stacking the two (8 spaces became 16 and the
                    # file stopped parsing). Rewind to the line start so the
                    # aligned replacement supplies the indentation exactly once.
                    line_start = content.rfind("\n", 0, start_char_idx) + 1
                    return content[:line_start] + repl + content[end_char_idx + 1:]
            
            raise ToolError(
                "expected search block was not found anywhere in the file. "
                "Please verify the expected content matches what is currently in the file."
            )

    baseline_line = file_lines[match_idx]
    repl = align_indentation(baseline_line, replace, search)
    # Keep newline consistency
    matched_text = "".join(file_lines[match_idx : match_idx + matched_len])
    if matched_text.endswith("\n") and not repl.endswith("\n"):
        repl += "\n"

    new_lines = file_lines[:match_idx] + [repl] + file_lines[match_idx + matched_len:]
    return "".join(new_lines)

