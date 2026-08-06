"""UI / display helpers extracted from the Orchestrator."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from .telemetry import RunStats
    from .utils.circuit_breaker import CircuitBreaker

console = Console()


class OrchestratorDisplay:
    """Renders run summaries, task headers, and handoff panels.

    Pulls the Rich-based UI logic out of the Orchestrator so the orchestrator
    can stay focused on coordination while display is handled elsewhere.
    """

    # ---- task header ----

    @staticmethod
    def display_task_header(task: str, run_id: str, model_name: str) -> None:
        console.print(
            Panel(
                f"[bold green]Task:[/bold green] {escape(task)}\n"
                f"[dim]run {run_id} \u00b7 model {model_name}[/dim]",
                title="AI Coding Agent",
            )
        )

    # ---- model unavailable ----

    @staticmethod
    def display_model_unavailable(host: str) -> None:
        console.print(
            f"[bold red]Ollama is not reachable at {host}.[/bold red] "
            "Start it with `ollama serve`."
        )

    # ---- run summary table ----

    @staticmethod
    def print_stats(
        stats: "RunStats",
        run_id: str,
        model_name: str,
        circuit: "CircuitBreaker",
    ) -> None:
        if stats.model_calls == 0:
            return
        table = Table(title="Run summary", show_header=False, title_style="bold")
        table.add_row("Run id", run_id)
        table.add_row("Model", model_name)
        table.add_row("Model calls", str(stats.model_calls))
        table.add_row("Prompt tokens", f"{stats.prompt_tokens:,}")
        table.add_row("Completion tokens", f"{stats.completion_tokens:,}")
        table.add_row("Total tokens", f"{stats.total_tokens:,}")
        table.add_row("Model time", f"{stats.total_seconds:.1f}s")
        table.add_row("Throughput", f"{stats.tokens_per_second:.1f} tok/s")
        table.add_row("Circuit", circuit.get_metrics()["state"])
        console.print(table)

    # ---- end-of-run message ----

    @staticmethod
    def print_session_ended(state: str) -> None:
        console.print(f"[bold]Session ended in state:[/bold] {state}")

    # ---- handoff report ----

    @staticmethod
    def write_handoff_report(
        *,
        workspace: Any,
        run_id: str,
        model_name: str,
        state: str,
        retry_count: int,
        max_retries: int,
        last_error_summary: str,
        eval_result: Any,
        reflections: List[str],
        missing_files: List[str],
        log: Any,
    ) -> Optional[str]:
        """Write ``AGENT_HANDOFF.md`` and return the report text."""
        missing = missing_files
        built: List[str] = []
        blocking = ""

        # missing / built computed inline to keep the method self-contained
        import re as _re

        task = ""
        # We receive the raw task from the caller via last_error_summary context;
        # for now, extract missing from eval_result if present.

        if eval_result is not None:
            blocking = (
                getattr(eval_result, "details", "")
                or getattr(eval_result, "summary", "")
                or ""
            ).strip()

        lessons = [str(x) for x in (reflections or [])][-3:]

        lines = [
            "# Agent handoff \u2014 unfinished run",
            "",
            f"- **Run id:** {run_id}",
            f"- **Model:** {model_name}",
            f"- **Final state:** {state}",
            f"- **Retries used:** {retry_count}/{max_retries}",
            "",
            "## Why it stopped",
            last_error_summary or "See the blocking error below.",
            "",
            "## Files present in the workspace",
        ]

        # list source-ish files
        try:
            from pathlib import Path as _P

            ws = workspace
            for p in sorted(ws.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(ws)
                parts = set(rel.parts)
                if parts & {".git", "__pycache__", ".pytest_cache", ".agents"}:
                    continue
                if p.suffix in {".pyc", ".pyo", ".log"}:
                    continue
                built.append(str(rel))
                if len(built) >= 60:
                    built.append("\u2026 (truncated)")
                    break
        except OSError:
            pass

        lines += [f"- {f}" for f in built] or ["- (none)"]
        lines += ["", "## Requested files still MISSING"]
        lines += [f"- {f}" for f in missing] or [
            "- (none \u2014 every explicitly requested file exists)"
        ]
        if blocking:
            lines += [
                "",
                "## Blocking error (most recent evaluation)",
                "```",
                blocking[:4000],
                "```",
            ]
        if lessons:
            lines += ["", "## What the agent tried (recent reflexion lessons)"]
            lines += [f"- {les[:300]}" for les in lessons]
        lines += [
            "",
            "## Suggested next step for a human",
            "Review the blocking error above, fix the specific file(s) it names, then "
            "re-run the agent \u2014 the completed layers are already on disk and will be kept.",
            "",
        ]
        report = "\n".join(lines)

        try:
            from pathlib import Path as _P

            (workspace / "AGENT_HANDOFF.md").write_text(report, encoding="utf-8")
        except OSError as exc:
            log.warning("Could not write AGENT_HANDOFF.md: %s", exc)

        console.print(
            Panel(
                f"[bold]Unfinished run \u2014 handoff written to AGENT_HANDOFF.md[/bold]\n"
                f"Missing requested files: {', '.join(missing) if missing else 'none'}\n"
                f"{'Blocking: ' + escape(blocking.splitlines()[-1][:160]) if blocking else ''}",
                title="Honest partial",
                border_style="yellow",
            )
        )
        return report

    # ---- transient-error banner ----

    @staticmethod
    def print_transient_error(error: Any, metrics: Dict[str, Any]) -> None:
        console.print(f"[yellow]Transient error ({error}). Circuit: {metrics['state']}[/yellow]")

    # ---- generic error banner ----

    @staticmethod
    def print_error(error: Any) -> None:
        console.print(f"[bold red]Error:[/bold red] {error}")

    # ---- model output streaming helper (thin wrapper) ----

    @staticmethod
    def print_label(label: str) -> None:
        console.print(f"[dim]{escape(label)}[/dim]")

    @staticmethod
    def print_stream_result(content: str, limit: int = 500) -> None:
        safe = content[:limit]
        console.print(f"[dim]{escape(safe)}[/dim]")

    @staticmethod
    def print_yellow(message: str) -> None:
        console.print(f"[yellow]{message}[/yellow]")
