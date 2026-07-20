"""The orchestrator: an FSM-driven plan/execute/evaluate/reflect loop."""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Awaitable, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape

from .context import ContextManager
from .errors import TransientError
from .customizations import CustomizationLoader
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
from .tools.parser import ToolParser, ToolCall
from .tools.registry import ToolRegistry, ToolResult
from .utils.circuit_breaker import CircuitBreaker
from .utils.retry import async_retry

logger = logging.getLogger(__name__)
console = Console()

# Default bound on tool calls within a single execution phase.
DEFAULT_MAX_STEPS = 25

# Tools that change the workspace. Everything else only looks.
MUTATING_TOOLS = frozenset({
    "write_file", "search_replace", "replace_all",
    "add_docstring", "add_parameter", "rename_symbol"
})
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
        planner_editor: bool = False,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.max_steps = max_steps
        # A green test suite only proves the agent finished if the agent actually
        # did something. On a refactor the suite is green BEFORE the first edit, so
        # an agent that stalls without touching a file evaluates green and reaches
        # `done` having changed nothing. Track both halves of that condition.
        self._mutations = 0            # successful workspace edits, whole run
        self._no_progress_abort = False  # the loop detector bailed at some point
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
        self._paused = False
        self._paused_event = asyncio.Event()
        self._paused_event.set()
        self._stopped = False
        self.stop_when_green = True
        self.planner_editor = planner_editor

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
        self.customizations = CustomizationLoader(self.workspace)
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
        self.initial_test_files = self._find_test_files()
        self.evaluator = Evaluator(
            self.sandbox, self.policy,
            test_command=test_command,
            initial_test_files=self.initial_test_files
        )

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

        self.reflexion = ReflexionEngine(
            self.model, self.evaluator, self.sandbox, self.policy,
            indexer=self.indexer, chat_fn=self._chat
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
                f"[bold green]Task:[/bold green] {escape(task)}\n[dim]run {self.run_id} · model {self.model_name}[/dim]",
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
                if self._stopped:
                    self.log.info("Run stopped by user request")
                    self.emit("run_stopped", reason="User request")
                    if self.fsm.can("error"):
                        self.fsm.transition("error")
                    else:
                        self.fsm.state = AgentState.ERROR
                    break

                if self._paused:
                    self.log.info("Run paused by user request. Waiting for resume...")
                    self.emit("run_paused")
                    await self._paused_event.wait()
                    self.log.info("Run resumed by user request.")
                    self.emit("run_resumed")
                    if self._stopped:
                        continue

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
            from rich.markup import escape
            console.print(f"[dim]{escape(label)}[/dim]")
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
        
        # Load workspace customizations (rules and matched skills)
        custom_rules = self.customizations.load_rules()
        custom_skills = self.customizations.load_skills(self.frame.task_description)
        customizations = custom_rules + custom_skills

        if self.planner_editor:
            messages = prompts.planner_messages(self.frame.task_description, skeleton, memory_text, customizations=customizations)
            response = await self._model_turn(messages, label="Planning Checklist...")
            checklist_text = response.content.strip()
            
            import re
            json_match = re.search(r"```json\s*(.*?)\s*```", checklist_text, re.DOTALL)
            if json_match:
                checklist_text = json_match.group(1).strip()
            elif checklist_text.startswith("```") and checklist_text.endswith("```"):
                checklist_text = checklist_text.strip("`").strip()
            
            import json
            try:
                checklist = json.loads(checklist_text)
                if not isinstance(checklist, list):
                    raise ValueError("JSON is not a list")
            except Exception as exc:
                self.log.warning("Planner returned invalid JSON checklist: %s", exc)
                target_file = self._find_target_file() or "solution.py"
                checklist = [{
                    "path": target_file,
                    "change_description": f"Implement the requested task: {self.frame.task_description}",
                    "is_new": not (self.workspace / target_file).exists()
                }]
            
            if isinstance(checklist, list):
                for task in checklist:
                    if isinstance(task, dict) and task.get("path"):
                        target_file = self.workspace / task["path"]
                        if target_file.exists():
                            task["is_new"] = False
            self.frame.metadata["checklist"] = checklist
            self.frame.plan = json.dumps(checklist, indent=2)
            self.log.info("Planner checklist created with %d tasks", len(checklist))
            self.emit("plan", text=self.frame.plan)
            if not self._stream:
                console.print(Panel(escape(self.frame.plan), title="Checklist", border_style="cyan"))

            exclude_names = set()
            if self._is_single_file_workspace():
                exclude_names.update({"rename_symbol", "add_parameter", "add_docstring"})

            self.frame.messages = [
                {"role": "system", "content": prompts.system_prompt(exclude_names=exclude_names)}
            ]
        else:
            messages = prompts.planning_messages(self.frame.task_description, skeleton, memory_text, customizations=customizations)
            response = await self._model_turn(messages, label="Planning...")
            self.frame.plan = response.content.strip()
            self.log.info("Plan created (%d chars)", len(self.frame.plan or ""))
            self._audit("plan_created", plan_chars=len(self.frame.plan or ""))
            self.emit("plan", text=self.frame.plan or "")
            if not self._stream:
                console.print(Panel(escape(self.frame.plan or "(no plan)"), title="Plan", border_style="cyan"))

            # Seed the execution conversation.
            exclude_names = set()
            if self._is_single_file_workspace():
                exclude_names.update({"rename_symbol", "add_parameter", "add_docstring"})
            system_content = prompts.system_prompt(exclude_names=exclude_names)
            if customizations:
                system_content += "\n\nAdditional instructions and guidelines for this workspace/task:\n" + "\n\n".join(customizations)
            self.frame.messages = [
                {"role": "system", "content": system_content},
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
        if self.planner_editor:
            checklist = self.frame.metadata.get("checklist") or []
            if not checklist:
                self.log.warning("No checklist found for planner_editor execution")
                self.fsm.transition("execution_done")
                return

            reflexion_lesson = self.frame.reflections[-1] if self.frame.reflections else ""

            for idx, item in enumerate(checklist):
                if self._stopped:
                    break
                if self._paused:
                    self.log.info("Run paused by user request. Waiting for resume...")
                    self.emit("run_paused")
                    await self._paused_event.wait()
                    self.log.info("Run resumed by user request.")
                    self.emit("run_resumed")
                    if self._stopped:
                        break

                path = item.get("path")
                change_description = item.get("change_description")
                is_new = item.get("is_new", False)

                self.log.info("Processing task %d/%d: %s (is_new=%s)", idx + 1, len(checklist), path, is_new)
                self.emit("tool_call", step=idx+1, tool=f"editor:{path}", args={"change": change_description})

                # Read clean/fresh content from workspace disk
                target_path = self.workspace / path
                original_content = ""
                file_lines = 0
                if not is_new and target_path.exists():
                    try:
                        original_content = target_path.read_text(encoding="utf-8", errors="replace")
                        file_lines = len(original_content.splitlines())
                    except Exception as e:
                        self.log.warning("Failed to read file %s: %s", path, e)

                exclude_names = set()
                if is_new:
                    exclude_names.update({"search_replace", "replace_all"})
                if self._is_single_file_workspace():
                    exclude_names.update({"rename_symbol", "add_parameter", "add_docstring"})

                # Initialize subtask messages
                try:
                    repo_map = self.indexer.get_repo_skeleton()
                except Exception as e:
                    self.log.warning("Failed to get repo skeleton: %s", e)
                    repo_map = ""

                subtask_messages = [
                    {"role": "system", "content": prompts.subtask_system_prompt(path, change_description, exclude_names=exclude_names)},
                    {"role": "user", "content": prompts.subtask_user_prompt(
                        task=self.frame.task_description,
                        path=path,
                        change_description=change_description,
                        content=original_content,
                        repo_map=repo_map,
                        reflexion_lesson=reflexion_lesson,
                        test_content=self._relevant_test_content(path)
                    )}
                ]

                # Local subtask tool-use execution loop (up to 5 steps)
                subtask_success = False
                offered_tools = self.tools.get_descriptions()
                
                if exclude_names:
                    offered_tools = [t for t in offered_tools if t.get("function", {}).get("name") not in exclude_names]

                mutation_steps = 0
                sub_loc_counts: dict = {}  # edits per (file, region) — catches same-spot thrash
                for sub_step in range(1, 16):
                    if self._stopped:
                        break
                    
                    response = await self._model_turn(subtask_messages, offered_tools, label=f"Editing {path} (subtask step {sub_step})...")
                    subtask_messages.append({"role": "assistant", "content": response.content or ""})

                    # Parse tool calls from model response
                    native = self.parser.parse_native(response.tool_calls)
                    calls = native or self.parser.parse(response.content)

                    # Fallback for implicit code blocks
                    if not calls:
                        is_py = path.endswith(".py")
                        implicit_code = self._extract_implicit_code(response.content or "", is_py)
                        if implicit_code:
                            self.log.info("Converted implicit code block to write_file for %s", path)
                            calls = [ToolCall(name="write_file", arguments={"path": path, "content": implicit_code})]
                            
                            # If no syntax error in the python file, treat it as successful direct completion
                            if is_py:
                                from .perception.analysis import python_syntax_errors
                                errors = python_syntax_errors(implicit_code, filename=path)
                                if not errors:
                                    result = await self.tools.execute("write_file", {"path": path, "content": implicit_code})
                                    if result.ok:
                                        self._mutations += 1
                                    subtask_success = True
                                    subtask_messages.append({
                                        "role": "user",
                                        "content": f"File '{path}' successfully written with no syntax errors. Subtask completed."
                                    })
                                    break
                            else:
                                result = await self.tools.execute("write_file", {"path": path, "content": implicit_code})
                                if result.ok:
                                    self._mutations += 1
                                subtask_success = True
                                subtask_messages.append({
                                    "role": "user",
                                    "content": f"File '{path}' successfully written. Subtask completed."
                                })
                                break

                    if not calls:
                        if self.parser.saw_truncated_call(response.content or ""):
                            # The call was cut off mid-JSON (too long), not absent.
                            # Telling the model to "use a tool" makes it resend the
                            # same oversized call and burn the step budget; tell it
                            # to shrink the edit instead.
                            subtask_messages.append({
                                "role": "user",
                                "content": (
                                    "Your previous tool call was cut off before it finished "
                                    "(incomplete JSON), so it was NOT applied. It was too long. "
                                    "Send a SMALLER edit: change fewer lines at once, or use "
                                    "search_replace on a short, unique snippet instead of "
                                    "rewriting a large block in one call."
                                ),
                            })
                        else:
                            # Nudge the model to use a tool if it only produced prose
                            subtask_messages.append({
                                "role": "user",
                                "content": "Respond with exactly one tool call in the required JSON format.",
                            })
                        continue

                    call = calls[0]
                    self.log.info("Subtask tool call: %s %s", call.name, call.arguments)

                    # Intercept the finish tool
                    if call.name == "finish":
                        can_finish = True
                        if self._is_single_file_workspace():
                            eval_result = await asyncio.to_thread(self.evaluator.evaluate, self.workspace)
                            if not eval_result.passed:
                                can_finish = False
                                subtask_messages.append({
                                    "role": "user",
                                    "content": f"Cannot finish subtask. Local tests are failing with this error:\n{eval_result.summary}\nPlease resolve the failures or correct the code before calling finish."
                                })
                        else:
                            if path.endswith(".py") and target_path.exists():
                                from .perception.analysis import python_syntax_errors
                                try:
                                    current_content = target_path.read_text(encoding="utf-8")
                                    errors = python_syntax_errors(current_content, filename=path)
                                    if errors:
                                        can_finish = False
                                        subtask_messages.append({
                                            "role": "user",
                                            "content": f"Cannot finish subtask. The file '{path}' has compilation/syntax errors:\n" + "; ".join(errors) + "\nPlease fix the syntax errors before calling finish."
                                        })
                                except Exception:
                                    pass

                        if can_finish:
                            subtask_success = True
                            subtask_messages.append({
                                "role": "user",
                                "content": "Subtask completed successfully."
                            })
                            break
                        else:
                            continue

                    # Execute the tool
                    mutation_tools = ("write_file", "search_replace", "edit_lines", "replace_all", "add_parameter", "add_docstring", "rename_symbol")
                    if call.name in mutation_tools:
                        if mutation_steps >= 4:
                            result = ToolResult(False, "Modification budget exhausted. You have already made 4 edits. You must run verification tests and call finish immediately.")
                        else:
                            result = await self.tools.execute(call.name, call.arguments)
                            if result.ok:
                                self._mutations += 1
                                mutation_steps += 1
                                if mutation_steps >= 4:
                                    result.content += "\n\nWarning: You have exhausted your file modification budget. You must verify your current code via tests and call finish immediately."
                    else:
                        result = await self.tools.execute(call.name, call.arguments)
                    
                    subtask_messages.append({
                        "role": "user",
                        "content": f"Tool '{call.name}' result: {result.content}"
                    })

                    # Location-thrash guard: re-editing the same region over and
                    # over (with slightly different content each time) is the
                    # dominant non-convergence pattern and the mutation budget above
                    # does not catch it — a failed or dropped edit costs a step but
                    # not budget. After a few edits to the same spot, tell the model
                    # to stop patching and rewrite the whole file, which is what the
                    # model solves one-shot.
                    if call.name in ("edit_lines", "search_replace"):
                        loc_key = (
                            str(call.arguments.get("path", path)),
                            call.arguments.get("start_line")
                            if call.name == "edit_lines"
                            else str(call.arguments.get("search", ""))[:40],
                        )
                        sub_loc_counts[loc_key] = sub_loc_counts.get(loc_key, 0) + 1
                        if sub_loc_counts[loc_key] == 3:
                            subtask_messages.append({
                                "role": "user",
                                "content": (
                                    f"You have edited the same part of '{path}' several times "
                                    "and it is still not right. Stop making small edits there. "
                                    "Read the whole file, then replace it in ONE `write_file` "
                                    "call with a complete, correct implementation."
                                ),
                            })

                    # Compile gate syntax check for python edits
                    if path.endswith(".py") and target_path.exists():
                        from .perception.analysis import python_syntax_errors
                        try:
                            current_content = target_path.read_text(encoding="utf-8")
                            errors = python_syntax_errors(current_content, filename=path)
                            if errors:
                                subtask_messages.append({
                                    "role": "user",
                                    "content": f"Warning: The current file '{path}' has compilation/syntax errors:\n" + "; ".join(errors) + "\nPlease fix the syntax errors."
                                })
                        except Exception:
                            pass

                self.log.info("Finished task %d/%d for %s: success=%s", idx + 1, len(checklist), path, subtask_success)
                self.emit("tool_result", step=idx+1, tool=f"editor:{path}", ok=subtask_success, content=f"Subtask completed for {path}")

            self.fsm.transition("execution_done")
            return

        tools = self.tools.get_descriptions()
        if self._is_single_file_workspace():
            exclude_names = {"rename_symbol", "add_parameter", "add_docstring"}
            tools = [t for t in tools if t.get("function", {}).get("name") not in exclude_names]
        seen: set[tuple] = set()   # every tool-call signature performed this phase
        redundant = 0              # count of repeated (already-performed) actions
        for step in range(1, self.max_steps + 1):
            if self._stopped:
                break
            if self._paused:
                self.log.info("Run paused by user request. Waiting for resume...")
                self.emit("run_paused")
                await self._paused_event.wait()
                self.log.info("Run resumed by user request.")
                self.emit("run_resumed")
                if self._stopped:
                    break

            response = await self._model_turn(self.frame.messages, tools, label=f"step {step}")

            native = self.parser.parse_native(response.tool_calls)
            calls = native or self.parser.parse(response.content)

            if not calls:
                target_file = self._find_target_file()
                if target_file:
                    is_py = target_file.endswith(".py")
                    implicit_code = self._extract_implicit_code(response.content or "", is_py)
                    if implicit_code:
                        self.log.info("Converted implicit code block to write_file tool call for %s", target_file)
                        call = ToolCall(name="write_file", arguments={"path": target_file, "content": implicit_code})
                        calls = [call]

            if not calls:
                console.print(f"[dim]step {step}: model produced no tool call[/dim]")
                self.frame.messages.append({"role": "assistant", "content": response.content})
                if self.parser.saw_truncated_call(response.content or ""):
                    # Cut off mid-JSON (too long), not absent — ask for a smaller edit.
                    self.frame.messages.append({
                        "role": "user",
                        "content": (
                            "Your previous tool call was cut off before it finished "
                            "(incomplete JSON), so it was NOT applied. It was too long. Send a "
                            "SMALLER edit: change fewer lines at once, or use search_replace on "
                            "a short, unique snippet instead of rewriting a large block."
                        ),
                    })
                else:
                    # Nudge the model to use a tool if it only produced prose.
                    self.frame.messages.append({
                        "role": "user",
                        "content": "Respond with exactly one tool call in the required JSON format.",
                    })
                continue

            self.frame.messages.append({"role": "assistant", "content": response.content or ""})

            call = calls[0]
            console.print(f"[bold cyan]→ {call.name}[/bold cyan] {list(call.arguments)}")
            self.emit("tool_call", step=step, tool=call.name, args=call.arguments)
            if self._is_single_file_workspace() and call.name in {"rename_symbol", "add_parameter", "add_docstring"}:
                result = ToolResult(False, f"Error: The tool '{call.name}' is not available in a single-file workspace. Please use 'write_file' or 'search_replace' to make edits.")
            else:
                result = await self.tools.execute(call.name, call.arguments)
            # Redact secrets once, at the boundary — before the output reaches the
            # console, the model's context, or the dashboard. Any tool's output
            # (read_file, search, …) is covered here, not just run_command.
            safe_content = self.policy.scrub(result.content)
            from rich.markup import escape
            console.print(f"[dim]{escape(safe_content[:500])}[/dim]")
            self.log.info("step %d: %s ok=%s", step, call.name, result.ok)
            if result.ok and call.name in MUTATING_TOOLS:
                self._mutations += 1
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

            # Stop-when-green guard: if tests pass, force finish.
            if self.stop_when_green and (call.name in MUTATING_TOOLS or call.name == "run_command"):
                eval_result = await asyncio.to_thread(self.evaluator.evaluate, self.workspace)
                if eval_result.passed and eval_result.ran_tests:
                    self.log.info("Stop-when-green: tests passed. Forcing finish.")
                    console.print("[green]Stop-when-green: tests passed. Forcing finish.[/green]")
                    result.is_final = True
                    result.content = "Stop-when-green: tests passed successfully."

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
                    self._no_progress_abort = True
                    break
            else:
                seen.add(sig)

            if result.is_final:
                if self.lsp:
                    await self.lsp.await_diagnostics(timeout=2.0)
                    has_errors = False
                    for client in getattr(self.lsp, "_clients", {}).values():
                        for diags in client.diagnostics.values():
                            if any(d.get("severity", 3) == 1 for d in diags):
                                has_errors = True
                                break
                        if has_errors:
                            break
                    if has_errors:
                        diagnostics_text = self.lsp.get_all_diagnostics()
                        console.print(f"[yellow]Blocked finish: compiler diagnostics reported errors[/yellow]")
                        self.frame.messages.append({
                            "role": "user",
                            "content": (
                                "Wait, you cannot finish yet. There are compile/lint errors in the workspace:\n"
                                f"{diagnostics_text}\n"
                                "Please read the files, fix these errors, and only then call finish."
                            )
                        })
                        result.is_final = False
                        result.ok = False
                        result.content = f"Blocked finish: compiler diagnostics reported errors:\n{diagnostics_text}"
                        continue
                self.frame.metadata["finish_summary"] = result.content
                break
        self.fsm.transition("execution_done")

    async def _evaluation_step(self) -> None:
        # Run tests/compile off the event loop so a long suite doesn't block it.
        result = await asyncio.to_thread(self.evaluator.evaluate, self.workspace)
        if result.passed and self._no_progress_abort and self._mutations == 0:
            # The loop detector bailed and not one edit landed, yet the suite is
            # green — because it was green before we started. That is a stalled
            # run wearing a success's clothes; refuse to certify it.
            result = replace(
                result,
                passed=False,
                summary=(
                    "Tests pass, but the agent stopped making progress without editing "
                    "any file — the suite was already green before the task began, so "
                    "it proves nothing here. Treating this as failure, not success."
                ),
            )
        style = "green" if result.passed else "red"
        console.print(Panel(escape(result.summary), title="Evaluation", border_style=style))
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

        if self.planner_editor and eval_result:
            checklist = self.frame.metadata.get("checklist") or []
            modified_paths = [item.get("path") for item in checklist if item.get("path")]
            impacted_tests = self.find_impacted_tests(modified_paths)

            refiner_msgs = prompts.planner_refiner_messages(
                task=self.frame.task_description,
                checklist=checklist,
                eval_result=str(eval_result),
                lesson=lesson,
                impacted_tests=impacted_tests
            )
            try:
                response = await self._model_turn(refiner_msgs, label="Refining Checklist...")
                refined_text = response.content.strip()
                import re
                json_match = re.search(r"```json\s*(.*?)\s*```", refined_text, re.DOTALL)
                if json_match:
                    refined_text = json_match.group(1).strip()
                elif refined_text.startswith("```") and refined_text.endswith("```"):
                    refined_text = refined_text.strip("`").strip()
                
                import json
                refined_checklist = json.loads(refined_text)
                if isinstance(refined_checklist, list) and len(refined_checklist) > 0:
                    for task in refined_checklist:
                        if isinstance(task, dict) and task.get("path"):
                            target_file = self.workspace / task["path"]
                            if target_file.exists():
                                task["is_new"] = False
                    self.frame.metadata["checklist"] = refined_checklist
                    self.frame.plan = json.dumps(refined_checklist, indent=2)
                    self.log.info("Refined checklist created with %d tasks", len(refined_checklist))
                    self.emit("plan", text=self.frame.plan)
            except Exception as exc:
                self.log.warning("Failed to refine checklist: %s. Re-running original checklist.", exc)
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

    def pause(self) -> None:
        """Pause execution at the next checkpoint."""
        self._paused = True
        self._paused_event.clear()

    def resume(self) -> None:
        """Resume execution."""
        self._paused = False
        self._paused_event.set()

    def stop(self) -> None:
        """Stop execution immediately at the next checkpoint."""
        self._stopped = True
        self._paused_event.set()

    def _find_test_files(self) -> list[str]:
        test_files = []
        for pattern in ("test_*.py", "*_test.py"):
            for p in self.workspace.rglob(pattern):
                parts = p.relative_to(self.workspace).parts
                if any(x in parts for x in (".venv", "venv", "__pycache__", ".git")):
                    continue
                test_files.append(p.relative_to(self.workspace).as_posix())
        return test_files

    def _find_target_file(self) -> Optional[str]:
        solution_path = self.workspace / "solution.py"
        if solution_path.exists():
            return "solution.py"

        candidates = []
        extensions = ("*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.cpp", "*.c", "*.h")
        for ext in extensions:
            for p in self.workspace.rglob(ext):
                parts = p.relative_to(self.workspace).parts
                if any(x in parts for x in (".venv", "venv", "__pycache__", ".git", "node_modules", "target")):
                    continue
                name_lower = p.name.lower()
                if "test" in name_lower or "spec" in name_lower:
                    continue
                candidates.append(p.relative_to(self.workspace).as_posix())

        if len(candidates) == 1:
            return candidates[0]
        return None

    def _extract_implicit_code(self, text: str, is_py: bool) -> Optional[str]:
        import re
        import ast

        text_stripped = text.strip()
        if not text_stripped:
            return None

        # 1. Try to extract fenced code blocks first
        fenced_pattern = re.compile(r"```([a-zA-Z0-9+#-]*)?\s*\n?(.*?)\n?\s*```", re.DOTALL)
        fenced_blocks = []
        for lang, code in fenced_pattern.findall(text):
            lang = (lang or "").strip().lower()
            if lang in ("json", "tool_call", "tool", "tool_name"):
                continue
            fenced_blocks.append(code.strip())

        if fenced_blocks:
            return "\n\n".join(fenced_blocks)

        # 2. If it is Python, check if we can extract bare code using AST validation
        if is_py:
            try:
                ast.parse(text_stripped)
                return text_stripped
            except SyntaxError:
                pass

            # Try to find the first line starting with a python keyword
            lines = text.splitlines()
            start_idx = -1
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(("def ", "async def ", "class ", "import ", "from ")):
                    start_idx = idx
                    break

            if start_idx != -1:
                candidate_code = "\n".join(lines[start_idx:])
                try:
                    ast.parse(candidate_code.strip())
                    return candidate_code.strip()
                except SyntaxError:
                    # Strip lines from the bottom one-by-one to remove trailing prose
                    cand_lines = candidate_code.splitlines()
                    while len(cand_lines) > 1:
                        cand_lines.pop()
                        try:
                            ast.parse("\n".join(cand_lines).strip())
                            return "\n".join(cand_lines).strip()
                        except SyntaxError:
                            continue
                    return candidate_code.strip()

        return None

    def _relevant_test_content(self, path: str, limit: int = 6000) -> str:
        """The test file that exercises `path`, so the editor sees the exact spec.

        Without the test in context, the editor guesses the exact strings and
        values the test asserts on — the dominant remaining failure mode (e.g.
        writing 'Graph item is malformed' when the test requires 'Node is
        malformed'). The bare model passes these when the test is in its prompt;
        the agent's editor never received it. We only *read* the test here; the
        editor is still told not to modify it. Skips when `path` is itself a test.
        """
        try:
            name = Path(path).name.lower()
            if "test" in name or "spec" in name:
                return ""
            stem = Path(path).stem
            skip = {".venv", "venv", "__pycache__", ".git", "node_modules", "target"}
            # Prefer the test whose name matches this file; else any test file
            # (single-file tasks have exactly one).
            preferred = [self.workspace / f"{stem}_test.py", self.workspace / f"test_{stem}.py"]
            others = [
                p for pat in ("*_test.py", "test_*.py")
                for p in sorted(self.workspace.rglob(pat))
                if not (set(p.relative_to(self.workspace).parts) & skip)
            ]
            for cand in preferred + others:
                if cand.exists():
                    text = cand.read_text(encoding="utf-8", errors="replace")
                    if len(text) > limit:
                        text = text[:limit] + "\n# ...(test truncated)..."
                    return text
            return ""
        except Exception as e:
            self.log.warning("Could not load test content for %s: %s", path, e)
            return ""

    def _is_single_file_workspace(self) -> bool:
        candidates = []
        extensions = ("*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.cpp", "*.c", "*.h")
        for ext in extensions:
            for p in self.workspace.rglob(ext):
                parts = p.relative_to(self.workspace).parts
                if any(x in parts for x in (".venv", "venv", "__pycache__", ".git", "node_modules", "target")):
                    continue
                name_lower = p.name.lower()
                if "test" in name_lower or "spec" in name_lower:
                    continue
                candidates.append(p)
        return len(candidates) <= 1

    def find_impacted_tests(self, modified_paths: List[str]) -> List[str]:
        """Find all test files impacted by changes in modified_paths (transitive closure)."""
        impacted_tests = set()
        visited_modules = set()
        
        symbol_index = self.tools._symbol_index()
        
        queue = []
        for p in modified_paths:
            path_obj = Path(p)
            if path_obj.suffix.lower() == ".py":
                mod_parts = list(path_obj.with_suffix("").parts)
                mod_name = ".".join(mod_parts)
                queue.append(mod_name)
                visited_modules.add(mod_name)

        while queue:
            curr_mod = queue.pop(0)
            imports = symbol_index.importers(curr_mod)
            for imp_path, line, module in imports:
                if any(pat in Path(imp_path).name.lower() for pat in ("test_", "_test")):
                    impacted_tests.add(imp_path)
                
                imp_path_obj = Path(imp_path)
                if imp_path_obj.suffix.lower() == ".py":
                    imp_mod = ".".join(imp_path_obj.with_suffix("").parts)
                    if imp_mod not in visited_modules:
                        visited_modules.add(imp_mod)
                        queue.append(imp_mod)
                        
        return sorted(list(impacted_tests))
