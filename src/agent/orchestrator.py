"""The orchestrator: an FSM-driven plan/execute/evaluate/reflect loop."""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Awaitable, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .context import ContextManager
from .errors import TransientError
from .memory import MemoryStore
from .evaluation.evaluator import Evaluator
from .evaluation.reflexion import ReflexionEngine
from .fsm import FSM, AgentState
from .model.client import OllamaClient
from .perception.indexer import WorkspaceIndexer
from .perception.lsp import LSPManager
from . import prompts
from .sandbox.config import SandboxConfig
from .sandbox.manager import SandboxManager
from .guardrails.policy import SecurityPolicy
from .state import AgentFrame
from .telemetry import RunStats
from .tools.parser import ToolParser
from .tools.registry import ToolRegistry
from .utils.circuit_breaker import CircuitBreaker
from .utils.retry import async_retry

logger = logging.getLogger(__name__)
console = Console()

# Default bound on tool calls within a single execution phase.
DEFAULT_MAX_STEPS = 25
# Default number of attempts for a single model call before giving up.
DEFAULT_MODEL_RETRIES = 3


class Orchestrator:
    def __init__(
        self,
        workspace: Path,
        model_name: str = "qwen2.5:7b",
        interactive: bool = True,
        sandbox_backend: str = "auto",
        max_retries: int = 2,
        max_steps: int = DEFAULT_MAX_STEPS,
        model_retries: int = DEFAULT_MODEL_RETRIES,
        log_dir: Path | None = None,
        host: str = "http://localhost:11434",
        test_command: str | None = None,
        sandbox_network: bool = False,
        num_ctx: int = 8192,
        use_memory: bool = True,
        event_sink: Optional[Callable[[dict], None]] = None,
        approval_callback: Optional[Callable[[str, str], Awaitable[bool]]] = None,
        escalation_callback: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.max_steps = max_steps
        self.run_id = uuid.uuid4().hex[:8]
        # Optional structured-event sink (e.g. the web server broadcaster).
        self._event_sink = event_sink
        # Optional human-escalation hook: called once when the retry budget is
        # exhausted; may return a hint to grant one more round of attempts.
        self._escalation_callback = escalation_callback
        self.stats = RunStats()
        self.fsm = FSM()
        self.frame = AgentFrame(task_description="", max_retries=max_retries)
        self.log = logging.LoggerAdapter(logger, {"run_id": self.run_id})

        self.model = OllamaClient(
            model_name=model_name, host=host,
            options={"temperature": 0.1, "num_ctx": num_ctx},
        )
        self.model_name = model_name
        # Keep every model call within the context window.
        self.context = ContextManager(max_tokens=num_ctx)
        self.sandbox = SandboxManager(
            SandboxConfig(
                workspace=self.workspace,
                backend=sandbox_backend,
                network_disabled=not sandbox_network,
            )
        )
        self.policy = SecurityPolicy(self.workspace, interactive=interactive, log_dir=log_dir)
        # Correlate every audit record (including tool-level ones) with this run.
        self.policy.audit.context = {"run_id": self.run_id}
        self.indexer = WorkspaceIndexer(self.workspace)
        # Persistent per-project memory (recalled into the planning context).
        self.memory = MemoryStore(self.workspace, enabled=use_memory)
        # Polymorphic LSP: routes each file to its language's server. Enabled
        # only when at least one known server binary is installed; otherwise the
        # model isn't offered semantic tools that can't run.
        self.lsp = LSPManager(self.workspace) if LSPManager.is_available(self.workspace) else None
        self.tools = ToolRegistry(
            self.sandbox, self.policy, self.workspace,
            lsp=self.lsp, approval_callback=approval_callback, indexer=self.indexer,
            memory=self.memory,
        )
        self.parser = ToolParser()
        self.evaluator = Evaluator(self.sandbox, self.policy, test_command=test_command)

        # Resilient model calls: retry with exponential backoff on transient
        # errors, wrapped in a circuit breaker that trips on repeated failure.
        self.model_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60, name="model")
        retry = async_retry(
            max_attempts=model_retries,
            base_delay=1.0,
            max_delay=20.0,
            exceptions=(TransientError,),
        )
        self._chat = self.model_circuit(retry(self.model.chat))
        self._chat_stream = self.model_circuit(retry(self.model.chat_stream))
        self._stream = True

        # Reflexion reuses the resilient (retry + circuit-breaker) chat call.
        self.reflexion = ReflexionEngine(
            self.model, self.evaluator, self.sandbox, self.policy, chat_fn=self._chat
        )

    def _audit(self, action: str, **fields) -> None:
        """Record an audit entry (run_id is injected by the audit context)."""
        self.policy.audit.record(action, **fields)

    def emit(self, event: str, **data) -> None:
        """Publish a structured UI event to the optional event sink.

        Sinks (e.g. the web server) are synchronous and non-blocking; failures
        never affect the run.
        """
        if self._event_sink is None:
            return
        try:
            self._event_sink({"event": event, "run_id": self.run_id, **data})
        except Exception:  # pragma: no cover - a UI sink must never break a run
            self.log.debug("event sink error for %s", event, exc_info=True)

    async def run_task(self, task: str, stream: bool = True) -> AgentFrame:
        self.frame.task_description = task
        self._stream = stream
        self.log.info("Task start: %s", task)
        self._audit(
            "task_start", task=task, model=self.model_name,
            workspace=str(self.workspace), stream=stream,
        )
        self.emit("run_started", task=task, model=self.model_name, workspace=str(self.workspace))
        self.sandbox.start()
        if self.lsp is not None:
            try:
                await self.lsp.start()
            except Exception as exc:
                self.log.warning("LSP server failed to start: %s", exc)
                self.lsp = None
        console.print(
            Panel(
                f"[bold green]Task:[/bold green] {task}\n[dim]run {self.run_id} · model {self.model_name}[/dim]",
                title="AI Coding Agent",
            )
        )

        if not await self.model.is_available():
            console.print(
                "[bold red]Ollama is not reachable at "
                f"{self.model.host}.[/bold red] Start it with `ollama serve`."
            )
            self.log.error("Ollama not reachable at %s", self.model.host)
            self._audit("model_unavailable", host=self.model.host)
            self.fsm.transition("start")
            self.fsm.transition("error")
            await self.model.close()
            self._finalize()
            return self.frame

        self.fsm.transition("start")
        try:
            while not self.fsm.is_terminal():
                state = self.fsm.state
                self.emit("state_changed", state=state.value)
                try:
                    if state == AgentState.PLANNING:
                        await self._planning_step()
                    elif state == AgentState.EXECUTING:
                        await self._execution_step()
                    elif state == AgentState.EVALUATING:
                        await self._evaluation_step()
                    elif state == AgentState.REFLEXING:
                        await self._reflexion_step()
                    else:  # pragma: no cover - defensive
                        break
                except Exception as exc:
                    await self._handle_error(exc)
        finally:
            await self.model.close()
            try:
                if self.lsp is not None:
                    await self.lsp.stop()
            except Exception:
                pass
            self._finalize()
        return self.frame

    async def _model_turn(self, messages, tools=None, label: str = ""):
        """Call the model, streaming tokens to the console when enabled.

        Whether streamed or not, returns a complete ``ChatResponse`` so the
        caller can still parse tool calls from the full message.
        """
        # Trim the conversation to fit the model's context window before sending.
        fitted = self.context.fit(messages)
        if fitted.trimmed:
            self.log.info(
                "Context trimmed: dropped %d msg(s), ~%d tokens sent",
                fitted.dropped, fitted.est_tokens,
            )
            self.emit("context_trimmed", dropped=fitted.dropped, est_tokens=fitted.est_tokens)
        send_messages = fitted.messages

        if not self._stream:
            response = await self._chat(send_messages, tools)
            self.stats.record(response.raw)
            self.emit("assistant_message", label=label, content=response.content)
            return response

        if label:
            console.print(f"[dim]{label}[/dim]")
        wrote = {"any": False}

        def writer(token: str) -> None:
            wrote["any"] = True
            sys.stdout.write(token)
            sys.stdout.flush()
            self.emit("token", text=token, label=label)

        response = await self._chat_stream(send_messages, tools, on_token=writer)
        if wrote["any"]:
            sys.stdout.write("\n")
            sys.stdout.flush()
        self.stats.record(response.raw)
        return response

    # -- phases --------------------------------------------------------------
    async def _planning_step(self) -> None:
        skeleton = self.indexer.get_repo_skeleton()
        memory_text = self.memory.format_for_prompt()
        if memory_text:
            self.log.info("Loaded %d memory entrie(s) into context", self.memory.count())
            self.emit("memory_loaded", count=self.memory.count())
        messages = prompts.planning_messages(self.frame.task_description, skeleton, memory_text)
        response = await self._model_turn(messages, label="Planning...")
        self.frame.plan = response.content.strip()
        self.log.info("Plan created (%d chars)", len(self.frame.plan or ""))
        self._audit("plan_created", plan_chars=len(self.frame.plan or ""))
        self.emit("plan", text=self.frame.plan or "")
        if not self._stream:
            console.print(Panel(self.frame.plan or "(no plan)", title="Plan", border_style="cyan"))

        # Seed the execution conversation.
        self.frame.messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            prompts.execution_primer(self.frame.task_description, self.frame.plan or ""),
        ]
        if memory_text:
            self.frame.messages.append({"role": "user", "content": memory_text})
        for lesson in self.frame.reflections:
            self.frame.messages.append(
                {"role": "user", "content": f"Lesson from a previous attempt: {lesson}"}
            )
        self.fsm.transition("plan_ready")

    async def _execution_step(self) -> None:
        tools = self.tools.get_descriptions()
        seen: set[tuple] = set()   # every tool-call signature performed this phase
        redundant = 0              # count of repeated (already-performed) actions
        for step in range(1, self.max_steps + 1):
            response = await self._model_turn(self.frame.messages, tools, label=f"step {step}")

            native = self.parser.parse_native(response.tool_calls)
            calls = native or self.parser.parse(response.content)

            if not calls:
                # Nudge the model to use a tool if it only produced prose.
                console.print(f"[dim]step {step}: model produced no tool call[/dim]")
                self.frame.messages.append({"role": "assistant", "content": response.content})
                self.frame.messages.append({
                    "role": "user",
                    "content": "Respond with exactly one tool call in the required JSON format.",
                })
                continue

            self.frame.messages.append({"role": "assistant", "content": response.content or ""})

            call = calls[0]
            console.print(f"[bold cyan]→ {call.name}[/bold cyan] {list(call.arguments)}")
            self.emit("tool_call", step=step, tool=call.name, args=call.arguments)
            result = await self.tools.execute(call.name, call.arguments)
            # Redact secrets once, at the boundary — before the output reaches the
            # console, the model's context, or the dashboard. Any tool's output
            # (read_file, search, …) is covered here, not just run_command.
            safe_content = self.policy.scrub(result.content)
            console.print(f"[dim]{safe_content[:500]}[/dim]")
            self.log.info("step %d: %s ok=%s", step, call.name, result.ok)
            self._audit(
                "tool_call", step=step, tool=call.name,
                args=list(call.arguments), ok=result.ok,
            )
            self.emit("tool_result", step=step, tool=call.name, ok=result.ok,
                      content=safe_content)

            self.frame.messages.append({
                "role": "tool",
                "content": safe_content,
                "name": call.name,
            })

            if result.is_final:
                self.frame.metadata["finish_summary"] = result.content
                break

            # No-progress detection. Track EVERY action performed this phase, not
            # just the immediately preceding one: a wandering model that repeats
            # an earlier action (write -> run -> re-read -> run ...) makes no real
            # progress even though consecutive calls differ. Repeating any prior
            # action is the signal; nudge on each repeat and bail after a few.
            sig = (call.name, repr(sorted(call.arguments.items())))
            if sig in seen:
                redundant += 1
                self.log.info("Redundant repeat of %s (x%d) at step %d", call.name, redundant, step)
                self.frame.messages.append({
                    "role": "user",
                    "content": (
                        f"You already ran `{call.name}` with those arguments earlier. "
                        "Do not repeat actions. If the change is complete and verified, "
                        "call the `finish` tool now with a short summary; otherwise take "
                        "a genuinely different action."
                    ),
                })
                if redundant >= 3:
                    console.print("[yellow]Repeated actions without progress; moving to evaluation.[/yellow]")
                    self.log.warning("No-progress loop detected at step %d; aborting phase", step)
                    self._audit("no_progress_abort", step=step, tool=call.name, redundant=redundant)
                    self.emit("no_progress", step=step, tool=call.name, redundant=redundant)
                    break
            else:
                seen.add(sig)
        self.fsm.transition("execution_done")

    async def _evaluation_step(self) -> None:
        # Run tests/compile off the event loop so a long suite doesn't block it.
        result = await asyncio.to_thread(self.evaluator.evaluate, self.workspace)
        style = "green" if result.passed else "red"
        console.print(Panel(result.summary, title="Evaluation", border_style=style))
        self.log.info("Evaluation passed=%s: %s", result.passed, result.summary)
        self._audit(
            "evaluation", passed=result.passed,
            summary=result.summary, ran_tests=result.ran_tests,
        )
        self.emit("evaluation", passed=result.passed, summary=result.summary)
        if result.passed:
            self.fsm.transition("passed")
        else:
            self.frame.last_error_summary = result.summary
            self.frame.metadata["last_eval"] = result
            self.fsm.transition("failed")

    async def _maybe_escalate(self) -> Optional[str]:
        """Ask a human for a hint once, when the retry budget is exhausted."""
        if self._escalation_callback is None or self.frame.metadata.get("escalated"):
            return None
        self.frame.metadata["escalated"] = True
        summary = self.frame.last_error_summary or "The change repeatedly failed evaluation."
        eval_result = self.frame.metadata.get("last_eval")
        details = (getattr(eval_result, "details", "") or "")[:2000]
        console.print("[yellow]Escalating to a human for a hint...[/yellow]")
        self.log.info("Escalating to human after %d retries", self.frame.retry_count)
        self._audit("escalation_requested", summary=summary)
        try:
            hint = await self._escalation_callback(f"{summary}\n\n{details}".strip())
        except Exception as exc:  # never let escalation crash the run
            self.log.warning("Escalation failed: %s", exc)
            return None
        return (hint or "").strip() or None

    async def _reflexion_step(self) -> None:
        if self.frame.retry_count >= self.frame.max_retries:
            hint = await self._maybe_escalate()
            if hint:
                self.frame.add_reflection(f"Human hint: {hint}")
                self.frame.messages.append({
                    "role": "user",
                    "content": (
                        f"A human operator reviewed the failures and provided this hint: "
                        f"{hint}\nUse it to fix the code, then call finish."
                    ),
                })
                # Grant one more round of attempts.
                self.frame.max_retries += max(1, self.frame.max_retries)
                self._audit("escalation_hint", hint=hint[:500])
                # A human hint is high-value — remember it for future runs.
                self.memory.add(hint, kind="lesson", task=self.frame.task_description)
                self.emit("escalation_resolved", hint=hint)
                self.fsm.transition("retry")
                return
            console.print("[yellow]Retry budget exhausted.[/yellow]")
            self.log.info("Retry budget exhausted after %d retries", self.frame.retry_count)
            self._audit("give_up", retries=self.frame.retry_count)
            # Why the run ended is the most important thing about a failed run, so it
            # must reach every surface — not just the console. Without this emit, a
            # dashboard or editor client shows a bare "error" with no reason.
            self.emit("give_up", retries=self.frame.retry_count,
                      summary=self.frame.last_error_summary or "")
            self.fsm.transition("give_up")
            return
        self.frame.retry_count += 1
        eval_result = self.frame.metadata.get("last_eval")
        lesson = await self.reflexion.reflect(self.frame.task_description, eval_result) if eval_result else ""
        self.log.info("Reflexion retry %d: %s", self.frame.retry_count, lesson[:200])
        self._audit("reflexion", retry=self.frame.retry_count, lesson=lesson[:500])
        self.emit("reflexion", retry=self.frame.retry_count, lesson=lesson)
        if lesson:
            self.frame.add_reflection(lesson)
            self.frame.messages.append(
                {"role": "user", "content": f"The change failed evaluation. {lesson} Fix it and call finish."}
            )
        self.fsm.transition("retry")

    # -- helpers -------------------------------------------------------------
    async def _handle_error(self, error: Exception) -> None:
        metrics = self.model_circuit.get_metrics()
        if isinstance(error, TransientError):
            console.print(f"[yellow]Transient error ({error}). Circuit: {metrics['state']}[/yellow]")
        else:
            console.print(f"[bold red]Error:[/bold red] {error}")
        # A TransientError is an *expected* operational failure — the model server went
        # away — and the console has already said so in one line. Dumping 30 lines of
        # httpx internals on top of it buries the message and reads like a crash, when
        # the agent in fact handled it exactly as designed. Keep the traceback for the
        # unexpected errors, where it is the only clue you get.
        self.log.error(
            "Error in state %s: %s", self.fsm.state.value, error,
            exc_info=not isinstance(error, TransientError),
        )
        self._audit(
            "error", state=self.fsm.state.value, error=str(error),
            error_type=type(error).__name__, circuit=metrics["state"],
        )
        if self.fsm.can("error"):
            self.fsm.transition("error")
        else:  # already terminal or unexpected state
            self.fsm.state = AgentState.ERROR

    def _finalize(self) -> None:
        try:
            self.sandbox.stop()
        finally:
            self._print_stats()
            state = self.fsm.state.value
            self.log.info("Task end in state=%s retries=%d", state, self.frame.retry_count)
            self._audit(
                "task_end", final_state=state, retries=self.frame.retry_count,
                **self.stats.as_dict(),
            )
            self.emit(
                "run_finished",
                final_state=state,
                summary=self.frame.metadata.get("finish_summary", ""),
                stats=self.stats.as_dict(),
            )
            console.print(f"[bold]Session ended in state:[/bold] {state}")

    def _print_stats(self) -> None:
        s = self.stats
        if s.model_calls == 0:
            return
        table = Table(title="Run summary", show_header=False, title_style="bold")
        table.add_row("Run id", self.run_id)
        table.add_row("Model", self.model_name)
        table.add_row("Model calls", str(s.model_calls))
        table.add_row("Prompt tokens", f"{s.prompt_tokens:,}")
        table.add_row("Completion tokens", f"{s.completion_tokens:,}")
        table.add_row("Total tokens", f"{s.total_tokens:,}")
        table.add_row("Model time", f"{s.total_seconds:.1f}s")
        table.add_row("Throughput", f"{s.tokens_per_second:.1f} tok/s")
        table.add_row("Circuit", self.model_circuit.get_metrics()["state"])
        console.print(table)
