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


def run_benchmarks(workspace: Path, model: str, task_name: str | None = None, planner_editor: bool = False, max_retries: int = 2, num_ctx: int = 16384) -> None:
    import fnmatch
    tasks = _load_tasks()
    
    # ONLY wins if non-empty: name exactly the tasks to run. Preferred over
    # EXCLUDED, because an exclusion list silently runs everything you forgot to
    # name -- on 2026-07-20 a 17-task Exercism list quietly pulled in all 164
    # HumanEval tasks too, and it took ~40 wasted minutes to notice.
    #
    # Empty = fall back to EXCLUDED (the full runnable set). Populate it only for
    # a targeted experiment, and empty it again afterwards -- a stale ONLY
    # silently measures last week's question.
    ONLY: set[str] = set()

    # Used only when ONLY is empty. 15 model-ceiling + 2 recoverable holdouts
    # (go-counting is one Go-rule short; tree-building has tangled validation).
    # bottle-song and zebra-puzzle are NOT here: aider passed them on the same
    # 32B, so the ceiling list overcounted. See CAPABILITY_ENVELOPE.md.
    EXCLUDED = {
        # Unpassable: check() runs a file with no tests and demands exit 0,
        # but pytest exits 5 on "no tests collected". Every run has scored it a
        # failure, for this agent and aider alike, so the real denominator is 33
        # not 34. See the note at the top of benchmarks/tasks/Exercism_paasio.py.
        "Exercism_paasio",
        "Exercism_book-store",
        "Exercism_bowling",
        "Exercism_connect",
        "Exercism_food-chain",
        "Exercism_forth",
        "Exercism_poker",
        "Exercism_pov",
        "Exercism_react",
        "Exercism_rest-api",
        "Exercism_scale-generator",
        "Exercism_sgf-parsing",
        "Exercism_two-bucket",
        "Exercism_variable-length-quantity",
        "Exercism_wordy",
        "Exercism_zipper",
        "Exercism_go-counting",
        "Exercism_tree-building",
    }
    if ONLY:
        tasks = [t for t in tasks if t[0] in ONLY]
        missing = ONLY - {t[0] for t in tasks}
        if missing:
            console.print(f"[red]ONLY names tasks that do not exist: {sorted(missing)}[/red]")
            return
    else:
        tasks = [t for t in tasks if t[0].startswith("Exercism_") and t[0] not in EXCLUDED]

    # Say out loud what is about to run, so a wrong list costs a second, not an hour.
    console.print(f"[cyan]Running {len(tasks)} task(s):[/cyan] {', '.join(t[0] for t in tasks)}")

    if task_name:
        tasks = [t for t in tasks if fnmatch.fnmatch(t[0].lower(), task_name.lower())]
        if not tasks:
            console.print(f"[red]Task {task_name!r} not found.[/red]")
            return
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

        import os
        import time
        from agent.errors import TransientError
        host = os.environ.get("AI_AGENT_HOST", "http://localhost:11434")
        sandbox_backend = os.environ.get("AI_AGENT_SANDBOX", "auto")
        console.print(f"[bold]Running benchmark:[/bold] {name}")
        
        passed = False
        for attempt in range(1, 4):
            orchestrator = Orchestrator(
                workspace=task_ws, model_name=model, interactive=False, planner_editor=planner_editor, max_retries=max_retries, host=host, sandbox_backend=sandbox_backend, num_ctx=num_ctx
            )
            try:
                asyncio.run(orchestrator.run_task(module.TASK, stream=False))
                passed = bool(module.check(task_ws))
                break
            except TransientError as exc:
                if attempt < 3:
                    # Must outlast a tunnel reconnect, or a dropped SSH session
                    # burns all 3 attempts against a dead socket and the task is
                    # scored a FAIL that has nothing to do with the model.
                    # autossh reconnects in ~10s (ServerAliveInterval 5 x 2).
                    console.print(f"[yellow]Transient infrastructure error on attempt {attempt}: {exc}. Retrying in 60 seconds...[/yellow]")
                    time.sleep(60)
                else:
                    logger.error("Benchmark %s failed after 3 infrastructure retries: %s", name, exc)
                    passed = False
            except Exception as exc:  # pragma: no cover - benchmark robustness
                logger.error("Benchmark %s errored: %s", name, exc)
                passed = False
                break

        table.add_row(name, "[green]PASS[/green]" if passed else "[red]FAIL[/red]")

    console.print(table)
