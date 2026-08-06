"""The orchestrator: an FSM-driven plan/execute/evaluate/reflect loop."""
from __future__ import annotations

import ast
import asyncio
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Optional, List, Dict, Any

from .audit import AuditLogger
from .context import ContextManager
from .display import OrchestratorDisplay
from .errors import TransientError
from .event_bus import EventBus
from .customizations import CustomizationLoader
from .factory import ComponentFactory
from .file_utils import FileSystemHelper
from .memory import MemoryStore
from .code_extract import CodeExtractor
from .evaluation.evaluator import Evaluator
from .evaluation.reflexion import ReflexionEngine
from .fsm import FSM, AgentState
from .model_service import ModelService
from .perception.indexer import WorkspaceIndexer
from .perception.lsp import LSPManager
from . import prompts
from .runtime import RuntimeState
from .sandbox.config import SandboxConfig
from .sandbox.manager import SandboxManager
from .guardrails.policy import SecurityPolicy
from .state import AgentFrame
from .task_analysis import TaskAnalyzer
from .telemetry import RunStats
from .test_analysis import find_impacted_tests
from .tools.parser import ToolParser
from .tools.registry import ToolRegistry
from .utils.circuit_breaker import CircuitBreaker
from .utils.retry import async_retry
from .agents.planner import PlannerAgent
from .agents.config import AgentConfig
from .agents.coder import CoderAgent
from .agents.reviewer import ReviewerAgent

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_STEPS = 25
MAX_BLOCKED_FINISHES = 2
DEFAULT_MODEL_RETRIES = 3
DEFAULT_CONTEXT_WINDOW = 8192


