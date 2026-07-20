"""Lightweight asynchronous JSON-RPC client for local Language Servers."""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bound LSP request/handshake waits so a missing or wedged server can never hang
# the agent's execution loop.
REQUEST_TIMEOUT = 15.0


class LSPClient:
    """Zero-dependency LSP client that spawns and controls a local server daemon."""

    @staticmethod
    def _resolve_cmd(workspace_dir: Path) -> List[str]:
        # Prefer a pylsp next to the running interpreter, then a workspace venv,
        # then whatever is on PATH.
        active = Path(sys.executable).parent / "pylsp"
        local = Path(workspace_dir).resolve() / ".venv" / "bin" / "pylsp"
        if active.exists():
            return [str(active)]
        if local.exists():
            return [str(local)]
        return ["pylsp"]

    @classmethod
    def resolve_command(cls, workspace_dir: Path, cmd: List[str]) -> List[str]:
        """Resolve a bare server name to an absolute path.

        Checks the running interpreter's bin dir (where `pylsp` lives in this
        venv), then a workspace-local venv, then PATH — so the server can be
        spawned even when it isn't on PATH.
        """
        exe = cmd[0]
        if Path(exe).is_absolute() or "/" in exe:
            return list(cmd)
        for candidate in (
            Path(sys.executable).parent / exe,
            Path(workspace_dir).resolve() / ".venv" / "bin" / exe,
        ):
            if candidate.exists():
                return [str(candidate), *cmd[1:]]
        found = shutil.which(exe)
        return [found, *cmd[1:]] if found else list(cmd)

    @classmethod
    def is_available(cls, workspace_dir: Path, cmd: Optional[List[str]] = None) -> bool:
        """True if the language-server binary can actually be found/launched."""
        resolved = cmd if cmd is not None else cls._resolve_cmd(workspace_dir)
        full = cls.resolve_command(workspace_dir, resolved)
        exe = full[0]
        if Path(exe).is_absolute() or "/" in exe:
            return Path(exe).exists()
        return shutil.which(exe) is not None

    def __init__(self, workspace_dir: Path, cmd: Optional[List[str]] = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        base = cmd if cmd is not None else self._resolve_cmd(self.workspace_dir)
        self.cmd = self.resolve_command(self.workspace_dir, base)

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._id_counter = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        # Mappings of file_uri -> list of diagnostic objects
        self.diagnostics: Dict[str, List[Dict[str, Any]]] = {}
        # URIs synced to the server whose diagnostics push we are still waiting for.
        self._pending_uris: set = set()
        self._ready = asyncio.Event()
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Launch the Language Server process and perform initialization handshake."""
        logger.info("Starting LSP client: %s", self.cmd)
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *self.cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.error("Failed to spawn LSP process %s: %s", self.cmd, exc)
            raise RuntimeError(f"LSP server not available: {exc}") from exc

        self._reader_task = asyncio.create_task(self._read_loop())
        await self._initialize()

    async def stop(self) -> None:
        """Gracefully exit and terminate the LSP server process."""
        self._running = False
        self._ready.clear()
        if self._proc:
            try:
                # Send the shutdown request, then exit notification
                await self._send_request("shutdown", {})
                await self.send_notification("exit", {})
            except Exception:
                pass
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except Exception:
                pass
            self._proc = None

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

    async def _send_request(
        self, method: str, params: Dict[str, Any], timeout: float = REQUEST_TIMEOUT
    ) -> Any:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("LSP server not running")
        self._id_counter += 1
        req_id = self._id_counter
        fut = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = fut

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        body = json.dumps(payload).encode("utf-8")
        logger.debug("LSP sent request: %s", json.dumps(payload))
        headers = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        self._proc.stdin.write(headers + body)
        await self._proc.stdin.drain()

        # Bound every request so a wedged server can never hang the caller
        # (initialize/shutdown included).
        try:
            res = await asyncio.wait_for(fut, timeout=timeout)
            logger.debug("LSP request %d response: %r", req_id, res)
            return res
        finally:
            self._pending_requests.pop(req_id, None)

    async def send_notification(self, method: str, params: Dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("LSP server not running")
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        body = json.dumps(payload).encode("utf-8")
        logger.debug("LSP sent notification: %s", json.dumps(payload))
        headers = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        self._proc.stdin.write(headers + body)
        await self._proc.stdin.drain()

    async def _initialize(self) -> None:
        params = {
            "processId": None,
            "rootUri": self.workspace_dir.as_uri(),
            "rootPath": str(self.workspace_dir),
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": False,
                        "willSave": False,
                        "willSaveWaitUntil": False,
                        "didSave": True,
                    },
                    "definition": {"dynamicRegistration": False},
                    "references": {"dynamicRegistration": False},
                }
            },
        }
        await self._send_request("initialize", params)
        await self.send_notification("initialized", {})
        self._ready.set()
        self._running = True

    async def _wait_ready(self) -> bool:
        """Bounded readiness wait so a missing/wedged server never hangs a call."""
        if not self._running and self._proc is None:
            return False
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=REQUEST_TIMEOUT)
            return True
        except asyncio.TimeoutError:  # pragma: no cover - server wedged
            return False

    async def _read_loop(self) -> None:
        try:
            while self._proc and self._proc.stdout:
                # Parse headers
                content_length = None
                while True:
                    line_bytes = await self._proc.stdout.readline()
                    if not line_bytes:
                        return
                    line = line_bytes.decode("utf-8").strip()
                    if not line:
                        break
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if content_length is None:
                    continue

                body_bytes = await self._proc.stdout.readexactly(content_length)
                body = json.loads(body_bytes.decode("utf-8"))
                logger.debug("LSP received message: %s", json.dumps(body))

                if "id" in body:
                    # Request Response
                    req_id = body["id"]
                    fut = self._pending_requests.pop(req_id, None)
                    if fut and not fut.done():
                        if "error" in body:
                            fut.set_exception(RuntimeError(body["error"]))
                        else:
                            fut.set_result(body.get("result"))
                else:
                    # Server Notification
                    method = body.get("method")
                    if method == "textDocument/publishDiagnostics":
                        params = body.get("params", {})
                        uri = params.get("uri", "")
                        diags = params.get("diagnostics", [])
                        self.diagnostics[uri] = diags
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Error in LSP reader loop: %s", exc)

    # Document Management & Project Sync
    async def open_document(self, path: Path, content: str, language_id: str = "python") -> None:
        """Notify the language server that a document has been opened."""
        if not await self._wait_ready():
            return
        uri = Path(path).resolve().as_uri()
        self._expect_diagnostics(uri)
        params = {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        }
        await self.send_notification("textDocument/didOpen", params)

    def _expect_diagnostics(self, uri: str) -> None:
        """Mark `uri` as awaiting a fresh diagnostics push.

        Analysis is asynchronous: the server answers a didOpen/didChange with a
        `publishDiagnostics` notification a second or so later. Dropping the previous
        entry matters as much as recording the wait — otherwise `await_diagnostics`
        sees the *stale* result sitting in the dict, returns instantly, and the model is
        told about the bug it just fixed (or not told about the one it just wrote).
        """
        self.diagnostics.pop(uri, None)
        self._pending_uris.add(uri)

    async def await_diagnostics(self, timeout: float = 5.0) -> bool:
        """Block until every synced document has fresh diagnostics. True if all arrived.

        Without this, `get_all_diagnostics` reports whatever happens to have landed so
        far — which right after a write is usually *nothing*, i.e. a clean bill of health
        for code the server has not looked at yet. A diagnostics tool that races is worse
        than none: it answers "no errors" when it means "don't know yet".
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while self._pending_uris - set(self.diagnostics):
            if loop.time() >= deadline:
                missing = sorted(self._pending_uris - set(self.diagnostics))
                logger.warning(
                    "Timed out after %.1fs waiting for diagnostics on %d document(s): %s",
                    timeout, len(missing), ", ".join(Path(u[7:]).name for u in missing),
                )
                return False
            await asyncio.sleep(0.05)
        return True

    async def change_document(self, path: Path, content: str) -> None:
        """Sync a document modification to the language server."""
        if not await self._wait_ready():
            return
        uri = Path(path).resolve().as_uri()
        self._expect_diagnostics(uri)
        params = {
            "textDocument": {
                "uri": uri,
                "version": 2,
            },
            "contentChanges": [{"text": content}],
        }
        await self.send_notification("textDocument/didChange", params)

    # Semantic Query Operations
    async def get_definition(self, path: Path, line: int, character: int) -> List[Dict[str, Any]]:
        """Query definition locations (0-indexed line and character)."""
        if not await self._wait_ready():
            return []
        uri = Path(path).resolve().as_uri()
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        }
        try:
            res = await asyncio.wait_for(
                self._send_request("textDocument/definition", params), timeout=REQUEST_TIMEOUT
            )
        except Exception as exc:
            logger.warning("LSP definition request failed: %s", exc)
            return []
        if not res:
            return []
        if isinstance(res, dict):
            return [res]
        return res

    async def get_references(self, path: Path, line: int, character: int) -> List[Dict[str, Any]]:
        """Query reference locations (0-indexed line and character)."""
        if not await self._wait_ready():
            return []
        uri = Path(path).resolve().as_uri()
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        }
        try:
            res = await asyncio.wait_for(
                self._send_request("textDocument/references", params), timeout=REQUEST_TIMEOUT
            )
        except Exception as exc:
            logger.warning("LSP references request failed: %s", exc)
            return []
        return res or []

    async def rename(self, path: Path, line: int, character: int, new_name: str) -> Optional[Dict[str, Any]]:
        """Query rename edits for a symbol (0-indexed line and character)."""
        if not await self._wait_ready():
            return None
        uri = Path(path).resolve().as_uri()
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "newName": new_name,
        }
        try:
            return await asyncio.wait_for(
                self._send_request("textDocument/rename", params), timeout=REQUEST_TIMEOUT
            )
        except Exception as exc:
            logger.warning("LSP rename request failed: %s", exc)
            return None

    def get_all_diagnostics(self) -> str:
        """Compile a clean human-readable list of current project diagnostics."""
        lines = []
        for uri, diags in self.diagnostics.items():
            if not diags:
                continue

            path_str = uri
            if uri.startswith("file://"):
                try:
                    # Strip standard file:// prefix (handling both windows/linux variations)
                    p = Path(uri[7:])
                    if p.is_relative_to(self.workspace_dir):
                        path_str = str(p.relative_to(self.workspace_dir))
                    else:
                        path_str = str(p)
                except Exception:
                    pass

            lines.append(f"File: {path_str}")
            for d in diags:
                severity = d.get("severity", 3)
                sev_str = "Error" if severity == 1 else "Warning" if severity == 2 else "Info"
                msg = d.get("message", "")
                rng = d.get("range", {})
                line = rng.get("start", {}).get("line", 0) + 1
                char = rng.get("start", {}).get("character", 0) + 1
                lines.append(f"  [{sev_str}] Line {line}, Col {char}: {msg}")

        return "\n".join(lines) if lines else "No diagnostics reported."


