"""Benchmark runner: execute bundled tasks and report pass/fail."""
from __future__ import annotations

import asyncio
import importlib.util
import logging
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from agent.orchestrator import Orchestrator

logger = logging.getLogger(__name__)
console = Console()

BENCH_DIR = Path(__file__).resolve().parents[3] / "benchmarks" / "tasks"


def _load_tasks() -> List[tuple[str, object]]:
    tasks: List[tuple[str, object]] = []
    if not BENCH_DIR.exists():
        return tasks
    for path in sorted(BENCH_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"bench_{path.stem}", path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "TASK") and hasattr(module, "check"):
            tasks.append((path.stem, module))
    return tasks


def run_benchmarks(workspace: Path, model: str) -> None:
    tasks = _load_tasks()
    if not tasks:
        console.print("[yellow]No benchmark tasks found.[/yellow]")
        return

    table = Table(title="Benchmark results")
    table.add_column("Task")
    table.add_column("Result")

    for name, module in tasks:
        task_ws = Path(workspace) / "bench" / name
        task_ws.mkdir(parents=True, exist_ok=True)
        for fname, content in getattr(module, "FILES", {}).items():
            (task_ws / fname).write_text(content, encoding="utf-8")

        console.print(f"[bold]Running benchmark:[/bold] {name}")
        orchestrator = Orchestrator(
            workspace=task_ws, model_name=model, interactive=False
        )
        try:
            asyncio.run(orchestrator.run_task(module.TASK, stream=False))
            passed = bool(module.check(task_ws))
        except Exception as exc:  # pragma: no cover - benchmark robustness
            logger.error("Benchmark %s errored: %s", name, exc)
            passed = False

        table.add_row(name, "[green]PASS[/green]" if passed else "[red]FAIL[/red]")

    console.print(table)
