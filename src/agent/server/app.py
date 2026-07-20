"""aiohttp web server that drives the Orchestrator and streams its events.

One run at a time. The browser connects over a WebSocket, submits a task,
receives structured events (state changes, plan, tokens, tool calls, results,
evaluation, approvals, final summary), and answers approval prompts.
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from ..orchestrator import Orchestrator
from .broadcaster import ApprovalBroker, Broadcaster, HintBroker
from .ui import INDEX_HTML

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    workspace: Path
    model: str = "qwen2.5:7b"
    host: str = "http://localhost:11434"      # Ollama endpoint
    sandbox_backend: str = "auto"
    interactive: bool = True                   # gate run_command via the browser
    max_steps: int = 25
    max_retries: int = 2
    num_ctx: int = 8192
    test_command: Optional[str] = None
    log_dir: Optional[Path] = None
    require_auth: bool = True                   # gate /ws with a per-session token
    planner_editor: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


def find_free_port(bind: str, port: int, tries: int = 20) -> int:
    """Return the first bindable port at or after ``port`` (avoids crash-on-in-use)."""
    for candidate in range(port, port + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((bind, candidate))
                return candidate
            except OSError:
                continue
    return port  # let the server surface a clear bind error


class AgentServer:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.broadcaster = Broadcaster()
        self.approvals = ApprovalBroker(self.broadcaster)
        self.hints = HintBroker(self.broadcaster)
        self._running = False
        self._orchestrator = None
        # Per-session token that the browser must present to open the WebSocket.
        self.token = uuid.uuid4().hex if config.require_auth else None

    # -- app -----------------------------------------------------------------
    def build_app(self):
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/", self._index)
        app.router.add_get("/api/health", self._health)
        app.router.add_get("/ws", self._websocket)
        return app

    @property
    def public_config(self) -> Dict[str, Any]:
        return {
            "workspace": str(self.config.workspace),
            "model": self.config.model,
            "sandbox": self.config.sandbox_backend,
            "interactive": self.config.interactive,
        }

    async def _index(self, request):
        from aiohttp import web

        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def _health(self, request):
        from aiohttp import web

        return web.json_response(
            {"status": "ok", "running": self._running, "clients": self.broadcaster.client_count}
        )

    async def _websocket(self, request):
        from aiohttp import web

        # Require the session token (unless auth is disabled). The dashboard page
        # carries it in its URL and forwards it on connect, so a network peer that
        # doesn't know the token cannot open a control socket.
        if self.token is not None and request.query.get("token") != self.token:
            logger.warning("Rejected WebSocket connection with a missing/invalid token")
            return web.json_response({"error": "invalid or missing token"}, status=403)

        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        queue = self.broadcaster.subscribe()

        await ws.send_json({"event": "connected", "config": self.public_config})

        async def pump() -> None:
            try:
                while True:
                    event = await queue.get()
                    await ws.send_json(event)
            except (asyncio.CancelledError, ConnectionResetError):
                pass

        pump_task = asyncio.create_task(pump())
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    await self._on_client_message(data)
                elif msg.type == web.WSMsgType.ERROR:  # pragma: no cover
                    break
        finally:
            pump_task.cancel()
            self.broadcaster.unsubscribe(queue)
        return ws

    # -- client messages -----------------------------------------------------
    async def _on_client_message(self, data: Dict[str, Any]) -> None:
        kind = data.get("type")
        if kind == "run":
            await self._start_run(data.get("task", ""), data.get("options", {}))
        elif kind == "approval":
            self.approvals.resolve(str(data.get("id", "")), bool(data.get("approved")))
        elif kind == "hint":
            self.hints.resolve(str(data.get("id", "")), data.get("hint"))
        elif kind == "pause":
            if self._orchestrator:
                self._orchestrator.pause()
        elif kind == "resume":
            if self._orchestrator:
                self._orchestrator.resume()
        elif kind == "stop":
            if self._orchestrator:
                self._orchestrator.stop()

    async def _start_run(self, task: str, options: Dict[str, Any]) -> None:
        if self._running:
            self.broadcaster.publish({"event": "error", "message": "A run is already in progress."})
            return
        if not task.strip():
            self.broadcaster.publish({"event": "error", "message": "Task must not be empty."})
            return
        self._running = True
        asyncio.create_task(self._run(task, options))

    async def _run(self, task: str, options: Dict[str, Any]) -> None:
        cfg = self.config
        interactive = bool(options.get("interactive", cfg.interactive))
        model = options.get("model") or cfg.model
        try:
            self._orchestrator = Orchestrator(
                workspace=cfg.workspace,
                model_name=model,
                host=cfg.host,
                sandbox_backend=cfg.sandbox_backend,
                interactive=interactive,
                max_steps=cfg.max_steps,
                max_retries=cfg.max_retries,
                num_ctx=cfg.num_ctx,
                test_command=cfg.test_command,
                log_dir=cfg.log_dir,
                event_sink=self.broadcaster.publish,
                approval_callback=self.approvals.request if interactive else None,
                escalation_callback=self.hints.request if interactive else None,
                planner_editor=cfg.planner_editor,
            )
            await self._orchestrator.run_task(task, stream=True)
        except Exception as exc:  # pragma: no cover - defensive top-level
            logger.exception("Run failed")
            self.broadcaster.publish({"event": "error", "message": str(exc)})
        finally:
            self._orchestrator = None
            self._running = False


def serve(config: ServerConfig, bind: str = "127.0.0.1", port: int = 8765) -> None:
    """Blocking entry point used by the CLI."""
    try:
        from aiohttp import web
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit(
            "The web UI needs aiohttp. Install it with:  pip install 'ai-coding-agent[web]'\n"
            f"(import error: {exc})"
        )

    from rich.console import Console
    from rich.panel import Panel

    server = AgentServer(config)
    port = find_free_port(bind, port)
    query = f"?token={server.token}" if server.token else ""
    url = f"http://{bind}:{port}/{query}"
    Console().print(Panel(
        f"[bold green]AI Coding Agent — web dashboard[/bold green]\n"
        f"Open [bold]{url}[/bold]\n"
        f"[dim]workspace: {config.workspace} · model: {config.model}"
        + ("" if server.token else " · [red]auth disabled[/red]") + "[/dim]",
        title="serve",
    ))
    web.run_app(server.build_app(), host=bind, port=port, print=None)
