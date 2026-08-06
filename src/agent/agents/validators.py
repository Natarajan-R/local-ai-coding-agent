"""Validation, thrash detection, stop-when-green, LSP diagnostics, redundant-repeat detection."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from ..perception.analysis import python_syntax_errors
from ..tools.parser import ToolCall
from ..tools.registry import ToolResult
from .config import AgentConfig

from rich.console import Console

console = Console()


async def get_syntax_errors(path: str, read_file_safe_fn) -> List[str]:
    """Get syntax errors for a Python file."""
    try:
        content = await read_file_safe_fn(path, False)
        return python_syntax_errors(content, filename=path)
    except Exception:
        return []


async def check_thrash_detection(
    call: ToolCall,
    path: str,
    edit_counts: Dict[str, int],
    messages: List[Dict],
) -> bool:
    """Check if the agent is thrashing (editing same location repeatedly)."""
    if call.name not in ("edit_lines", "search_replace"):
        return False

    loc_key = _get_location_key(call, path)
    edit_counts[loc_key] = edit_counts.get(loc_key, 0) + 1

    if edit_counts[loc_key] == AgentConfig.THRASH_DETECTION_THRESHOLD:
        messages.append({
            "role": "user",
            "content": (
                f"You have edited the same part of '{path}' several times "
                "and it is still not right. Stop making small edits there. "
                "Read the whole file, then replace it in ONE `write_file` "
                "call with a complete, correct implementation."
            ),
        })
        return True

    return False


def _get_location_key(call: ToolCall, path: str) -> str:
    if call.name == "edit_lines":
        return f"{path}:{call.arguments.get('start_line')}"
    else:
        search_text = str(call.arguments.get("search", ""))[:40]
        return f"{path}:{search_text}"


async def check_stop_when_green(call: ToolCall, result: ToolResult, orch: Any) -> bool:
    """Check if stop-when-green condition is met."""
    if (
        orch.config.stop_when_green
        and not orch._baseline_green
        and (call.name in AgentConfig.MUTATING_TOOLS or call.name == "run_command")
    ):
        eval_result = await asyncio.to_thread(orch.evaluator.evaluate, orch.workspace)
        return bool(eval_result.passed and eval_result.ran_tests)
    return False


async def check_redundant_repeats(
    call: ToolCall,
    seen: Dict[Tuple[str, str], int],
    step: int,
    execution_context: Any,
    orch: Any,
) -> bool:
    """Check and handle redundant tool calls. Returns False when budget exceeded."""
    sig = (call.name, repr(sorted(call.arguments.items())))
    last_mutations = seen.get(sig)
    moved = (
        call.name in AgentConfig.VERIFY_TOOLS
        and last_mutations != execution_context.mutations
    )

    if last_mutations is not None and not moved:
        execution_context.redundant_repeats += 1
        orch.log.info(
            "Redundant repeat of %s (x%d) at step %d",
            call.name, execution_context.redundant_repeats, step,
        )
        orch.frame.messages.append({
            "role": "user",
            "content": (
                f"You already ran `{call.name}` with those arguments earlier. "
                "Do not repeat actions. If you need to create multiple files, "
                "use `run_command` with heredocs (e.g. `cat > file.py << 'PYEOF'`)"
                " — it is not limited by the mutation budget. "
                "If the change is complete and verified, "
                "call the `finish` tool now with a short summary; otherwise take "
                "a genuinely different action."
            ),
        })

        if execution_context.redundant_repeats >= AgentConfig.MAX_REDUNDANT_REPEATS:
            return False
    else:
        seen[sig] = execution_context.mutations

    return True


async def check_lsp_diagnostics(orch: Any) -> bool:
    """Check LSP diagnostics for errors. Returns True if clean (finish allowed)."""
    await orch.lsp.await_diagnostics(timeout=AgentConfig.LSP_DIAGNOSTICS_TIMEOUT)

    has_errors = False
    for client in getattr(orch.lsp, "_clients", {}).values():
        for diags in client.diagnostics.values():
            if any(d.get("severity", 3) == 1 for d in diags):
                has_errors = True
                break
        if has_errors:
            break

    if has_errors:
        diagnostics_text = orch.lsp.get_all_diagnostics()
        console.print("[yellow]Blocked finish: compiler diagnostics reported errors[/yellow]")
        orch.frame.messages.append({
            "role": "user",
            "content": (
                "Wait, you cannot finish yet. There are compile/lint errors in the workspace:\n"
                f"{diagnostics_text}\n"
                "Please read the files, fix these errors, and only then call finish."
            ),
        })
        return False

    return True
