"""Legacy execution mode: single-step execution, redundant-repeat tracking, and finish handling."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from ..tools.parser import ToolCall
from ..tools.registry import ToolResult
from .config import AgentConfig
from .tool_executor import (
    execute_tool_safely,
    parse_legacy_tool_calls,
    get_filtered_tools,
)
from .validators import check_stop_when_green, check_redundant_repeats
from .finish_handler import handle_legacy_finish

from rich.console import Console
from rich.markup import escape

console = Console()


async def execute_legacy_step(
    step: int,
    tools: List[Dict],
    seen: Dict[Tuple[str, str], int],
    orch: Any,
    security: Any,
    execution_context: Any,
    file_locks: Any,
) -> bool:
    """Execute a single step in legacy mode. Returns True to stop the loop."""
    response = await orch._model_turn(
        orch.frame.messages, tools, label=f"step {step}",
    )

    calls = await parse_legacy_tool_calls(orch, response, execution_context)
    if not calls:
        return False

    orch.frame.messages.append({"role": "assistant", "content": response.content or ""})
    call = calls[0]

    console.print(f"[bold cyan]→ {call.name}[/bold cyan] {list(call.arguments)}")
    orch.emit("tool_call", step=step, tool=call.name, args=call.arguments)

    if orch._is_single_file_workspace() and call.name in {"rename_symbol", "add_parameter", "add_docstring"}:
        result = ToolResult(
            False,
            f"Error: The tool '{call.name}' is not available in a single-file workspace. "
            "Please use 'write_file' or 'search_replace' to make edits.",
        )
    else:
        result = await execute_tool_safely(call, "", orch, security, execution_context, file_locks)

    safe_content = security.scrub_output(result.content)
    console.print(f"[dim]{escape(safe_content[:500])}[/dim]")
    orch.log.info("step %d: %s ok=%s", step, call.name, result.ok)

    if result.ok and call.name in AgentConfig.MUTATING_TOOLS:
        execution_context.mutations += 1
        orch._mutations += 1

    orch._audit("tool_call", step=step, tool=call.name, args=list(call.arguments), ok=result.ok)
    orch.emit("tool_result", step=step, tool=call.name, ok=result.ok, content=safe_content)

    orch.frame.messages.append({
        "role": "tool",
        "content": safe_content,
        "name": call.name,
    })

    if await check_stop_when_green(call, result, orch):
        result.is_final = True
        result.content = "Stop-when-green: tests passed successfully."

    await check_redundant_repeats(call, seen, step, execution_context, orch)
    if execution_context.redundant_repeats >= AgentConfig.MAX_REDUNDANT_REPEATS:
        return False

    if result.is_final:
        return await handle_legacy_finish(result, orch, execution_context)

    return False
