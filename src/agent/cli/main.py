"""Command-line interface for the AI coding agent."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from agent import __version__
from agent.errors import AgentError
from agent.logging import setup_logging
from agent.orchestrator import Orchestrator

console = Console()
app = typer.Typer(help="Local AI Coding Agent", add_completion=False)


async def _console_hint(context: str) -> Optional[str]:
    """Escalation prompt: show the failure and read a hint from the operator."""
    console.print(Panel(context[:1500] or "(no details)",
                        title="Agent is stuck — provide a hint?", border_style="red"))

    def _read() -> str:
        try:
            return input("Hint (or press Enter to give up): ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""

    return await asyncio.to_thread(_read)


@app.command()
def run(
    task: str = typer.Argument(..., help="Natural-language task description"),
    workspace: Path = typer.Option(Path("workspace"), "--workspace", "-w", help="Working directory"),
    model: str = typer.Option(
        "qwen2.5:7b", "--model", "-m", envvar="AI_AGENT_MODEL", help="Ollama model name"
    ),
    host: str = typer.Option(
        "http://localhost:11434", "--host", envvar="AI_AGENT_HOST", help="Ollama server URL"
    ),
    interactive: bool = typer.Option(True, "--interactive/--auto", help="Prompt before risky actions"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream model output"),
    sandbox: str = typer.Option(
        "auto", "--sandbox", envvar="AI_AGENT_SANDBOX", help="Sandbox backend: auto|docker|local"
    ),
    network: bool = typer.Option(
        False, "--network/--no-network",
        help="Allow network in the Docker sandbox (e.g. for pip/npm install)",
    ),
    max_retries: int = typer.Option(2, "--max-retries", help="Reflexion retries on failure"),
    max_steps: int = typer.Option(25, "--max-steps", help="Max tool calls per execution phase"),
    model_retries: int = typer.Option(3, "--model-retries", help="Backoff retries per model call"),
    num_ctx: int = typer.Option(8192, "--num-ctx", envvar="AI_AGENT_NUM_CTX",
                                help="Model context window (tokens); prompts are trimmed to fit"),
    memory: bool = typer.Option(True, "--memory/--no-memory",
                                help="Recall/save persistent project memory (.ai-agent/memory.jsonl)"),
    test_command: Optional[str] = typer.Option(
        None, "--test-command", envvar="AI_AGENT_TEST_COMMAND",
        help="Override the evaluation command (e.g. 'npm test', 'go test ./...')",
    ),
    audit_dir: Path = typer.Option(
        Path("logs"), "--audit-dir", envvar="AI_AGENT_AUDIT_DIR", help="Directory for audit.jsonl"
    ),
    log_level: str = typer.Option("INFO", "--log-level", envvar="AI_AGENT_LOG_LEVEL"),
    json_logs: bool = typer.Option(False, "--json-logs", help="Write logs/agent.log as JSON lines"),
) -> None:
    """Run the agent on a single task.

    Options may also be supplied via environment variables (AI_AGENT_MODEL,
    AI_AGENT_HOST, AI_AGENT_SANDBOX, AI_AGENT_AUDIT_DIR, AI_AGENT_LOG_LEVEL).
    """
    logger = setup_logging(log_level=log_level, json_logs=json_logs)
    logger.info("Starting task: %s", task)

    workspace.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(
        workspace=workspace,
        model_name=model,
        host=host,
        interactive=interactive,
        sandbox_backend=sandbox,
        max_retries=max_retries,
        max_steps=max_steps,
        model_retries=model_retries,
        log_dir=audit_dir,
        test_command=test_command,
        sandbox_network=network,
        num_ctx=num_ctx,
        use_memory=memory,
        escalation_callback=_console_hint if interactive else None,
    )

    try:
        frame = asyncio.run(orchestrator.run_task(task, stream=stream))
        final_state = orchestrator.fsm.state.value
        if final_state == "done":
            summary = frame.metadata.get("finish_summary", "Task completed.")
            console.print(Panel(f"[bold green]{summary}[/bold green]", title="Success"))
        else:
            console.print(Panel(f"Agent ended in state: {final_state}", title="Finished", border_style="yellow"))
        logger.info("Task finished in state: %s", final_state)
    except KeyboardInterrupt:
        logger.warning("Task interrupted by user")
        console.print("\n[yellow]Task stopped by user.[/yellow]")
    except AgentError as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        console.print(f"[bold red]Agent Error:[/bold red] {exc}")
    except Exception as exc:  # pragma: no cover - top-level safety net
        logger.error("Unexpected error: %s", exc, exc_info=True)
        console.print(f"[bold red]Unexpected Error:[/bold red] {exc}")
    finally:
        logger.info("Session ended")


@app.command()
def bench(
    workspace: Path = typer.Option(Path("workspace"), "--workspace", "-w"),
    model: str = typer.Option("qwen2.5:7b", "--model", "-m"),
) -> None:
    """Run the bundled benchmark tasks (see benchmarks/tasks)."""
    from agent.cli.bench import run_benchmarks

    run_benchmarks(workspace=workspace, model=model)


@app.command()
def serve(
    workspace: Path = typer.Option(Path("workspace"), "--workspace", "-w", help="Working directory"),
    model: str = typer.Option("qwen2.5:7b", "--model", "-m", envvar="AI_AGENT_MODEL"),
    host: str = typer.Option("http://localhost:11434", "--host", envvar="AI_AGENT_HOST", help="Ollama URL"),
    sandbox: str = typer.Option("auto", "--sandbox", envvar="AI_AGENT_SANDBOX"),
    interactive: bool = typer.Option(True, "--interactive/--auto", help="Gate commands via the browser"),
    bind: str = typer.Option("127.0.0.1", "--bind", help="Address to bind the web server to"),
    port: int = typer.Option(8765, "--port", help="Port for the web dashboard"),
    max_steps: int = typer.Option(25, "--max-steps"),
    max_retries: int = typer.Option(2, "--max-retries"),
    num_ctx: int = typer.Option(8192, "--num-ctx", envvar="AI_AGENT_NUM_CTX"),
    test_command: Optional[str] = typer.Option(None, "--test-command", envvar="AI_AGENT_TEST_COMMAND"),
    auth: bool = typer.Option(True, "--auth/--no-auth",
                              help="Require a session token to connect (recommended)"),
    log_level: str = typer.Option("INFO", "--log-level", envvar="AI_AGENT_LOG_LEVEL"),
) -> None:
    """Launch the web dashboard: submit tasks and watch the agent run live."""
    setup_logging(log_level=log_level)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        from agent.server.app import ServerConfig, serve as serve_app
    except ImportError as exc:
        console.print(
            "[bold red]The web UI needs aiohttp.[/bold red] Install with: "
            "pip install 'ai-coding-agent[web]'"
        )
        raise typer.Exit(1) from exc

    if bind not in ("127.0.0.1", "localhost") and not auth:
        console.print("[bold red]Refusing to bind a non-loopback address with --no-auth.[/bold red]")
        raise typer.Exit(1)

    config = ServerConfig(
        workspace=workspace, model=model, host=host, sandbox_backend=sandbox,
        interactive=interactive, max_steps=max_steps, max_retries=max_retries,
        num_ctx=num_ctx, test_command=test_command, log_dir=Path("logs"),
        require_auth=auth,
    )
    # serve() resolves a free port and prints the tokened URL to open.
    serve_app(config, bind=bind, port=port)


@app.command(name="build-sandbox")
def build_sandbox(
    tag: str = typer.Option("ai-agent-sandbox:latest", "--tag", help="Image tag to build"),
) -> None:
    """Build the Docker sandbox image used by `--sandbox docker`."""
    import subprocess

    from agent import sandbox as sandbox_pkg

    context = Path(sandbox_pkg.__file__).resolve().parent
    dockerfile = context / "Dockerfile"
    if not dockerfile.exists():
        console.print(f"[red]Dockerfile not found at {dockerfile}[/red]")
        raise typer.Exit(1)
    console.print(f"Building [bold]{tag}[/bold] from {dockerfile} ...")
    rc = subprocess.call(["docker", "build", "-t", tag, "-f", str(dockerfile), str(context)])
    if rc == 0:
        console.print(f"[green]Built {tag}[/green]. Use it with: ai-agent run ... --sandbox docker")
    raise typer.Exit(rc)


@app.command()
def memory(
    workspace: Path = typer.Option(Path("workspace"), "--workspace", "-w"),
    clear: bool = typer.Option(False, "--clear", help="Delete all remembered facts"),
) -> None:
    """View or clear the project's persistent memory (.ai-agent/memory.jsonl)."""
    from rich.table import Table

    from agent.memory import MemoryStore

    store = MemoryStore(workspace)
    if clear:
        n = store.clear()
        console.print(f"[yellow]Cleared {n} memory entrie(s).[/yellow]")
        return

    entries = store.load()
    if not entries:
        console.print("[dim]No memory yet. The agent saves facts via the `remember` tool "
                      "and from your escalation hints.[/dim]")
        return
    table = Table(title=f"Project memory ({len(entries)} entries) · {store.path}")
    table.add_column("Kind", style="cyan")
    table.add_column("Fact")
    table.add_column("When", style="dim")
    for e in entries:
        table.add_row(e.kind, e.text, (e.created or "")[:10])
    console.print(table)


@app.command()
def version() -> None:
    """Print the agent version."""
    console.print(f"ai-coding-agent {__version__}")


if __name__ == "__main__":
    app()
