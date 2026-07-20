"""Registry of tools the agent can call, with Ollama-compatible schemas."""
from __future__ import annotations

import ast
import asyncio
import inspect
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import url2pathname

from ..errors import ToolError
from ..perception.analysis import syntax_note
from ..perception.indexer import IGNORE_DIRS
from ..perception.lsp import LSPClient
from .patcher import _strip_regex_escapes, apply_and_diff, make_diff, apply_line_edit

try:
    from rope.base.project import Project
    from rope.refactor.change_signature import ChangeSignature, ArgumentAdder
    HAS_ROPE = True
except ImportError:
    HAS_ROPE = False

logger = logging.getLogger(__name__)

# Cap on returned content to keep prompts within the model context window.
MAX_READ_CHARS = 20_000
MAX_OUTPUT_CHARS = 8_000


@dataclass
class ToolResult:
    ok: bool
    content: str
    is_final: bool = False


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., ToolResult]

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def safe_unescape(s: str) -> str:
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


def _restore_signature_annotations(
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
    import copy
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


# Regex to normalize duplicate async keywords (e.g. async async def) emitted by model scaffolding.
# Note: This can cosmetically collapse the pattern inside string literals, which is low-risk.
_MULTIPLE_ASYNC_RE = re.compile(r"\b(async\s+){2,}def\b")


def _normalize_async_scaffolding(content: str) -> str:
    return _MULTIPLE_ASYNC_RE.sub("async def", content)



def _undocumented(source: str) -> List[str]:
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
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified = f"{prefix}{child.name}"
                if not ast.get_docstring(child):
                    missing.append(qualified)
                walk(child, prefix=f"{qualified}.")

    walk(tree)
    return missing


class ToolRegistry:
    """Holds the concrete tools and dispatches calls to them."""

    def __init__(
        self,
        sandbox,
        policy,
        workspace: Path,
        lsp: Optional[LSPClient] = None,
        approval_callback: Optional[Callable[[str, str], Any]] = None,
        indexer=None,
        memory=None,
    ) -> None:
        self.sandbox = sandbox
        self.policy = policy
        self.workspace = Path(workspace).resolve()
        self.lsp = lsp
        self.memory = memory  # persistent MemoryStore (optional)
        # Async approval hook (e.g. web UI). When set, run_command approval is
        # awaited through it instead of the synchronous console prompt.
        self.approval_callback = approval_callback
        # Workspace indexer powers the on-demand exploration tools; created lazily
        # if not injected so the registry works standalone (e.g. in tests).
        if indexer is None:
            from ..perception.indexer import WorkspaceIndexer
            indexer = WorkspaceIndexer(self.workspace)
        self.indexer = indexer
        self._symbols = None  # lazily-built SymbolIndex
        self.tools: Dict[str, Tool] = {}
        self._register_core_tools()
        self._register_exploration_tools()
        if self.memory is not None and getattr(self.memory, "enabled", False):
            self._register_memory_tools()
        if self.lsp:
            self._register_lsp_tools()

    # -- registration --------------------------------------------------------
    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def _register_core_tools(self) -> None:
        self.register(Tool(
            "read_file",
            "Read a UTF-8 text file from the workspace. Optionally pass start_line "
            "and end_line (1-indexed, inclusive) to read only a slice of a large file.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace"},
                    "start_line": {"type": "integer", "description": "First line to read (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Last line to read (1-indexed, inclusive)"},
                },
                "required": ["path"],
            },
            self._read_file,
        ))
        self.register(Tool(
            "solve_constraints",
            "Solve a constraint or optimisation problem exactly, using a real solver "
            "(z3). Use this instead of reasoning it out by hand whenever the answer "
            "requires search over combinations: scheduling and timetabling, resource "
            "or shift allocation, picking dependency versions that satisfy ranges, "
            "checking whether a configuration is even possible, or maximising a value "
            "under limits. Declare each variable (type int/real/bool, with min/max or "
            "an explicit domain list), then give constraints as ordinary expressions, "
            "e.g. 'start_b >= start_a + 3' or 'x + y <= 10'. Returns a concrete "
            "assignment, or tells you the constraints conflict -- which is a real "
            "answer, not a failure. Do NOT hand-solve a problem you can state here.",
            {
                "type": "object",
                "properties": {
                    "variables": {
                        "type": "array",
                        "description": "Variables to solve for. Each: {name, type: int|real|bool, "
                                       "and optionally min, max, or domain: [allowed values]}",
                        "items": {"type": "object"},
                    },
                    "constraints": {
                        "type": "array",
                        "description": "Expressions that must all hold, e.g. ['x + y == 10', 'x > y']. "
                                       "Use variables, numbers, + - * / % **, comparisons, and/or/not.",
                        "items": {"type": "string"},
                    },
                    "all_different": {
                        "type": "array",
                        "description": "Names of variables that must all take different values",
                        "items": {"type": "string"},
                    },
                    "minimize": {"type": "string", "description": "Expression to minimise (optional)"},
                    "maximize": {"type": "string", "description": "Expression to maximise (optional)"},
                },
                "required": ["variables", "constraints"],
            },
            self._solve_constraints,
        ))
        self.register(Tool(
            "write_file",
            "Create or overwrite a file in the workspace with the given content.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            self._write_file,
        ))
        self.register(Tool(
            "search_replace",
            "Replace an exact block of text in a file. The search block must be unique. "
            "`search` is LITERAL text, NOT a regular expression — copy it verbatim from "
            "the file and do not escape any characters.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "search": {
                        "type": "string",
                        "description": "Literal text to find, copied verbatim from the "
                                       "file. NOT a regex: write record[\"id\"], never "
                                       "record\\[\"id\"\\].",
                    },
                    "replace": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "search", "replace"],
            },
            self._search_replace,
        ))
        self.register(Tool(
            "edit_lines",
            "Replace a range of lines in a file. Specifying the target line range (1-indexed, inclusive) "
            "and the exact expected 'search' block of text inside that range. If the lines shifted "
            "due to previous edits, the tool automatically scans the neighborhood to adjust the line numbers safely.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer", "description": "The starting line number of the target block (1-indexed)"},
                    "end_line": {"type": "integer", "description": "The ending line number of the target block (1-indexed)"},
                    "search": {"type": "string", "description": "The exact current text of the lines to be replaced (without line numbers)"},
                    "replace": {"type": "string", "description": "The replacement text"},
                },
                "required": ["path", "start_line", "end_line", "search", "replace"],
            },
            self._edit_lines,
        ))
        self.register(Tool(
            "replace_all",
            "Rename or replace EVERY occurrence of an exact string in one file, in a "
            "single step. Use this instead of search_replace when the same text appears "
            "more than once (renaming a field, a variable, a function). Returns the "
            "number of occurrences changed and a diff. `old` is LITERAL text, NOT a "
            "regular expression — do not escape any characters.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {
                        "type": "string",
                        "description": "Literal text to replace everywhere. NOT a regex: "
                                       "write record[\"id\"], never record\\[\"id\"\\].",
                    },
                    "new": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old", "new"],
            },
            self._replace_all,
        ))
        self.register(Tool(
            "rename_symbol",
            "Rename a symbol (class, function, variable, field) across the WHOLE repository "
            "in one step — every file, every occurrence. Use this for any rename that spans "
            "more than one file: it is the only way to do it correctly, because renaming in "
            "one file at a time breaks the others until the last edit lands. Matches whole "
            "words only, so renaming `Foo` never touches `FooBar` or `my_foo_thing`. `old` "
            "and `new` are LITERAL identifiers, NOT regular expressions — do not escape "
            "anything. Returns the number of occurrences changed in each file.",
            {
                "type": "object",
                "properties": {
                    "old": {
                        "type": "string",
                        "description": "The existing identifier, exactly as written in the "
                                       "code, e.g. RetryCallState",
                    },
                    "new": {
                        "type": "string",
                        "description": "The new identifier, e.g. RetryState",
                    },
                },
                "required": ["old", "new"],
            },
            self._rename_symbol,
        ))
        self.register(Tool(
            "read_symbol",
            "Show the exact source of ONE function, method or class, by name. Use this "
            "instead of `search_text` when you know WHAT you want to change: it addresses "
            "a class's own method (Class.method), which grepping for `def __init__` cannot "
            "— that finds every constructor in the file and you will edit the wrong one. "
            "The text it returns is safe to copy verbatim into a `search_replace`.",
            {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Name of a function or class, or Class.method for a "
                                       "method (e.g. RetryCallState.__init__)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Optional file to look in; omit to search the workspace",
                    },
                },
                "required": ["symbol"],
            },
            self._read_symbol,
        ))
        self.register(Tool(
            "add_docstring",
            "Add (or replace) the docstring of ONE function, method or class, without "
            "touching anything else. This is the correct tool for documenting code: it "
            "finds the definition itself and inserts the docstring at the right "
            "indentation, so you cannot break the file's syntax. Pass the docstring TEXT "
            "only — no quotes, no def line, no surrounding code. For a method inside a "
            "class use Class.method (e.g. Shape.describe).",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File to edit"},
                    "symbol": {
                        "type": "string",
                        "description": "Name of the function, class, or Class.method",
                    },
                    "docstring": {
                        "type": "string",
                        "description": "The docstring body WITHOUT triple quotes, e.g. "
                                       "'Return the area of a circle.\\n\\nArgs:\\n    "
                                       "r (float): The radius.'",
                    },
                },
                "required": ["path", "symbol", "docstring"],
            },
            self._add_docstring,
        ))
        self.register(Tool(
            "list_files",
            "List files in the workspace (recursively, ignoring VCS and caches). "
            "Pass an optional directory to scope the listing to a subtree.",
            {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Optional subdirectory to list"},
                },
            },
            self._list_files,
        ))
        self.register(Tool(
            "run_command",
            "Run a shell command in the sandbox and return its output.",
            {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            self._run_command,
        ))
        self.register(Tool(
            "finish",
            "Signal that the task is complete. Provide a short summary of what changed.",
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            self._finish,
        ))
        if HAS_ROPE:
            self.register(Tool(
                "add_parameter",
                "Add a parameter to a function or method signature and automatically rewrite "
                "all its call sites across the whole repository in a single step. "
                "Pass the symbol name as Class.method or function_name, and specify the "
                "parameter name (which can include a type hint like `c: int`), default value "
                "in the signature, and value to pass at existing call sites.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The file containing the function/method definition"},
                        "symbol": {
                            "type": "string",
                            "description": "Name of the function/class method (e.g., 'Calculator.add' or 'hello')",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the new parameter, optionally with a type hint (e.g., 'caller_name: str')",
                        },
                        "default": {
                            "type": "string",
                            "description": "The default value in the signature, or 'None' / empty if no default (e.g., '\"\"' or 'None')",
                        },
                        "value": {
                            "type": "string",
                            "description": "The literal value passed to EVERY existing call site. "
                                           "If the task asks for a sensible/meaningful value, put it "
                                           "HERE — e.g. '\"USD\"' for a currency — do not add a "
                                           "placeholder and then hand-edit the sites afterwards. "
                                           "Every call site will pass exactly this value.",
                        },
                    },
                    "required": ["path", "symbol", "name", "value"],
                },
                self._add_parameter,
            ))

    def _register_exploration_tools(self) -> None:
        self.register(Tool(
            "search_text",
            "Search file contents across the workspace (grep-like). Returns "
            "matching path:line: text. Use this to locate code in a large repo.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for"},
                    "max_results": {"type": "integer", "description": "Cap on matches (default 50)"},
                },
                "required": ["query"],
            },
            self._search_text,
        ))
        self.register(Tool(
            "outline",
            "Show the code outline (class/function signatures) of a single file "
            "without its bodies — cheaper than read_file for understanding shape.",
            {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            self._outline,
        ))
        self.register(Tool(
            "find_symbol",
            "Find where a class/function/method is DEFINED, by name (exact, else "
            "substring). Returns kind and path:line across the whole repo.",
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            self._find_symbol,
        ))
        self.register(Tool(
            "find_importers",
            "Find which files IMPORT a given module or symbol (Python) — impact "
            "analysis before changing it.",
            {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            self._find_importers,
        ))

    def _symbol_index(self):
        if self._symbols is None:
            from ..perception.symbols import SymbolIndex
            self._symbols = SymbolIndex(self.indexer)
        return self._symbols

    def _register_memory_tools(self) -> None:
        self.register(Tool(
            "remember",
            "Save a durable fact for FUTURE runs of this project: a convention, a "
            "lesson learned, or a preference. Use sparingly — only for facts that "
            "will genuinely help next time (not per-task details).",
            {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The fact to remember (one sentence)"},
                    "kind": {
                        "type": "string",
                        "enum": ["convention", "lesson", "preference", "note"],
                        "description": "Category of the fact",
                    },
                },
                "required": ["text"],
            },
            self._remember,
        ))

    def _remember(self, text: str, kind: str = "note") -> ToolResult:
        if self.memory is None:
            return ToolResult(False, "Memory is disabled.")
        entry = self.memory.add(text, kind=kind)
        if entry is None:
            return ToolResult(True, "Already remembered (or empty) — nothing added.")
        return ToolResult(True, f"Remembered [{entry.kind}]: {entry.text}")

    # -- dispatch ------------------------------------------------------------
    def get_descriptions(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        logger.debug("Executing tool %s args=%s", tool_name, args)
        tool = self.tools.get(tool_name)
        if tool is None:
            return ToolResult(False, f"Unknown tool: {tool_name}")
        try:
            if inspect.iscoroutinefunction(tool.handler):
                return await tool.handler(**(args or {}))
            return tool.handler(**(args or {}))
        except ToolError as exc:
            return ToolResult(False, f"Error: {exc}")
        except TypeError as exc:
            return ToolResult(False, f"Bad arguments for {tool_name}: {exc}")
        except Exception as exc:  # defensive - never crash the loop on a tool
            logger.exception("Tool %s failed", tool_name)
            return ToolResult(False, f"Unexpected error in {tool_name}: {exc}")

    # -- handlers ------------------------------------------------------------
    def _safe_path(self, path: str) -> Path:
        if not self.policy.validate_path(path):
            raise ToolError(f"Path '{path}' is outside the workspace")
        return self.policy.resolve_path(path)

    async def _solve_constraints(
        self,
        variables: Any,
        constraints: Any,
        all_different: Any = None,
        minimize: Optional[str] = None,
        maximize: Optional[str] = None,
    ) -> ToolResult:
        from .solver import solve, SolverError
        try:
            solution = await asyncio.to_thread(
                solve, variables, constraints, all_different, minimize, maximize
            )
        except SolverError as exc:
            # State the fix, not just the fault -- a bare error sends the model
            # round the loop re-sending the same malformed problem.
            return ToolResult(False, f"Could not solve: {exc}")
        except Exception as exc:  # pragma: no cover - solver robustness
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

    async def _read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> ToolResult:
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if not target.is_file():
            return ToolResult(False, f"Not a file: {path}")
        # Read off the event loop so a large file can't stall streaming / the web UI.
        text = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")

        if start_line is None and end_line is None:
            return ToolResult(True, _truncate(text, MAX_READ_CHARS))

        # Return a 1-indexed, inclusive slice with line-number gutters.
        lines = text.splitlines()
        start = max(1, start_line or 1)
        end = min(len(lines), end_line or len(lines))
        if start > end:
            return ToolResult(False, f"Invalid range: start_line {start} > end_line {end}")
        numbered = [f"{i}\t{lines[i - 1]}" for i in range(start, end + 1)]
        header = f"[{path} lines {start}-{end} of {len(lines)}]\n"
        return ToolResult(True, header + _truncate("\n".join(numbered), MAX_READ_CHARS))

    async def _write_file(self, path: str, content: str) -> ToolResult:
        if path.endswith(".py"):
            content = _normalize_async_scaffolding(content)
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_text, content, encoding="utf-8")
        if self.lsp:  # the LSP layer routes each file to its language's server
            try:
                await self.lsp.open_document(target, content)
                await self.lsp.change_document(target, content)
            except Exception:
                pass
        if self._symbols is not None:
            self._symbols.refresh()  # keep the symbol index fresh after edits
        note = syntax_note(path, content)
        self.policy.audit.record("write_file", path=path, bytes=len(content), syntax_ok=not note)
        return ToolResult(True, f"Wrote {len(content)} bytes to {path}{note}")

    async def _search_replace(self, path: str, search: str, replace: str) -> ToolResult:
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if isinstance(search, str):
            search = search.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
            search = safe_unescape(search)
        if isinstance(replace, str):
            replace = replace.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
            replace = safe_unescape(replace)
        if path.endswith(".py"):
            replace = _normalize_async_scaffolding(replace)
        original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
        updated, diff = apply_and_diff(original, search, replace, path)
        await asyncio.to_thread(target.write_text, updated, encoding="utf-8")
        if self.lsp:  # the LSP layer routes each file to its language's server
            try:
                await self.lsp.open_document(target, updated)
                await self.lsp.change_document(target, updated)
            except Exception:
                pass
        if self._symbols is not None:
            self._symbols.refresh()
        note = syntax_note(path, updated)
        self.policy.audit.record("search_replace", path=path, syntax_ok=not note)
        return ToolResult(True, f"Applied edit to {path}:\n{_truncate(diff, MAX_OUTPUT_CHARS)}{note}")

    async def _edit_lines(self, path: str, start_line: int, end_line: int, search: str, replace: str) -> ToolResult:
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if isinstance(search, str):
            search = search.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
            search = safe_unescape(search)
        if isinstance(replace, str):
            replace = replace.replace('\\\\n', '\\n').replace('\\\\t', '\\t')
            replace = safe_unescape(replace)
        if path.endswith(".py"):
            replace = _normalize_async_scaffolding(replace)
        original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
        updated = apply_line_edit(original, start_line, end_line, search, replace)
        diff = make_diff(original, updated, path)
        await asyncio.to_thread(target.write_text, updated, encoding="utf-8")
        if self.lsp:
            try:
                await self.lsp.open_document(target, updated)
                await self.lsp.change_document(target, updated)
            except Exception:
                pass
        if self._symbols is not None:
            self._symbols.refresh()
        note = syntax_note(path, updated)
        self.policy.audit.record("edit_lines", path=path, syntax_ok=not note)
        return ToolResult(True, f"Applied line edit to {path}:\n{_truncate(diff, MAX_OUTPUT_CHARS)}{note}")

    def _read_symbol(self, symbol: str, path: Optional[str] = None) -> ToolResult:
        """Return the exact source of ONE function, method or class.

        `find_symbol` answers *where* (`__init__.py:567`) and never *what*, and it
        has no way to say "the constructor **of this class**". So, asked to change
        `RetryCallState.__init__`, the model did the only thing it could: grepped
        `def __init__`, got every constructor in the file, and edited the wrong
        one — breaking 144 tests without ever reading a line.

        Given a name it cannot address, a model does not stop. It guesses.
        """
        targets = [self._safe_path(path)] if path else [
            p for p in sorted(self.workspace.rglob("*.py"))
            if not any(part in IGNORE_DIRS for part in p.relative_to(self.workspace).parts)
        ]
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
            if node is None:
                continue
            lines = source.splitlines()[node.lineno - 1: node.end_lineno]
            rel = file.relative_to(self.workspace)
            return ToolResult(
                True,
                f"{rel}:{node.lineno}-{node.end_lineno}  {symbol}\n"
                + _truncate("\n".join(lines), MAX_READ_CHARS),
            )

        where = f" in {path}" if path else " anywhere in the workspace"
        return ToolResult(False, f"No function, method or class named {symbol!r} found{where}. "
                                 f"For a method inside a class, use Class.method.")

    async def _add_docstring(self, path: str, symbol: str, docstring: str) -> ToolResult:
        """Insert or replace one definition's docstring, AST-precisely.

        Documenting a file scored 0/9 for two compounding reasons. First, the model's
        docstring edit was silently dropped by the parser (a raw `\"\"\"` is illegal
        inside a JSON string) — fixed there. Once its edits actually landed it reached
        5/7, and the remaining failures were syntax errors: to insert a docstring with
        `search_replace` the model must reproduce the def line and invent the body's
        indentation, and it gets that wrong often enough to break the file.

        Neither the model nor the prompt is the fix. The fix is a tool at the
        granularity of the job: name a symbol, hand over prose, let the AST decide
        where it goes and how far to indent it.
        """
        target = self._safe_path(path)
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
        # The body's own indentation is the ground truth — never guess it.
        first = node.body[0]
        indent = " " * first.col_offset

        existing = ast.get_docstring(node, clean=False)
        text = docstring.strip('"\' \n')
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
        try:  # never hand back a file we just broke
            ast.parse(updated)
        except SyntaxError as exc:
            return ToolResult(False, f"Refusing the edit: it would break {path} ({exc})")

        await asyncio.to_thread(target.write_text, updated, encoding="utf-8")
        if self.lsp:
            try:
                await self.lsp.open_document(target, updated)
                await self.lsp.change_document(target, updated)
            except Exception:
                pass
        if self._symbols is not None:
            self._symbols.refresh()

        # Tell it what is still undocumented, every time. The model can see the
        # methods (`outline` lists them) and still stops early — it stops because it
        # believes it is finished, and a prompt rule saying "be thorough" measures
        # zero against that. So don't ask; report. A tool result is fresh, specific
        # and about the file in front of it, which a standing instruction is not.
        remaining = _undocumented(updated)
        note = (
            f"\nStill undocumented in {path}: {', '.join(remaining)}"
            if remaining else f"\nEvery function, method and class in {path} now has a docstring."
        )
        return ToolResult(True, f"{verb} docstring for {symbol} in {path}.\n"
                                f"{make_diff(source, updated, path)}{note}")

    async def _add_parameter(
        self,
        path: str,
        symbol: str,
        name: str,
        value: str,
        default: Optional[str] = None,
    ) -> ToolResult:
        """Add a parameter to a function or method signature. 
        This tool automatically refactors and updates the signature AND all call sites across the workspace. 
        DO NOT manually edit call sites after running this tool.
        """
        # Validate/normalize value to prevent NameError (bare string literal without quotes)
        value = value.strip()
        try:
            expr = ast.parse(value, mode="eval")
            if isinstance(expr.body, ast.Name):
                if expr.body.id not in ("True", "False", "None"):
                    value = f'"{value}"'
        except SyntaxError:
            value = f'"{value}"'

        # Apply same normalization to default if provided
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

        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")

        content = await asyncio.to_thread(target.read_text, encoding="utf-8")
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            return ToolResult(False, f"{path} does not parse, so it cannot be edited: {exc}")

        # Resolve symbol name or Class.method to an AST node
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

        # Idempotency guard. The model, unsure whether the first call worked, often
        # calls add_parameter again — and Rope will happily add a SECOND `currency`,
        # producing `def __init__(self, ..., currency, currency)` and breaking every
        # call site. Measured: this was the whole thrash on a small project where the
        # model fired add_parameter 3×. If the parameter is already there, it's done.
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

        # Rope strips parameter annotations from the signature it edits, so capture
        # them now, while the original is still intact, to restore afterwards.
        _orig_annotations = {
            a.arg: ast.unparse(a.annotation)
            for a in (list(node.args.posonlyargs) + list(node.args.args)
                      + list(node.args.kwonlyargs))
            if a.annotation is not None
        }
        _orig_return = ast.unparse(node.returns) if node.returns is not None else None
        # If the new parameter carries its own hint ("caller_name: str"), keep it too.
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
            proj = Project(str(self.workspace))
            try:
                rel_path = str(target.relative_to(self.workspace))
                resource = proj.get_resource(rel_path)
                refactor = ChangeSignature(proj, resource, char_offset)

                # Append argument at the end of existing args list
                existing_args = refactor.get_args()
                insert_idx = len(existing_args)

                # Add parameter
                adder = ArgumentAdder(insert_idx, name, default=default, value=value)
                changes = refactor.get_changes([adder])
                proj.do(changes)

                # Track changed resources to notify LSP
                for r in changes.get_changed_resources():
                    if not r.is_folder():
                        changed_files.append(Path(r.real_path))
            finally:
                proj.close()

        try:
            await asyncio.to_thread(run_rope)
        except Exception as exc:
            return ToolResult(False, f"Rope refactoring failed: {exc}")

        # Rope drops parameter annotations from the signature it rewrote. Restore
        # them so a typed library does not silently lose its types (pytest can't
        # see it — the suite stays green while the annotations are gone).
        restored = await asyncio.to_thread(target.read_text, encoding="utf-8")
        reannotated = _restore_signature_annotations(
            restored, symbol, _orig_annotations, _orig_return
        )
        if reannotated != restored:
            await asyncio.to_thread(target.write_text, reannotated, encoding="utf-8")

        if self._symbols is not None:
            self._symbols.refresh()

        # Generate a diff for the modified definition file
        new_content = await asyncio.to_thread(target.read_text, encoding="utf-8")
        diff = make_diff(content, new_content, path)

        # Notify LSP server of changes in all modified files
        if self.lsp:
            for filepath in changed_files:
                try:
                    updated_text = await asyncio.to_thread(filepath.read_text, encoding="utf-8")
                    await self.lsp.open_document(filepath, updated_text)
                    await self.lsp.change_document(filepath, updated_text)
                except Exception:
                    pass

        # Name every file that was updated, and tell the model the refactor is
        # COMPLETE. Measured failure mode (SR4/VS3): after a correct add_parameter
        # the model goes hunting for call sites to fix by hand — but they are
        # already done — and double-edits them into broken code. A vague "updated
        # call sites" invites that; an explicit list plus "do not edit these
        # yourself" stops it. Same fix that took add_docstring 5/7 -> 7/7: a tool
        # result is evidence, so make it specific and directive.
        try:
            updated = sorted(
                str(Path(f).resolve().relative_to(self.workspace)) for f in changed_files
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

    async def _apply_workspace_edit(self, edit: Dict[str, Any]) -> List[str]:
        """Apply an LSP WorkspaceEdit structure to workspace files.
        Returns a list of workspace-relative paths of modified files.
        """
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
            return []

        applied_paths = []
        for uri, edits in file_edits.items():
            if not uri.startswith("file://"):
                continue
            parsed = urlparse(uri)
            path_str = url2pathname(parsed.path)
            filepath = Path(path_str).resolve()
            if not filepath.exists() or not filepath.is_relative_to(self.workspace):
                continue

            content = await asyncio.to_thread(filepath.read_text, encoding="utf-8")

            # Sort edits in reverse start position to preserve offsets
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

                # Apply text edit
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

            updated_content = "".join(lines)
            await asyncio.to_thread(filepath.write_text, updated_content, encoding="utf-8")

            # Notify LSP server of the changed document
            if self.lsp:
                try:
                    await self.lsp.open_document(filepath, updated_content)
                    await self.lsp.change_document(filepath, updated_content)
                except Exception:
                    pass

            rel_path = str(filepath.relative_to(self.workspace))
            applied_paths.append(rel_path)

        if self._symbols is not None:
            self._symbols.refresh()

        return applied_paths

    async def _rename_symbol(self, old: str, new: str) -> ToolResult:
        """Rename an identifier across every file in the workspace, in one call.
        Uses LSP textDocument/rename when active, falling back to regex word replacement.
        """
        if not old:
            return ToolResult(False, "`old` must not be empty")
        if not new:
            return ToolResult(False, "`new` must not be empty")
        if old == new:
            return ToolResult(False, "`old` and `new` are identical — nothing to do")

        # 1. Try LSP rename first
        if self.lsp:
            hits = []
            if self._symbols is not None:
                hits = self._symbols.find_definition(old)

            if hits:
                hit = hits[0]
                target_path = self.workspace / hit.path
                if target_path.exists():
                    try:
                        content = await asyncio.to_thread(target_path.read_text, encoding="utf-8")
                        lines = content.splitlines()
                        line_idx = hit.line - 1
                        if 0 <= line_idx < len(lines):
                            line_text = lines[line_idx]
                            col_offset = line_text.find(old)
                            if col_offset != -1:
                                workspace_edit = await self.lsp.rename(target_path, line_idx, col_offset, new)
                                if workspace_edit:
                                    applied = await self._apply_workspace_edit(workspace_edit)
                                    if applied:
                                        return ToolResult(
                                            True,
                                            f"Semantically renamed {old!r} to {new!r} via LSP across "
                                            f"{len(applied)} file(s):\n" + "\n".join(f"  {f}" for f in applied)
                                        )
                    except Exception as exc:
                        logger.warning("LSP rename failed, falling back to regex: %s", exc)

        # 2. Fall back to regex word-boundary replacement
        pattern = re.compile(rf"\b{re.escape(old)}\b")
        changed: List[Any] = []
        total = 0
        for path in sorted(self.workspace.rglob("*")):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.relative_to(self.workspace).parts):
                continue
            try:
                content = await asyncio.to_thread(path.read_text, encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable — not source
            count = len(pattern.findall(content))
            if not count:
                continue
            await asyncio.to_thread(
                path.write_text, pattern.sub(new, content), encoding="utf-8"
            )
            changed.append((str(path.relative_to(self.workspace)), count))
            total += count

        if not total:
            return ToolResult(
                False,
                f"No whole-word occurrences of {old!r} found in the workspace. Check the "
                f"spelling — `old` is a literal identifier, not a regex or a substring.",
            )

        if self._symbols is not None:
            self._symbols.refresh()

        lines = "\n".join(f"  {p}: {c}" for p, c in changed)
        return ToolResult(
            True,
            f"Renamed {old!r} to {new!r}: {total} occurrence(s) across "
            f"{len(changed)} file(s).\n{lines}",
        )

    def _list_files(self, directory: Optional[str] = None) -> ToolResult:
        if directory and not self.policy.validate_path(directory):
            return ToolResult(False, f"Path '{directory}' is outside the workspace")
        files = self.indexer.list_files(directory)
        rows = [str(f.relative_to(self.workspace)) for f in files]
        if not rows:
            scope = f" under {directory}" if directory else ""
            return ToolResult(True, f"(no files{scope})")
        return ToolResult(True, _truncate("\n".join(rows), MAX_OUTPUT_CHARS))

    def _search_text(self, query: str, max_results: int = 50) -> ToolResult:
        try:
            max_results = max(1, min(int(max_results), 200))
        except (TypeError, ValueError):
            max_results = 50
        matches = self.indexer.search_text(query, max_results=max_results)
        if not matches:
            return ToolResult(True, f"No matches for {query!r}.")
        rows = [f"{rel}:{lineno}: {line}" for rel, lineno, line in matches]
        header = f"{len(matches)} match(es) for {query!r}:\n"
        return ToolResult(True, header + _truncate("\n".join(rows), MAX_OUTPUT_CHARS))

    def _outline(self, path: str) -> ToolResult:
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if not target.is_file():
            return ToolResult(False, f"Not a file: {path}")
        outline = self.indexer.outline(target)
        if not outline:
            return ToolResult(True, f"(no symbols found in {path}; use read_file to view it)")
        return ToolResult(True, f"# Outline of {path}\n{_truncate(outline, MAX_OUTPUT_CHARS)}")

    def _find_symbol(self, name: str) -> ToolResult:
        index = self._symbol_index()
        hits = index.find_definition(name)
        if not hits:
            hits = index.search(name)  # fall back to substring
        if not hits:
            return ToolResult(True, f"No symbol matching {name!r} found.")
        rows = [f"{h.path}:{h.line}: {h.kind} {h.name}" for h in hits]
        return ToolResult(True, f"{len(hits)} definition(s) for {name!r}:\n" + "\n".join(rows))

    # Source suffixes that mark a *file name*. An import records the *module*
    # ("from models import User" -> "models"), never the file ("models.py").
    _MODULE_SUFFIXES = (".py", ".pyi", ".js", ".jsx", ".mjs", ".ts", ".tsx", ".go",
                        ".rs", ".java", ".rb", ".c", ".h", ".cpp", ".cs")

    @classmethod
    def _as_module_name(cls, name: str) -> str:
        """Turn whatever the caller has in hand into a module name.

        The model reads a directory listing, so it asks about "models.py" — the only
        name it has seen. The import table is keyed by module, so that lookup matched
        nothing and the tool reported "No files import 'models.py'" for a module three
        files import. A confident false negative is the worst answer an impact-analysis
        tool can give: it says "safe to change" about the thing you are about to break.
        """
        stem = Path(name.strip()).name
        for ext in cls._MODULE_SUFFIXES:
            if stem.endswith(ext) and len(stem) > len(ext):
                return stem[: -len(ext)]
        return name.strip()

    def _find_importers(self, name: str) -> ToolResult:
        module = self._as_module_name(name)
        rows = self._symbol_index().importers(module)
        if not rows:
            return ToolResult(True, f"No files import {module!r}.")
        out = [f"{path}:{line}: imports {module_name}" for path, line, module_name in rows]
        return ToolResult(True, f"{len(rows)} importer(s) of {module!r}:\n" + "\n".join(out))

    async def _replace_all(self, path: str, old: str, new: str) -> ToolResult:
        """Replace every occurrence of `old` in one file.

        `search_replace` deliberately refuses an ambiguous match (Chapter 12): precise,
        reviewable, one site at a time. That is right for "fix this function" and wrong
        for "rename this field", where the model must then build a uniquely-worded edit
        for every site — against a file that changes under it after the first one. It
        can't, and measurably doesn't: a 9-site rename landed 1 of 9.

        So this is the blunt sibling: one call, one file, every occurrence, with the
        count and a diff back so the edit stays reviewable. It is a *substring* replace
        and will happily turn `user_id` inside `user_idx` — hence the diff, and hence
        the evaluator running the tests afterwards.
        """
        target = self._safe_path(path)
        if not target.exists():
            return ToolResult(False, f"File not found: {path}")
        if not old:
            return ToolResult(False, "`old` must not be empty")
        original = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")
        count = original.count(old)
        if count == 0:
            # `old` may be regex-escaped (`record\["id"\]`) rather than literal — models
            # read a field named "old"/"search" as a pattern. Retry unescaped; harmless,
            # because if the file really contained those backslashes we'd have matched.
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
        await asyncio.to_thread(target.write_text, updated, encoding="utf-8")
        if self.lsp:
            try:
                await self.lsp.open_document(target, updated)
                await self.lsp.change_document(target, updated)
            except Exception:
                pass
        if self._symbols is not None:
            self._symbols.refresh()
        diff = make_diff(original, updated, path)
        note = syntax_note(path, updated)
        self.policy.audit.record("replace_all", path=path, count=count, syntax_ok=not note)
        body = f"Replaced {count} occurrence(s) of {old!r} with {new!r} in {path}:\n{diff}"
        if note:
            body += f"\n{note}"
        return ToolResult(True, body)

    async def _run_command(self, command: str) -> ToolResult:
        if self.approval_callback is not None:
            approved = await self.policy.approve_command_async(command, self.approval_callback)
        else:
            approved = self.policy.approve_command(command)
        if not approved:
            return ToolResult(False, f"Command blocked or not approved: {command}")
        # Run off the event loop so a long command doesn't block async callers.
        if hasattr(self.sandbox, "aexec"):
            result = await self.sandbox.aexec(command)
        else:  # pragma: no cover - direct backend without the facade
            result = self.sandbox.exec(command)
        body = self.policy.scrub(result.output) or "(no output)"
        status = "ok" if result.ok else f"exit={result.exit_code}"
        return ToolResult(result.ok, f"[{status}]\n{_truncate(body, MAX_OUTPUT_CHARS)}")

    def _finish(self, summary: str = "") -> ToolResult:
        return ToolResult(True, summary or "Task finished.", is_final=True)

    def _register_lsp_tools(self) -> None:
        self.register(Tool(
            "find_definition",
            "Find the source code definition of the symbol at the given file, line, and character (0-indexed).",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace relative path of the file"},
                    "line": {"type": "integer", "description": "0-indexed line number"},
                    "character": {"type": "integer", "description": "0-indexed character number"},
                },
                "required": ["path", "line", "character"],
            },
            self._find_definition,
        ))
        self.register(Tool(
            "find_references",
            "Find all locations referencing the symbol at the given file, line, and character (0-indexed).",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace relative path of the file"},
                    "line": {"type": "integer", "description": "0-indexed line number"},
                    "character": {"type": "integer", "description": "0-indexed character number"},
                },
                "required": ["path", "line", "character"],
            },
            self._find_references,
        ))
        self.register(Tool(
            "get_diagnostics",
            "Retrieve current compiler and linting diagnostics (errors, warnings) in the project workspace.",
            {"type": "object", "properties": {}},
            self._get_diagnostics,
        ))

    async def _find_definition(self, path: str, line: int, character: int) -> ToolResult:
        if not self.lsp:
            return ToolResult(False, "LSP client not initialized")
        target = self._safe_path(path)
        res = await self.lsp.get_definition(target, line, character)
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
                    if p.is_relative_to(self.workspace):
                        path_str = str(p.relative_to(self.workspace))
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

    async def _find_references(self, path: str, line: int, character: int) -> ToolResult:
        if not self.lsp:
            return ToolResult(False, "LSP client not initialized")
        target = self._safe_path(path)
        res = await self.lsp.get_references(target, line, character)
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
                    if p.is_relative_to(self.workspace):
                        path_str = str(p.relative_to(self.workspace))
                    else:
                        path_str = str(p)
                except Exception:
                    pass
            out.append(f"File: {path_str}, Line {start.get('line', 0) + 1}, Col {start.get('character', 0) + 1}")
        return ToolResult(True, "\n".join(out))

    async def _get_diagnostics(self) -> ToolResult:
        if not self.lsp:
            return ToolResult(False, "LSP client not initialized")
        # The server analyses in the background and pushes results ~1s later, so reading
        # the cache straight after a write reports "No diagnostics reported." for code it
        # has not looked at yet — a clean bill of health the model then acts on.
        await self.lsp.await_diagnostics()
        res = self.lsp.get_all_diagnostics()
        return ToolResult(True, res)
