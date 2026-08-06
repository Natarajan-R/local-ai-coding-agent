"""Pure utility functions and data classes for tool implementations.

No registry dependencies — all functions are stateless.
"""
from __future__ import annotations

import ast
import copy
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolResult:
    """The result of running a tool: success flag, output text, and whether it ends the run."""

    ok: bool
    content: str
    is_final: bool = False


@dataclass
class Tool:
    """A registered tool: its name, description, JSON-schema parameters and handler."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., ToolResult]
    needs_ctx: bool = True

    def schema(self) -> Dict[str, Any]:
        """Return the OpenAI-style function schema describing this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# Cap on returned content to keep prompts within the model context window.
MAX_READ_CHARS = 20_000
MAX_OUTPUT_CHARS = 8_000


def truncate(text: str, limit: int) -> str:
    """Return ``text`` capped at ``limit`` chars, with a note when truncated."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def safe_unescape(s: str) -> str:
    """Convert literal ``\\n``/``\\t`` escapes to real characters, but never inside string/comment quoting."""
    if not isinstance(s, str):
        return s
    if "\n" in s or "\t" in s:
        return s

    in_single_quote = False
    in_double_quote = False
    in_triple_single = False
    in_triple_double = False

    chars = []
    i = 0
    n = len(s)
    while i < n:
        in_quote = in_single_quote or in_double_quote or in_triple_single or in_triple_double

        # Check comment
        if not in_quote and s[i] == '#':
            while i < n and s[i] not in ('\n', '\r') and s[i:i+2] != '\\n':
                chars.append(s[i])
                i += 1
            continue

        # Check triple quotes
        if not in_single_quote and not in_double_quote:
            if s[i:i+3] == "'''":
                in_triple_single = not in_triple_single
                chars.append("'''")
                i += 3
                continue
            elif s[i:i+3] == '"""':
                in_triple_double = not in_triple_double
                chars.append('"""')
                i += 3
                continue

        # Check single quotes
        if not in_double_quote and not in_triple_single and not in_triple_double:
            if s[i] == "'" and (i == 0 or s[i-1] != '\\'):
                in_single_quote = not in_single_quote
                chars.append("'")
                i += 1
                continue

        # Check double quotes
        if not in_single_quote and not in_triple_single and not in_triple_double:
            if s[i] == '"' and (i == 0 or s[i-1] != '\\'):
                in_double_quote = not in_double_quote
                chars.append('"')
                i += 1
                continue

        in_quote = in_single_quote or in_double_quote or in_triple_single or in_triple_double

        if s[i:i+2] == '\\\\':
            chars.append('\\')
            i += 2
        elif s[i:i+2] == '\\n':
            if in_quote:
                chars.append('\\n')
            else:
                chars.append('\n')
            i += 2
        elif s[i:i+2] == '\\t':
            if in_quote:
                chars.append('\\t')
            else:
                chars.append('\t')
            i += 2
        else:
            chars.append(s[i])
            i += 1

    return "".join(chars)


# Regex to normalize duplicate async keywords (e.g. async async def) emitted by model scaffolding.
_MULTIPLE_ASYNC_RE = re.compile(r"\b(async\s+){2,}def\b")


def normalize_async_scaffolding(content: str) -> str:
    """Collapse repeated ``async async def`` scaffolding a model sometimes emits into one ``async def``."""
    return _MULTIPLE_ASYNC_RE.sub("async def", content)


