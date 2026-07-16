"""Registry of tools the agent can call, with Ollama-compatible schemas."""
from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..errors import ToolError
from ..perception.analysis import syntax_note
from ..perception.lsp import LSPClient
from .patcher import _strip_regex_escapes, apply_and_diff, make_diff

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