# Language servers keyed by (command, languageId) with their file extensions.
# Multiple languages can share one server binary (typescript-language-server for
# JS/TS, clangd for C/C++); clients are pooled by command so it's started once.
_LSP_SERVERS = [
    (["pylsp"], "python", [".py", ".pyi"]),
    (["gopls"], "go", [".go"]),
    (["typescript-language-server", "--stdio"], "typescript", [".ts", ".tsx", ".mts", ".cts"]),
    (["typescript-language-server", "--stdio"], "javascript", [".js", ".jsx", ".mjs", ".cjs"]),
    (["rust-analyzer"], "rust", [".rs"]),
    (["clangd"], "c", [".c", ".h"]),
    (["clangd"], "cpp", [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"]),
]


def _default_ext_map() -> Dict[str, tuple]:
    ext_map: Dict[str, tuple] = {}
    for cmd, language_id, extensions in _LSP_SERVERS:
        for ext in extensions:
            ext_map[ext] = (tuple(cmd), language_id)
    return ext_map


class LSPManager:
    """Routes each file to the language server for its type (polymorphic LSP).

    Presents the same interface the tool registry uses as a single ``LSPClient``,
    but internally pools one client per server command and starts it lazily the
    first time a file of that language is touched — only if the binary exists.
    """

    def __init__(self, workspace_dir: Path, ext_map: Optional[Dict[str, tuple]] = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self._ext_map = ext_map or _default_ext_map()
        self._clients: Dict[tuple, LSPClient] = {}

    @classmethod
    def is_available(cls, workspace_dir: Path, ext_map: Optional[Dict[str, tuple]] = None) -> bool:
        ext_map = ext_map or _default_ext_map()
        checked: set = set()
        for cmd, _lang in ext_map.values():
            if cmd in checked:
                continue
            checked.add(cmd)
            if LSPClient.is_available(workspace_dir, list(cmd)):
                return True
        return False

    def _spec_for(self, path) -> Optional[tuple]:
        return self._ext_map.get(Path(path).suffix.lower())

    async def _client_for(self, path):
        spec = self._spec_for(path)
        if spec is None:
            return None, None
        cmd, language_id = spec
        if cmd in self._clients:
            return self._clients[cmd], language_id
        if not LSPClient.is_available(self.workspace_dir, list(cmd)):
            return None, language_id
        client = LSPClient(self.workspace_dir, cmd=list(cmd))
        try:
            await client.start()
        except Exception as exc:  # pragma: no cover - depends on server binary
            logger.warning("Failed to start LSP server %s: %s", cmd, exc)
            return None, language_id
        self._clients[cmd] = client
        return client, language_id

    async def start(self) -> None:
        # Servers start lazily per language; nothing to do up front.
        return None

    async def stop(self) -> None:
        for client in list(self._clients.values()):
            try:
                await client.stop()
            except Exception:  # pragma: no cover - best effort
                pass
        self._clients.clear()

    async def open_document(self, path: Path, content: str) -> None:
        client, language_id = await self._client_for(path)
        if client is not None:
            await client.open_document(path, content, language_id=language_id or "plaintext")

    async def change_document(self, path: Path, content: str) -> None:
        client, _ = await self._client_for(path)
        if client is not None:
            await client.change_document(path, content)

    async def get_definition(self, path: Path, line: int, character: int) -> List[Dict[str, Any]]:
        client, _ = await self._client_for(path)
        return await client.get_definition(path, line, character) if client is not None else []

    async def get_references(self, path: Path, line: int, character: int) -> List[Dict[str, Any]]:
        client, _ = await self._client_for(path)
        return await client.get_references(path, line, character) if client is not None else []

    async def rename(self, path: Path, line: int, character: int, new_name: str) -> Optional[Dict[str, Any]]:
        client, _ = await self._client_for(path)
        if client is not None:
            return await client.rename(path, line, character, new_name)
        return None

    async def await_diagnostics(self, timeout: float = 5.0) -> bool:
        """Wait for every pooled server to answer. Same contract as the single client."""
        results = [await c.await_diagnostics(timeout) for c in self._clients.values()]
        return all(results)

    def get_all_diagnostics(self) -> str:
        parts = []
        for client in self._clients.values():
            text = client.get_all_diagnostics()
            if text and text != "No diagnostics reported.":
                parts.append(text)
        return "\n".join(parts) if parts else "No diagnostics reported."
