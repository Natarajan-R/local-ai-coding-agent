"""Registry of tools the agent can call, with Ollama-compatible schemas."""
from __future__ import annotations

import asyncio
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..errors import ToolError
from ..perception.lsp import LSPClient
from .patcher import commit_and_write
from .utils import Tool, ToolResult

logger = logging.getLogger(__name__)

# Backward-compatible re-exports so existing `from .registry import` keep working.
from .utils import truncate as _truncate, safe_unescape, normalize_async_scaffolding as _normalize_async_scaffolding
from .utils import restore_signature_annotations as _restore_signature_annotations  # noqa: F401
from .simple_handlers import HandlerContext  # noqa: F401 – public API


try:
    from rope.base.project import Project  # noqa: F401 – used in file_edit_handlers
    HAS_ROPE = True
except ImportError:
    HAS_ROPE = False


class ToolRegistry:
    """Holds the concrete tools and dispatches calls to them.

    All handler logic has been extracted into dedicated modules.  This class is
    now responsible only for:
      1. Storing registry state (tools dict, mutation lock, edit-miss counters).
      2. Creating a :class:`HandlerContext` and wiring it to extracted handlers.
      3. Dispatching tool calls by name to the correct handler.
    """

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
        self.memory = memory
        self.approval_callback = approval_callback

        if indexer is None:
            from ..perception.indexer import WorkspaceIndexer
            indexer = WorkspaceIndexer(self.workspace)
        self.indexer = indexer
        self._symbols = None  # lazily-built SymbolIndex

        self._mutation_lock = asyncio.Lock()
        self._edit_misses: Dict[str, int] = {}
        self.tools: Dict[str, Tool] = {}

        self._register_core_tools()
        self._register_exploration_tools()
        if self.memory is not None and getattr(self.memory, "enabled", False):
            self._register_memory_tools()
        if self.lsp:
            self._register_lsp_tools()

    # -- context builder -----------------------------------------------------

    def _ctx(self) -> HandlerContext:
        """Build a fresh HandlerContext pointing back at *this* registry."""
        return HandlerContext.from_registry(self)

    # -- backward-compatible helpers (used by tests) -------------------------

    def _safe_path(self, path: str):
        """Validate ``path`` stays in the workspace. Kept for backward compat with tests."""
        from .file_edit_handlers import safe_path
        return safe_path(self._ctx(), path)

    def _safe_write_path(self, path: str):
        """Like ``_safe_path``, but also refuse writes to a protected file."""
        from .file_edit_handlers import safe_write_path
        return safe_write_path(self._ctx(), path)

    async def _write_file(self, path: str, content: str):
        """Backward-compatible wrapper — calls the extracted handler."""
        from .simple_handlers import write_file
        return await write_file(self._ctx(), path, content)

    # -- registration --------------------------------------------------------

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def _register_core_tools(self) -> None:
        from . import simple_handlers as _sh
        from . import file_edit_handlers as _fe
        from . import rename_handlers as _rn

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
            _sh.read_file,
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
            _sh.solve_constraints,
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
            _sh.write_file,
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
            _fe.search_replace,
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
            _fe.edit_lines,
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
            _fe.replace_all,
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
            _rn.rename_symbol,
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
            _sh.read_symbol,
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
            _fe.add_docstring,
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
            _sh.list_files,
        ))
        self.register(Tool(
            "run_command",
            "Run a shell command in the sandbox and return its output.",
            {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            _sh.run_command,
        ))
        self.register(Tool(
            "finish",
            "Signal that the task is complete. Provide a short summary of what changed.",
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
            _sh.finish,
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
                _fe.add_parameter,
            ))

    def _register_exploration_tools(self) -> None:
        from . import simple_handlers as _sh

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
            _sh.search_text,
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
            _sh.outline,
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
            _sh.find_symbol,
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
            _sh.find_importers,
        ))

    def _register_memory_tools(self) -> None:
        from . import simple_handlers as _sh

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
            _sh.remember,
        ))

    def _register_lsp_tools(self) -> None:
        from . import lsp_handlers as _lsp

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
            _lsp.find_definition,
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
            _lsp.find_references,
        ))
        self.register(Tool(
            "get_diagnostics",
            "Retrieve current compiler and linting diagnostics (errors, warnings) in the project workspace.",
            {"type": "object", "properties": {}},
            _lsp.get_diagnostics,
        ))

    # -- symbol index (lazy) -------------------------------------------------

    def _symbol_index(self):
        if self._symbols is None:
            from ..perception.symbols import SymbolIndex
            self._symbols = SymbolIndex(self.indexer)
        return self._symbols

    # -- mutation infrastructure (used by extracted handlers via ctx.reg) -----

    async def _atomic_commit_and_refresh(self, target: Path, content: str) -> None:
        """Atomically commit file changes, notify LSP, and refresh symbol indexes under a lock."""
        async with self._mutation_lock:
            await asyncio.to_thread(
                commit_and_write, self.workspace, target, content, 'utf-8'
            )
            if self.lsp:
                try:
                    await self.lsp.open_document(target, content)
                    await self.lsp.change_document(target, content)
                except Exception:
                    logger.warning("Failed to notify LSP of changes to %s", target)
            if self._symbols is not None:
                self._symbols.refresh()

    # -- dispatch ------------------------------------------------------------

    def get_descriptions(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        logger.debug("Executing tool %s args=%s", tool_name, args)
        tool = self.tools.get(tool_name)
        if tool is None:
            return ToolResult(False, f"Unknown tool: {tool_name}")
        try:
            if tool.needs_ctx:
                kwargs = {"ctx": self._ctx(), **(args or {})}
            else:
                kwargs = args or {}
            if inspect.iscoroutinefunction(tool.handler):
                return await tool.handler(**kwargs)
            return tool.handler(**kwargs)
        except ToolError as exc:
            return ToolResult(False, f"Error: {exc}")
        except TypeError as exc:
            return ToolResult(False, f"Bad arguments for {tool_name}: {exc}")
        except Exception as exc:
            logger.exception("Tool %s failed", tool_name)
            return ToolResult(False, f"Unexpected error in {tool_name}: {exc}")
