"""CoderAgent: tactical execution agent for file edits.

All handler logic has been extracted into dedicated modules.  This module is
responsible only for the execution loop orchestration and state management.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..tools.parser import ToolCall
from ..tools.registry import ToolResult
from .config import AgentConfig, AgentStoppedError, CoderRunState
from .execution_context import ExecutionContext
from .tool_security import ToolSecurity

# Backward-compatible re-exports
from .config import AgentConfig as AgentConfig  # noqa: F811
from .execution_context import ExecutionContext as ExecutionContext  # noqa: F811
from .tool_security import ToolSecurity as ToolSecurity  # noqa: F811

from rich.console import Console

console = Console()


class CoderAgent:
    """Agent responsible for tactical execution: making exact file edits based on a plan."""

    def __init__(self, orchestrator):
        self.orch = orchestrator
        self._security = ToolSecurity(orchestrator.workspace, orchestrator.policy)
        self._file_locks: Dict[Path, asyncio.Lock] = {}
        self._execution_context = ExecutionContext()
        self._state = CoderRunState.IDLE
        self._multi_pass_done = False

    # ==================== Main entry point ====================

    async def execute(self) -> None:
        try:
            self._state = CoderRunState.PROCESSING
            self._execution_context.reset_for_subtask()
            if self.orch.config.milestones:
                await self._execute_with_milestones()
            elif self.orch.config.planner_editor:
                await self._execute_with_planner_editor()
            else:
                await self._execute_legacy()
            self._state = CoderRunState.COMPLETED
        except AgentStoppedError:
            self.orch.log.info("Agent execution stopped via state exception.")
        except Exception as e:
            self.orch.log.error("Execution failed: %s", str(e), exc_info=True)
            self._state = CoderRunState.ERROR
            raise
        finally:
            await self._cleanup()

    # ==================== Execution modes ====================

    async def _execute_with_planner_editor(self) -> None:
        from .message_builder import compact_subtask_history
        from .finish_handler import handle_finish_tool
        from .tool_executor import (
            execute_tool_safely, parse_tool_calls, handle_no_tool_call,
            get_filtered_tools, get_excluded_tools, get_repo_map, read_file_safe,
        )
        from .validators import get_syntax_errors, check_thrash_detection

        checklist = self.orch.frame.metadata.get("checklist") or []
        if not checklist:
            self.orch.log.warning("No checklist found for planner_editor execution")
            await self._transition_to_done()
            return

        reflexion_lesson = self.orch.frame.reflections[-1] if self.orch.frame.reflections else ""

        for idx, item in enumerate(checklist):
            await self._check_stop_or_pause()

            path = item.get("path")
            change_description = item.get("change_description")
            is_new = item.get("is_new", False)

            self.orch.log.info(
                "Processing task %d/%d: %s (is_new=%s)",
                idx + 1, len(checklist), path, is_new,
            )
            self.orch.emit("tool_call", step=idx + 1, tool=f"editor:{path}", args={"change": change_description})

            original_content = await read_file_safe(path, is_new, self.orch.workspace)
            self._execution_context.reset_for_subtask()
            exclude_names = get_excluded_tools(self.orch, is_new)

            success = await self._execute_subtask(
                path=path,
                change_description=change_description,
                original_content=original_content,
                reflexion_lesson=reflexion_lesson,
                exclude_names=exclude_names,
                is_new=is_new,
            )

            self.orch.log.info("Finished task %d/%d for %s: success=%s", idx + 1, len(checklist), path, success)
            self.orch.emit("tool_result", step=idx + 1, tool=f"editor:{path}", ok=success, content=f"Subtask completed for {path}")

        await self._transition_to_done()

    async def _execute_legacy(self) -> None:
        from .tool_executor import get_filtered_tools
        from .legacy_executor import execute_legacy_step
        from .validators import check_redundant_repeats

        tools = get_filtered_tools(self.orch)
        seen = {}

        for step in range(1, self.orch.config.max_steps + 1):
            await self._check_stop_or_pause()

            success = await execute_legacy_step(
                step, tools, seen, self.orch, self._security,
                self._execution_context, self._file_locks,
            )
            if success:
                break

            if self._execution_context.redundant_repeats >= AgentConfig.MAX_REDUNDANT_REPEATS:
                await self._handle_no_progress(step)
                break

        await self._transition_to_done()

    async def _execute_with_milestones(self) -> None:
        milestones = self.orch.frame.metadata.get("milestones") or []
        if not milestones:
            self.orch.log.warning("No milestones found; falling back to flat checklist execution")
            await self._execute_with_planner_editor()
            return

        await self._run_milestone_loop()
        # Multi-pass: run cross-file / semantic / false-pass checks (at most once)
        if not self._multi_pass_done:
            self._multi_pass_done = True
            multi_pass_issues = await self._run_cross_file_pass()
            if multi_pass_issues:
                self.orch.log.info(
                    "Multi-pass: %d issue(s) found — running fix pass",
                    len(multi_pass_issues),
                )
                self.orch.frame.reflections = list(self.orch.frame.reflections or [])
                self.orch.frame.reflections.append(multi_pass_issues)
                await self._run_milestone_loop()

        await self._transition_to_done()

    async def _run_milestone_loop(self) -> None:
        """Run the milestone loop once (may be called twice: initial + fix pass)."""
        milestones = self.orch.frame.metadata.get("milestones") or []
        base_lesson = self.orch.frame.reflections[-1] if self.orch.frame.reflections else ""
        for m_idx, milestone in enumerate(milestones):
            await self._check_stop_or_pause()
            name = milestone.get("name", f"milestone {m_idx + 1}")
            files = milestone.get("files", [])
            tests = milestone.get("tests", [])
            self.orch.log.info(
                "Milestone %d/%d: %s (%d file(s), %d test target(s))",
                m_idx + 1, len(milestones), name, len(files), len(tests),
            )
            self.orch.emit("milestone_start", index=m_idx + 1, total=len(milestones), name=name)

            files_exist = bool(files) and all(
                (self.orch.workspace / f.get("path", "")).exists()
                for f in files if f.get("path")
            )
            if files_exist:
                pre_ok, pre_summary, _, _ = await self._verify_scope(tests)
                if pre_ok:
                    self.orch.log.info("Milestone %d/%d '%s' already satisfied (%s) — skipping",
                                       m_idx + 1, len(milestones), name, pre_summary)
                    self.orch.emit("milestone_skip", index=m_idx + 1, name=name)
                    continue

            ok, summary = True, "no scoped tests"
            for attempt in range(1, AgentConfig.MAX_MILESTONE_RETRIES + 1):
                lesson = base_lesson if attempt == 1 else (
                    f"The '{name}' milestone still fails its tests: {summary}. "
                    f"Fix the files in this milestone so those tests pass."
                )
                for item in files:
                    await self._check_stop_or_pause()
                    await self._build_file(item, lesson, max_steps=AgentConfig.MILESTONE_SUBTASK_STEPS)
                # AC-11: Coverage gates — verify all milestone files were created
                missing_files = [
                    f.get("path", "") for f in files
                    if f.get("path") and not (self.orch.workspace / f.get("path", "")).exists()
                ]
                ok, summary, _, collection_error = await self._verify_scope(tests)
                if missing_files:
                    missing_msg = ", ".join(missing_files)
                    self.orch.log.warning(
                        "AC-11: Milestone '%s' coverage gate — files not created: %s",
                        name, missing_msg,
                    )
                    summary = f"Missing files: {missing_msg}. " + (summary or "Files not created.")
                    ok = False
                self.orch.log.info("Milestone '%s' verify (attempt %d): ok=%s (%s)",
                                   name, attempt, ok, summary.splitlines()[0])
                if ok:
                    break
                if collection_error:
                    self.orch.log.info(
                        "Milestone '%s': collection error is not layer-local; "
                        "deferring to reflexion instead of retrying this layer.", name)
                    break

            self.orch.emit("milestone_done", index=m_idx + 1, name=name, ok=ok, summary=summary)

    async def _run_cross_file_pass(self) -> str:
        from .cross_file_checker import run_cross_file_check, format_issues_as_lesson
        from .semantic_diff import run_semantic_diff, format_semantic_issues
        from .false_pass_detector import run_false_pass_detection
        issues: List[str] = []
        issues.extend(run_cross_file_check(self.orch.workspace))
        issues.extend(run_false_pass_detection(self.orch.workspace))
        task = getattr(self.orch.frame, "task_description", "") or ""
        if task:
            issues.extend(run_semantic_diff(task, self.orch.workspace))
        if issues:
            for issue in issues:
                self.orch.log.warning("Multi-pass: %s", issue)
            return format_issues_as_lesson(issues)
        self.orch.log.info("Multi-pass: no cross-file or semantic issues found")
        return ""

    # ==================== Subtask loop ====================

    async def _execute_subtask(
        self,
        path: str,
        change_description: str,
        original_content: str,
        reflexion_lesson: str,
        exclude_names: Set[str],
        is_new: bool,
        max_steps: Optional[int] = None,
    ) -> bool:
        from .message_builder import build_subtask_messages, compact_subtask_history
        from .tool_executor import (
            execute_tool_safely, parse_tool_calls, handle_no_tool_call,
            get_filtered_tools, get_repo_map, read_file_safe,
        )
        from .finish_handler import handle_finish_tool
        from .validators import get_syntax_errors, check_thrash_detection

        target_path = self.orch.workspace / path
        repo_map = await get_repo_map(self.orch)

        subtask_messages = build_subtask_messages(
            path=path,
            change_description=change_description,
            content=original_content,
            repo_map=repo_map,
            reflexion_lesson=reflexion_lesson,
            exclude_names=exclude_names,
            orch=self.orch,
        )

        offered_tools = get_filtered_tools(self.orch, exclude_names)
        edit_counts = {}

        step_budget = max_steps or AgentConfig.MAX_SUBTASK_STEPS
        for subtask_step in range(1, step_budget + 1):
            await self._check_stop_or_pause()

            ctx = self.orch.context
            subtask_messages = compact_subtask_history(subtask_messages, ctx)

            response = await self.orch._model_turn(
                subtask_messages, offered_tools, label=f"Editing {path} (subtask step {subtask_step})...",
            )
            subtask_messages.append({"role": "assistant", "content": response.content or ""})

            calls = await parse_tool_calls(self.orch, response, path)
            if not calls:
                await handle_no_tool_call(subtask_messages, response.content or "", self.orch)
                continue

            call = calls[0]

            if call.name == "finish":
                if await handle_finish_tool(path, target_path, subtask_messages, self.orch,
                                            lambda p, n: read_file_safe(p, n, self.orch.workspace)):
                    return True
                continue

            result = await execute_tool_safely(
                call, path, self.orch, self._security, self._execution_context, self._file_locks,
            )

            subtask_messages.append({
                "role": "user",
                "content": f"Tool '{call.name}' result: {result.content}",
            })

            if await check_thrash_detection(call, path, edit_counts, subtask_messages):
                continue

            has_errors = False
            if path.endswith(".py") and target_path.exists():
                errors = await get_syntax_errors(path, lambda p, n: read_file_safe(p, n, self.orch.workspace))
                if errors:
                    has_errors = True
                    subtask_messages.append({
                        "role": "user",
                        "content": (
                            f"Warning: The current file '{path}' has compilation/syntax errors:\n"
                            + "; ".join(errors) + "\nPlease fix the syntax errors."
                        ),
                    })

            if result.ok and not has_errors and call.name in AgentConfig.MUTATING_TOOLS:
                return True

        return False

    # ==================== Milestone helpers ====================

    async def _build_file(self, item: Dict[str, Any], lesson: str,
                          max_steps: Optional[int] = None) -> None:
        from .tool_executor import get_excluded_tools, read_file_safe

        path = item.get("path")
        if not path:
            return
        is_new = bool(item.get("is_new", False)) and not (self.orch.workspace / path).exists()
        original_content = await read_file_safe(path, is_new, self.orch.workspace)
        self._execution_context.reset_for_subtask()
        exclude_names = get_excluded_tools(self.orch, is_new)
        await self._execute_subtask(
            path=path,
            change_description=item.get("change_description", ""),
            original_content=original_content,
            reflexion_lesson=lesson,
            exclude_names=exclude_names,
            is_new=is_new,
            max_steps=max_steps,
        )

    async def _verify_scope(self, test_paths: List[str]) -> Tuple[bool, str, List[str], bool]:
        import shlex
        from ..evaluation.evaluator import (
            _parse_pytest_tally, _is_collection_error, _condense_test_output,
        )
        tests = [t for t in (test_paths or [])
                 if isinstance(t, str) and (self.orch.workspace / t).exists()]
        if not tests:
            return True, "no scoped tests to run", [], False
        cmd = "PYTHONPATH=. python -m pytest -q " + " ".join(shlex.quote(t) for t in tests)
        try:
            result = await self.orch.sandbox.aexec(cmd)
        except Exception as exc:
            self.orch.log.warning("Scoped verify failed to run: %s", exc)
            return False, f"could not run scoped tests: {exc}", [], False
        output = self.orch.policy.scrub(result.output)
        passed, failed, skipped, failing = _parse_pytest_tally(output)
        ok = bool(getattr(result, "ok", False) and failed == 0)
        collection_error = (not ok) and (
            _is_collection_error(output) or (passed == 0 and failed == 0)
        )
        if collection_error:
            detail = _condense_test_output(output, limit=1200).strip()
            summary = f"tests could not be collected (import/collection error):\n{detail}"
        else:
            summary = f"{passed} passed, {failed} failed, {skipped} skipped"
        return ok, summary, failing, collection_error

    # ==================== State management ====================

    async def _check_stop_or_pause(self) -> None:
        if self._state == CoderRunState.STOPPED or self.orch._stopped:
            raise AgentStoppedError()
        if self._state == CoderRunState.PAUSED:
            self.orch.log.info("Run paused by user request. Waiting for resume...")
            self.orch.emit("run_paused")
            await self.orch._paused_event.wait()
            self.orch.log.info("Run resumed by user request.")
            self.orch.emit("run_resumed")

    async def _transition_to_done(self) -> None:
        self.orch.fsm.transition("execution_done")

    async def _handle_no_progress(self, step: int) -> None:
        console.print("[yellow]Repeated actions without progress; moving to evaluation.[/yellow]")
        self.orch.log.warning("No-progress loop detected at step %d; aborting phase", step)
        self.orch._audit("no_progress_abort", step=step, redundant=self._execution_context.redundant_repeats)
        self.orch.emit("no_progress", step=step, redundant=self._execution_context.redundant_repeats)
        self.orch._no_progress_abort = True

    async def _on_paused(self) -> None:
        self.orch.emit("run_paused")

    async def _on_stopped(self) -> None:
        self.orch.emit("run_stopped")

    async def _cleanup(self) -> None:
        self._file_locks.clear()

    # ==================== Backward-compatible wrappers ====================
    # Tests and other code access these as instance methods.

    def _required_exports(self, path: str):
        from .message_builder import required_exports
        return required_exports(path, self.orch.workspace)

    def _relevant_references(self, path: str, change_description: str, **kw):
        from .message_builder import relevant_references
        return relevant_references(path, change_description, self.orch.customizations, **kw)

    def _compact_subtask_history(self, messages):
        from .message_builder import compact_subtask_history
        return compact_subtask_history(messages, self.orch.context)

    async def _get_syntax_errors(self, path: str):
        from .validators import get_syntax_errors
        from .tool_executor import read_file_safe
        return await get_syntax_errors(path, lambda p, n: read_file_safe(p, n, self.orch.workspace))
