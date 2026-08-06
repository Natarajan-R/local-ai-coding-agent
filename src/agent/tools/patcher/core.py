"""Core text manipulation functions for the patcher."""
import difflib
import re
import textwrap

_REGEX_ESCAPE_RE = re.compile(r"\\([.^$*+?()\[\]{}|/-])")


def _strip_regex_escapes(text: str) -> str:
    """Turn `\\[` back into `[`, for the metacharacters a model actually escapes."""
    return _REGEX_ESCAPE_RE.sub(r"\1", text)


def _normalize(line: str) -> str:
    """Collapse all runs of whitespace and strip ends."""
    return " ".join(line.split())


def _clean_str(s: str) -> tuple[str, list[int]]:
    """Return ``s`` with whitespace removed, plus the original index of each kept char."""
    chars = []
    indices = []
    for idx, char in enumerate(s):
        if not char.isspace():
            chars.append(char)
            indices.append(idx)
    return "".join(chars), indices


def make_diff(before: str, after: str, path: str = "file") -> str:
    """Return a unified diff between ``before`` and ``after``."""
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff)


def clean_indentation(text: str) -> str:
    """Dedent ``text`` by stripping the common leading indentation from all lines."""
    return textwrap.dedent(text)


def _get_leading_whitespace(s: str) -> str:
    """Extract leading spaces and tabs without a manual character loop."""
    stripped = s.lstrip(' \t')
    return s[:len(s) - len(stripped)]

def _indent_width(ws: str) -> int:
    """Calculate visual indentation width (tabs = 4 spaces)."""
    return sum(4 if c == '\t' else 1 for c in ws)


def align_indentation(baseline_line: str, replace_block: str) -> str:
    """Re-indent ``replace_block`` so its first line matches ``baseline_line``'s indentation."""
    if not replace_block:
        return replace_block
        
    baseline_indent = _get_leading_whitespace(baseline_line)
    base_width = _indent_width(baseline_indent)
    
    replace_lines = replace_block.splitlines(keepends=True)
    first_non_empty = next((line for line in replace_lines if line.strip()), replace_lines[0])

    incoming_indent = _get_leading_whitespace(first_non_empty)
    target_indent = ' ' * base_width
    
    if incoming_indent == target_indent:
        return replace_block
        
    delta = base_width - _indent_width(incoming_indent)
    new_lines = []
    
    for line in replace_lines:
        if not line.strip():
            new_lines.append(line)
            continue
            
        line_ws = _get_leading_whitespace(line)
        line_content = line[len(line_ws):]
        
        if line_ws.startswith(incoming_indent):
            if incoming_indent == "" and delta > 0 and line_ws.startswith(target_indent):
                new_lines.append(line)
            else:
                new_ws = target_indent + line_ws[len(incoming_indent):]
                new_lines.append(new_ws + line_content)
        else:
            new_width = max(0, _indent_width(line_ws) + delta)
            new_lines.append((' ' * new_width) + line_content)
            
    return "".join(new_lines)