def restore_signature_annotations(
    source: str,
    symbol: str,
    original_annotations: Dict[str, str],
    original_return: Optional[str],
) -> str:
    """Put back the type annotations Rope's ChangeSignature strips.

    Rope rewrites every call site correctly — which is why we use it — but it
    drops the parameter annotations from the signature it edits. On a typed
    library that is a silent regression: `pytest` does not type-check, so the
    suite stays green while the code lost its types. This re-attaches, on the
    edited function only, every annotation that was present before Rope ran and
    is missing now. Any argument Rope legitimately added but we have no
    annotation for is simply left bare.

    Returns ``source`` unchanged if anything is unexpected — never a file that
    does not parse.
    """
    if not original_annotations and not original_return:
        return source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source

    node: Any = None
    scope: Any = tree
    for part in symbol.split("."):
        node = next(
            (n for n in ast.iter_child_nodes(scope)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and n.name == part),
            None,
        )
        if node is None:
            return source
        scope = node
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return source

    all_args = list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs)
    if node.args.vararg:
        all_args.append(node.args.vararg)
    if node.args.kwarg:
        all_args.append(node.args.kwarg)

    changed = False
    for a in all_args:
        if a.annotation is None and a.arg in original_annotations:
            try:
                a.annotation = ast.parse(original_annotations[a.arg], mode="eval").body
                changed = True
            except SyntaxError:
                pass
    if node.returns is None and original_return:
        try:
            node.returns = ast.parse(original_return, mode="eval").body
            changed = True
        except SyntaxError:
            pass
    if not changed:
        return source

    # Rebuild only the signature line(s), from `def` to the colon. Rope collapses
    # the signature to one line; unparse gives us a clean single-line version.
    tmp = copy.deepcopy(node)
    tmp.body = [ast.Pass()]
    tmp.decorator_list = []
    ast.fix_missing_locations(tmp)
    new_sig = ast.unparse(tmp).splitlines()[0]

    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    if node.decorator_list:
        first_dec_line = node.decorator_list[0].lineno - 1
        last_dec_line = node.decorator_list[-1].lineno - 1
        if start == first_dec_line:
            # Python < 3.12: search for the actual def keyword line index after the last decorator.
            for idx in range(last_dec_line + 1, len(lines)):
                line_stripped = lines[idx].strip()
                if line_stripped.startswith("def ") or line_stripped.startswith("async def "):
                    start = idx
                    break
    body_start = node.body[0].lineno - 1
    if body_start <= start:
        return source  # single-line `def f(): ...` — leave it alone rather than risk it
    indent = " " * node.col_offset
    rebuilt = "".join(lines[:start] + [indent + new_sig + "\n"] + lines[body_start:])
    try:
        ast.parse(rebuilt)
    except SyntaxError:
        return source
    return rebuilt


def undocumented(source: str) -> List[str]:
    """Every function/method/class in ``source`` that still has no docstring.

    Qualified (``Shape.describe``) so the name can be passed straight back to
    ``add_docstring``.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    missing: List[str] = []

    def walk(node, prefix: str = "") -> None:
        """Recurse the AST, collecting qualified names of undocumented defs/classes."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}{child.name}"
                if not ast.get_docstring(child):
                    missing.append(qualified)
                walk(child, prefix=f"{qualified}.")

    walk(tree)
    return missing


def sanitize_docstring(text: str) -> str:
    """Cleanly unwrap LLM wrapper quotes and escape symbols for safe AST insertion."""
    text = text.strip()

    # 1. Safely unwrap outer wrapper quotes if the LLM disobeyed instructions
    if len(text) >= 6 and (
        (text.startswith('"""') and text.endswith('"""')) or
        (text.startswith("'''") and text.endswith("'''"))
    ):
        text = text[3:-3].strip()
    elif len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"')) or
        (text.startswith("'") and text.endswith("'"))
    ):
        text = text[1:-1].strip()

    # 2. Escape internal triple quotes so they don't prematurely terminate the block
    text = text.replace('"""', '\\"\\"\\"')

    # 3. Prevent syntax errors on single-line docstrings ending with a quote
    # E.g., turning `"""Returns "foo""""` into `"""Returns "foo"\""""`
    if text.endswith('"') and not text.endswith('\\"'):
        text = text[:-1] + '\\"'

    # 4. Prevent trailing backslashes from escaping the closing quote
    if text.endswith('\\') and not text.endswith('\\\\'):
        text = text + '\\'

    return text