class OrchestratorState(Enum):
    """Internal orchestrator states."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    workspace: Path
    model_name: str = "qwen2.5:7b"
    interactive: bool = True
    sandbox_backend: str = "auto"
    max_retries: int = 2
    max_steps: int = DEFAULT_MAX_STEPS
    model_retries: int = DEFAULT_MODEL_RETRIES
    log_dir: Optional[Path] = None
    host: str = "http://localhost:11434"
    test_command: Optional[str] = None
    sandbox_network: bool = False
    num_ctx: int = DEFAULT_CONTEXT_WINDOW
    use_memory: bool = True
    protected_paths: Optional[List[str]] = None
    planner_editor: bool = False
    stop_when_green: bool = True
    request_interval: float = 0.0
    milestones: bool = False
    temperature: float = 0.1
    max_mutations: int = 8

    @classmethod
    def from_kwargs(cls, **kwargs) -> "OrchestratorConfig":
        """Create config from keyword arguments."""
        return cls(
            workspace=Path(kwargs.get("workspace")),
            model_name=kwargs.get("model_name", "qwen2.5:7b"),
            interactive=kwargs.get("interactive", True),
            sandbox_backend=kwargs.get("sandbox_backend", "auto"),
            max_retries=kwargs.get("max_retries", 2),
            max_steps=kwargs.get("max_steps", DEFAULT_MAX_STEPS),
            model_retries=kwargs.get("model_retries", DEFAULT_MODEL_RETRIES),
            log_dir=kwargs.get("log_dir"),
            host=kwargs.get("host", "http://localhost:11434"),
            test_command=kwargs.get("test_command"),
            sandbox_network=kwargs.get("sandbox_network", False),
            num_ctx=kwargs.get("num_ctx", DEFAULT_CONTEXT_WINDOW),
            use_memory=kwargs.get("use_memory", True),
            protected_paths=kwargs.get("protected_paths"),
            planner_editor=kwargs.get("planner_editor", False),
            stop_when_green=kwargs.get("stop_when_green", True),
            temperature=kwargs.get("temperature", 0.1),
            max_mutations=kwargs.get("max_mutations", 8),
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Drives one task run through the FSM, owning the model, tools, sandbox and guardrails."""

    def __init__(
        self,
        workspace: Path,
        model_name: str = "qwen2.5:7b",
        interactive: bool = True,
        sandbox_backend: str = "auto",
        max_retries: int = 2,
        max_steps: int = DEFAULT_MAX_STEPS,
        model_retries: int = DEFAULT_MODEL_RETRIES,
        log_dir: Optional[Path] = None,
        host: str = "http://localhost:11434",
        test_command: Optional[str] = None,
        sandbox_network: bool = False,
        num_ctx: int = DEFAULT_CONTEXT_WINDOW,
        use_memory: bool = True,
        protected_paths: Optional[List[str]] = None,
        event_sink: Optional[Callable[[Dict], None]] = None,
        approval_callback: Optional[Callable[[str, str], Awaitable[bool]]] = None,
        escalation_callback: Optional[Callable[[str], Awaitable[Optional[str]]]] = None,
        planner_editor: bool = False,
        request_interval: float = 0.0,
        milestones: bool = False,
        temperature: float = 0.1,
        max_mutations: int = 8,
    ) -> None:
        self.config = OrchestratorConfig(
            workspace=workspace, model_name=model_name, interactive=interactive,
            sandbox_backend=sandbox_backend, max_retries=max_retries, max_steps=max_steps,
            model_retries=model_retries, log_dir=log_dir, host=host,
            test_command=test_command, sandbox_network=sandbox_network, num_ctx=num_ctx,
            use_memory=use_memory, protected_paths=protected_paths,
            planner_editor=planner_editor, request_interval=request_interval,
            milestones=milestones, temperature=temperature, max_mutations=max_mutations,
        )
        AgentConfig.configure(max_mutations=self.config.max_mutations)
        if milestones:
            self.config.planner_editor = True

        self._state = OrchestratorState.INITIALIZING
        self.run_id = uuid.uuid4().hex[:8]
        self.runtime = RuntimeState(event_sink=event_sink, escalation_callback=escalation_callback)
        self.log = logging.LoggerAdapter(logger, {"run_id": self.run_id})

        # Core state (needed before _init_components wires ModelService)
        self.fsm = FSM()
        self.frame = AgentFrame(task_description="", max_retries=max_retries)
        self.stats = RunStats()

        self._init_components(approval_callback=approval_callback)

        self.planner_agent = PlannerAgent(self)
        self.coder_agent = CoderAgent(self)
        self.reviewer_agent = ReviewerAgent(self)

        self._state = OrchestratorState.RUNNING

    # ---- component wiring ----

    def _init_components(self, approval_callback: Optional[Callable]) -> None:
        self.model = ComponentFactory.create_model(self.config)
        self.model_name = self.config.model_name
        self.context = ContextManager(max_tokens=self.config.num_ctx)
        self.sandbox = ComponentFactory.create_sandbox(self.config)
        self.policy = ComponentFactory.create_policy(self.config)
        self.policy.audit.context = {"run_id": self.run_id}
        self.audit = AuditLogger(self.policy.audit)
        self.indexer = ComponentFactory.create_indexer(self.config)
        self.memory = MemoryStore(self.config.workspace, enabled=self.config.use_memory)
        self.lsp = ComponentFactory.create_lsp(self.config)
        self.tools = ComponentFactory.create_tools(
            sandbox=self.sandbox, policy=self.policy, workspace=self.config.workspace,
            lsp=self.lsp, indexer=self.indexer, memory=self.memory,
            approval_callback=approval_callback,
        )
        self.parser = ToolParser()
        self.customizations = CustomizationLoader(self.config.workspace)
        self.event_bus = EventBus(run_id=self.run_id, sink=self.runtime.event_sink)
        self.initial_test_files = FileSystemHelper.find_test_files(self.config.workspace)
        self.evaluator = Evaluator(
            self.sandbox, self.policy,
            test_command=self.config.test_command, initial_test_files=self.initial_test_files,
        )
        self.model_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=120, name="model")
        retry = async_retry(max_attempts=self.config.model_retries, base_delay=1.0,
                            max_delay=20.0, exceptions=(TransientError,))
        self._chat = self.model_circuit(retry(self.model.chat))
        self._chat_stream = self.model_circuit(retry(self.model.chat_stream))
        self.model_service = ModelService(
            context=self.context,
            get_chat=lambda: self._chat,
            get_chat_stream=lambda: self._chat_stream,
            stats=self.stats,
            event_bus=self.event_bus,
        )
        self.reflexion = ReflexionEngine(
            self.model, self.evaluator, self.sandbox, self.policy,
            indexer=self.indexer, chat_fn=self._chat,
        )

    # ---- public API ----

    @property
    def workspace(self) -> Path:
        if hasattr(self, "config"):
            return self.config.workspace
        return getattr(self, "_mock_workspace", None)

    @workspace.setter
    def workspace(self, value: Path) -> None:
        if hasattr(self, "config"):
            self.config.workspace = value
        else:
            self._mock_workspace = value

    @property
    def interactive(self) -> bool:
        return self.config.interactive

    @property
    def stop_when_green(self) -> bool:
        return self.config.stop_when_green

    @stop_when_green.setter
    def stop_when_green(self, value: bool) -> None:
        self.config.stop_when_green = value

    @property
    def max_steps(self) -> int:
        return self.config.max_steps

    @max_steps.setter
    def max_steps(self, value: int) -> None:
        self.config.max_steps = value

    @property
    def planner_editor(self) -> bool:
        return self.config.planner_editor

    @planner_editor.setter
    def planner_editor(self, value: bool) -> None:
        self.config.planner_editor = value

    # ---- backward-compatible runtime-state accessors ----

    @property
    def _stopped(self) -> bool:
        return self.runtime.stopped

    @_stopped.setter
    def _stopped(self, value: bool) -> None:
        self.runtime.stopped = value

    @property
    def _paused(self) -> bool:
        return self.runtime.paused

    @_paused.setter
    def _paused(self, value: bool) -> None:
        self.runtime.paused = value

    @property
    def _paused_event(self) -> asyncio.Event:
        return self.runtime.paused_event

    @property
    def _mutations(self) -> int:
        return self.runtime.mutations

    @_mutations.setter
    def _mutations(self, value: int) -> None:
        self.runtime.mutations = value

    @property
    def _no_progress_abort(self) -> bool:
        return self.runtime.no_progress_abort

    @_no_progress_abort.setter
    def _no_progress_abort(self, value: bool) -> None:
        self.runtime.no_progress_abort = value

    @property
    def _baseline_green(self) -> Optional[bool]:
        return self.runtime.baseline_green

    @_baseline_green.setter
    def _baseline_green(self, value: Optional[bool]) -> None:
        self.runtime.baseline_green = value

    @property
    def _stream(self) -> bool:
        return self.runtime.stream

    @_stream.setter
    def _stream(self, value: bool) -> None:
        self.runtime.stream = value

    @property
    def _escalation_callback(self) -> Optional[Callable]:
        return self.runtime.escalation_callback

    # ---- run lifecycle ----

    async def run_task(self, task: str, stream: bool = True) -> AgentFrame:
        """Run one task end to end through the FSM and return the final frame."""
        self.frame.task_description = task
        self.runtime.stream = stream
        self.log.info("Task start: %s", task)
        self.audit.record("task_start", task=task, model=self.model_name,
                          workspace=str(self.config.workspace), stream=stream)
        self.event_bus.emit("run_started", task=task, model=self.model_name,
                            workspace=str(self.config.workspace))
        try:
            await self._initialize_environment()
            OrchestratorDisplay.display_task_header(task, self.run_id, self.model_name)
            if not await self._check_model_availability():
                return self.frame
            self.fsm.transition("start")
            transient_backoff = 1.0
            MAX_TRANSIENT_RETRIES = 5
            transient_retries = 0
            while not self.fsm.is_terminal():
                if await self._handle_stop_or_pause():
                    break
                self.emit("state_changed", state=self.fsm.state.value)
                try:
                    await self._execute_state(self.fsm.state)
                    transient_backoff = 1.0
                    transient_retries = 0
                except TransientError as exc:
                    transient_retries += 1
                    if transient_retries > MAX_TRANSIENT_RETRIES:
                        self.log.error(
                            "Transient error persisted after %d retries, giving up: %s",
                            MAX_TRANSIENT_RETRIES, exc,
                        )
                        await self._handle_error(exc)
                        break
                    sleep_for = min(transient_backoff, 30.0)
                    self.log.warning(
                        "Transient error (attempt %d/%d), retrying in %.0fs: %s",
                        transient_retries, MAX_TRANSIENT_RETRIES, sleep_for, exc,
                    )
                    metrics = self.model_circuit.get_metrics()
                    OrchestratorDisplay.print_transient_error(exc, metrics)
                    await asyncio.sleep(sleep_for)
                    transient_backoff *= 2
                except Exception as exc:
                    transient_retries = 0
                    await self._handle_error(exc)
        finally:
            await self._cleanup()
        return self.frame

    def pause(self) -> None:
        self.runtime.paused = True
        self.runtime.paused_event.clear()
        self._state = OrchestratorState.PAUSED

    def resume(self) -> None:
        self.runtime.paused = False
        self.runtime.paused_event.set()
        self._state = OrchestratorState.RUNNING

    def stop(self) -> None:
        self.runtime.stopped = True
        self.runtime.paused_event.set()
        self._state = OrchestratorState.STOPPED

    # ---- private: environment lifecycle ----

    async def _initialize_environment(self) -> None:
        self.sandbox.start()
        if self.lsp is not None:
            try:
                await self.lsp.start()
            except Exception as exc:
                self.log.warning("LSP server failed to start: %s", exc)
                self.lsp = None
        self._capture_green_baseline()

    async def _cleanup(self) -> None:
        await self.model.close()
        if self.lsp is not None:
            try:
                await self.lsp.stop()
            except Exception:
                pass
        self.sandbox.stop()
        self._finalize()

    def _capture_green_baseline(self) -> None:
        if not self.config.stop_when_green:
            self.runtime.baseline_green = False
            return
        try:
            baseline = self.evaluator.evaluate(self.config.workspace)
            self.runtime.baseline_green = bool(baseline.passed and baseline.ran_tests)
        except Exception as exc:
            self.log.warning("Could not capture a green baseline: %s", exc)
            self.runtime.baseline_green = False
            return
        if self.runtime.baseline_green:
            self.log.info("Suite already green before this run; stop-when-green disabled.")
            self.event_bus.emit("baseline_green", disabled_stop_when_green=True)

    # ---- private: FSM drive ----

    async def _check_model_availability(self) -> bool:
        if not await self.model.is_available():
            OrchestratorDisplay.display_model_unavailable(self.model.host)
            self.log.error("Ollama not reachable at %s", self.model.host)
            self.audit.record("model_unavailable", host=self.model.host)
            self.fsm.transition("start")
            self.fsm.transition("error")
            return False
        return True

    async def _handle_stop_or_pause(self) -> bool:
        if self.runtime.stopped:
            self.log.info("Run stopped by user request")
            self.event_bus.emit("run_stopped", reason="User request")
            if self.fsm.can("error"):
                self.fsm.transition("error")
            else:
                self.fsm.state = AgentState.ERROR
            return True
        if self.runtime.paused:
            self.log.info("Run paused. Waiting for resume...")
            self.event_bus.emit("run_paused")
            await self.runtime.paused_event.wait()
            self.log.info("Run resumed.")
            self.event_bus.emit("run_resumed")
            if self.runtime.stopped:
                return True
        return False

    async def _execute_state(self, state: AgentState) -> None:
        if state == AgentState.PLANNING:
            await self.planner_agent.execute()
        elif state == AgentState.EXECUTING:
            await self.coder_agent.execute()
        elif state == AgentState.EVALUATING:
            await self.reviewer_agent.execute_evaluation()
        elif state == AgentState.REFLEXING:
            await self.reviewer_agent.execute_reflexion()
        else:
            self.log.warning("Unknown state: %s", state)

    async def _model_turn(self, messages, tools=None, label: str = "") -> Any:
        """Call the model — delegates to ModelService."""
        return await self.model_service.turn(messages, tools, label=label, stream=self.runtime.stream)

    async def _handle_error(self, error: Exception) -> None:
        metrics = self.model_circuit.get_metrics()
        if isinstance(error, TransientError):
            OrchestratorDisplay.print_transient_error(error, metrics)
        else:
            OrchestratorDisplay.print_error(error)
        self.log.error("Error in state %s: %s", self.fsm.state.value, error,
                        exc_info=not isinstance(error, TransientError))
        self.audit.record("error", state=self.fsm.state.value, error=str(error),
                          error_type=type(error).__name__, circuit=metrics["state"])
        if self.fsm.can("error"):
            self.fsm.transition("error")
        else:
            self.fsm.state = AgentState.ERROR

    def _finalize(self) -> None:
        self._state = OrchestratorState.FINALIZING
        OrchestratorDisplay.print_stats(self.stats, self.run_id, self.model_name, self.model_circuit)
        state = self.fsm.state.value
        self.log.info("Task end in state=%s retries=%d", state, self.frame.retry_count)
        self.audit.record("task_end", final_state=state, retries=self.frame.retry_count,
                          **self.stats.as_dict())
        if state != AgentState.DONE.value and self.stats.model_calls > 0:
            try:
                report = OrchestratorDisplay.write_handoff_report(
                    workspace=self.workspace, run_id=self.run_id, model_name=self.model_name,
                    state=state, retry_count=self.frame.retry_count,
                    max_retries=self.frame.max_retries,
                    last_error_summary=self.frame.last_error_summary or "",
                    eval_result=self.frame.metadata.get("last_eval"),
                    reflections=self.frame.reflections,
                    missing_files=self._missing_requested_files(), log=self.log,
                )
                if report:
                    self.frame.metadata["partial_report"] = report
                    self.audit.record("handoff_written", state=state, retries=self.frame.retry_count)
            except Exception:
                self.log.debug("handoff report generation failed", exc_info=True)
        self.event_bus.emit("run_finished", final_state=state,
                            summary=self.frame.metadata.get("finish_summary", ""),
                            stats=self.stats.as_dict())
        OrchestratorDisplay.print_session_ended(state)
        self._state = OrchestratorState.COMPLETED

    def _write_handoff_report(self, state: str) -> None:
        """Backward-compatible handoff report (delegates to OrchestratorDisplay)."""
        report = OrchestratorDisplay.write_handoff_report(
            workspace=self.workspace, run_id=self.run_id, model_name=self.model_name,
            state=state, retry_count=self.frame.retry_count, max_retries=self.frame.max_retries,
            last_error_summary=self.frame.last_error_summary or "",
            eval_result=self.frame.metadata.get("last_eval"),
            reflections=self.frame.reflections,
            missing_files=self._missing_requested_files(), log=self.log,
        )
        if report:
            self.frame.metadata["partial_report"] = report

    # ---- public utility delegates ----

    def _audit(self, action: str, **fields) -> None:
        self.audit.record(action, **fields)

    def emit(self, event: str, **data) -> None:
        self.event_bus.emit(event, **data)

    def _missing_requested_files(self) -> List[str]:
        task = getattr(self.frame, "task_description", "") or ""
        workspace = getattr(self, "config", getattr(self, "workspace", None))
        if hasattr(workspace, "workspace"):
            workspace = workspace.workspace
        if not workspace:
            return []
        return TaskAnalyzer.extract_requested_files(task, workspace)

    def _find_target_file(self) -> Optional[str]:
        return FileSystemHelper.find_target_file(self.config.workspace)

    def _extract_implicit_code(self, text: str, is_py: bool = False) -> Optional[str]:
        return CodeExtractor.extract_implicit_code(text, is_py)

    def _relevant_test_content(self, path: str, limit: int = 6000) -> str:
        try:
            name = Path(path).name.lower()
            if "test" in name or "spec" in name:
                # For test files, provide the implementation code they likely import
                # so the model can write tests that match the actual API
                impl_content = self._get_implementation_for_test(path, limit)
                return impl_content
            test_path = FileSystemHelper.find_relevant_test(self.config.workspace, path)
            if test_path and test_path.exists():
                text = test_path.read_text(encoding="utf-8", errors="replace")
                if len(text) > limit:
                    text = text[:limit] + "\n# ...(test truncated)..."
                return text
            return ""
        except Exception as e:
            self.log.warning("Could not load test content for %s: %s", path, e)
            return ""

    def _get_implementation_for_test(self, test_path: str, limit: int = 6000) -> str:
        """When writing a test file, find and return the implementation code it imports."""
        try:
            workspace = self.config.workspace
            # Parse the test file to find imports from src/
            test_file = workspace / test_path
            if not test_file.exists():
                return ""
            tree = ast.parse(test_file.read_text(encoding="utf-8", errors="replace"))
            impl_files: List[str] = []
            seen: set = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mod = node.module
                    # Convert module path to file path
                    parts = mod.split(".")
                    for depth in range(len(parts), 0, -1):
                        sub = "/".join(parts[:depth])
                        # Try multiple base locations: workspace root, src/, and workspace/src/
                        for base in [workspace, workspace / "src"]:
                            candidate = base / (sub + ".py")
                            if candidate.exists():
                                rel = str(candidate.relative_to(workspace))
                                if rel not in seen:
                                    seen.add(rel)
                                    impl_files.append(rel)
                            init = base / sub / "__init__.py"
                            if init.exists():
                                rel = str(init.relative_to(workspace))
                                if rel not in seen:
                                    seen.add(rel)
                                    impl_files.append(rel)
            
            if not impl_files:
                return ""
            
            # Read implementation files
            content_parts = ["=== IMPLEMENTATION CODE (your tests must match this API) ==="]
            total = 0
            for impl_file in impl_files[:5]:  # cap at 5 files
                fpath = workspace / impl_file
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                    if total + len(text) > limit:
                        text = text[:limit - total] + "\n# ...(truncated)..."
                    content_parts.append(f"\n--- {impl_file} ---\n{text}")
                    total += len(text)
                except Exception:
                    pass
            
            return "\n".join(content_parts) if len(content_parts) > 1 else ""
        except Exception as e:
            self.log.warning("Could not load implementation for test %s: %s", test_path, e)
            return ""

    def _is_single_file_workspace(self) -> bool:
        return len(FileSystemHelper.find_source_files(self.config.workspace)) <= 1

    def find_impacted_tests(self, modified_paths: List[str]) -> List[str]:
        return find_impacted_tests(modified_paths, self.tools._symbol_index())
