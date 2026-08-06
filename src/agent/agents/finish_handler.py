"""Finish-tool validation: syntax checks, missing-file blocking, finish summary storage."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List

from .config import AgentConfig
from .validators import get_syntax_errors, check_lsp_diagnostics

from rich.console import Console

console = Console()


async def handle_finish_tool(
    path: str,
    target_path: Path,
    messages: List[Dict],
    orch: Any,
    read_file_safe_fn,
) -> bool:
    """Handle the finish tool call in subtask mode. Returns True if finish is allowed."""
    can_finish = True

    if orch._is_single_file_workspace():
        eval_result = await asyncio.to_thread(
            orch.evaluator.evaluate, orch.workspace,
        )
        if not eval_result.passed:
            can_finish = False
            messages.append({
                "role": "user",
                "content": (
                    f"Cannot finish subtask. Local tests are failing with this error:\n"
                    f"{eval_result.summary}\n"
                    "Please resolve the failures or correct the code before calling finish."
                ),
            })
    else:
        if path.endswith(".py") and target_path.exists():
            errors = await get_syntax_errors(path, read_file_safe_fn)
            if errors:
                can_finish = False
                messages.append({
                    "role": "user",
                    "content": (
                        f"Cannot finish subtask. The file '{path}' has compilation/syntax errors:\n"
                        + "; ".join(errors) + "\n"
                        "Please fix the syntax errors before calling finish."
                    ),
                })

    if can_finish:
        messages.append({"role": "user", "content": "Subtask completed successfully."})
        return True

    return False


async def handle_legacy_finish(
    result: Any,
    orch: Any,
    execution_context: Any,
) -> bool:
    """Handle finish in legacy mode. Returns True if finish is allowed."""
    if orch.lsp and not await check_lsp_diagnostics(orch):
        return False

    missing = orch._missing_requested_files()
    if missing and execution_context.blocked_finishes >= AgentConfig.MAX_BLOCKED_FINISHES:
        orch.log.warning(
            "Allowing finish with %d requested file(s) still missing after %d blocks: %s",
            len(missing), execution_context.blocked_finishes, ", ".join(missing),
        )
        console.print(
            f"[yellow]Finishing with {len(missing)} requested file(s) still "
            f"missing: {', '.join(missing)}[/yellow]"
        )
        orch.emit("finish_incomplete", missing=missing)
        orch.frame.metadata["missing_requested_files"] = missing
        missing = []

    if missing:
        execution_context.blocked_finishes += 1
        console.print(f"[yellow]Blocked finish: {len(missing)} requested file(s) missing[/yellow]")
        orch.frame.messages.append({
            "role": "user",
            "content": (
                "Wait, you cannot finish yet. The task asked for these files "
                "and they do not exist:\n"
                + "\n".join(f"  - {m}" for m in missing)
                + "\nCreate exactly these paths with write_file, at exactly "
                "these locations, with content that satisfies the task. The "
                "tests already pass, so do not change any existing code -- "
                "only add the missing files, then call finish. If the task "
                "explicitly forbids one of these files, say so in your finish "
                "summary instead of creating it."
            ),
        })
        return False

    orch.frame.metadata["finish_summary"] = result.content
    return True
