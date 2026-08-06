import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Tuple
from pathlib import Path

from ..evaluation.evaluator import EvalResult

from rich.console import Console
from rich.panel import Panel
from rich.markup import escape

from .. import prompts
from ..fsm import AgentState

logger = logging.getLogger(__name__)
console = Console()



@dataclass
class EvaluationContext:
    """Context for evaluation and reflexion."""
    last_error_summary: str = ""
    escalated: bool = False
    evaluation_history: List[Dict[str, Any]] = field(default_factory=list)
    reflexion_history: List[str] = field(default_factory=list)
    
    def add_evaluation(self, passed: bool, summary: str, details: str = ""):
        self.evaluation_history.append({
            "timestamp": asyncio.get_running_loop().time(),
            "passed": passed,
            "summary": summary,
            "details": details
        })
        if not passed:
            self.last_error_summary = summary
    
    def add_reflexion(self, lesson: str):
        self.reflexion_history.append(lesson)



class EvaluatorValidator:
    """Validates evaluation results and applies business rules."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    def validate(self, result: EvalResult) -> EvalResult:
        """Apply validation rules to an evaluation result."""
        # Rule 1: Check for missing requested files
        if result.passed:
            missing = self.orch._missing_requested_files()
            if missing:
                return replace(
                    result,
                    passed=False,
                    summary=(
                        "Tests pass, but the task asked for files that do not exist: "
                        + ", ".join(missing)
                        + ". Create exactly these files. Do not modify the code that "
                        "is already passing. Use `run_command` with heredocs to create "
                        "all missing files in one step — `run_command` is not limited "
                        "by the write_file mutation budget."
                    ),
                )
        
        # Rule 2: Check for no-progress abort with zero mutations
        if result.passed and self.orch._no_progress_abort and self.orch._mutations == 0:
            return replace(
                result,
                passed=False,
                summary=(
                    "Tests pass, but the agent stopped making progress without editing "
                    "any file — the suite was already green before the task began, so "
                    "it proves nothing here. Treating this as failure, not success."
                ),
            )
        
        return result


class ReflexionCoordinator:
    """Handles reflexion logic and lesson generation."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    async def generate_lesson(
        self, 
        task_description: str, 
        eval_result: EvalResult,
        retry_count: int = 0,
    ) -> str:
        """Generate a reflexion lesson from the evaluation result."""
        if not eval_result:
            return ""
        
        try:
            lesson = await self.orch.reflexion.reflect(task_description, eval_result, retry_count)
            self.orch.log.info("Reflexion generated: %s", lesson[:200])
            return lesson
        except Exception as e:
            self.orch.log.error("Reflexion generation failed: %s", str(e))
            return f"Reflexion generation failed: {str(e)}. Please review the changes manually."


class ChecklistRefiner:
    """Refines checklists based on evaluation feedback."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    async def refine(
        self, 
        checklist: List[Dict[str, Any]], 
        eval_result: EvalResult,
        lesson: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Refine the checklist based on evaluation feedback."""
        if not checklist:
            self.orch.log.warning("No checklist to refine")
            return None
        
        try:
            # Determine impacted tests
            modified_paths = [item.get("path") for item in checklist if item.get("path")]
            impacted_tests = self.orch.find_impacted_tests(modified_paths)
            
            # Build refinement messages
            refiner_msgs = self._build_refinement_messages(
                checklist=checklist,
                eval_result=eval_result,
                lesson=lesson,
                impacted_tests=impacted_tests
            )
            
            # Get refined checklist from model
            response = await self.orch._model_turn(
                refiner_msgs, 
                label="Refining Checklist..."
            )
            
            raw_items = self._parse_refined_checklist(response.content)

            if raw_items:
                # Validate/normalize each refined item through the SAME strict
                # validation the planner uses. The model can emit an item with a
                # null or empty path; before this, such an item reached the coder
                # and crashed it (`workspace / None` -> TypeError), aborting the
                # whole run. Drop invalid items here instead of trusting the model.
                from .planner import ChecklistItem

                validated: List[Dict[str, Any]] = []
                seen_paths: set = set()
                for task in raw_items:
                    item = ChecklistItem.from_dict(task, self.orch.workspace)
                    if item is None:
                        self.orch.log.warning("Dropping invalid refined checklist item: %s", task)
                        continue
                    # De-duplicate by path: the model often lists the same file two or
                    # three times in one refined checklist, which made the coder edit it
                    # repeatedly in a single retry cycle (wasted steps, more thrash).
                    # Keep the first mention of each path only.
                    if item.path in seen_paths:
                        self.orch.log.info("Dropping duplicate refined task for %s", item.path)
                        continue
                    seen_paths.add(item.path)
                    # An existing file is an edit, not a creation.
                    if (self.orch.workspace / item.path).exists():
                        item.is_new = False
                    validated.append(item.to_dict())

                if validated:
                    self.orch.log.info("Refined checklist created with %d tasks", len(validated))
                    return validated
                self.orch.log.warning("Refined checklist had no valid items after validation")

            return None
            
        except Exception as e:
            self.orch.log.warning("Failed to refine checklist: %s. Re-running original checklist.", e)
            return None
    
    def _build_refinement_messages(
        self,
        checklist: List[Dict[str, Any]],
        eval_result: EvalResult,
        lesson: str,
        impacted_tests: List[str]
    ) -> List[Dict[str, str]]:
        """Build messages for checklist refinement."""
        return prompts.planner_refiner_messages(
            task=self.orch.frame.task_description,
            checklist=checklist,
            eval_result=str(eval_result),
            lesson=lesson,
            impacted_tests=impacted_tests
        )
    
    def _parse_refined_checklist(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """Parse refined checklist from model response."""
        refined_text = content.strip()
        
        # Extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", refined_text, re.DOTALL)
        if json_match:
            refined_text = json_match.group(1).strip()
        elif refined_text.startswith("```") and refined_text.endswith("```"):
            refined_text = refined_text.strip("`").strip()
        
        try:
            parsed = json.loads(refined_text)
            if isinstance(parsed, list):
                return parsed
            return None
        except json.JSONDecodeError as e:
            self.orch.log.warning("Failed to parse refined checklist JSON: %s", str(e))
            return None
    


class EscalationHandler:
    """Handles human escalation for complex issues."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    async def escalate(self, error_summary: str, details: str) -> Optional[str]:
        """Escalate to human and get a hint."""
        if self.orch._escalation_callback is None:
            return None
        
        if self.orch.frame.metadata.get("escalated"):
            return None
        
        self.orch.frame.metadata["escalated"] = True
        
        console.print("[yellow]Escalating to a human for a hint...[/yellow]")
        self.orch.log.info("Escalating to human after %d retries", self.orch.frame.retry_count)
        self.orch._audit("escalation_requested", summary=error_summary)
        
        try:
            hint = await self.orch._escalation_callback(
                f"{error_summary}\n\n{details}".strip()
            )
            if hint:
                hint = hint.strip()
                self.orch.log.info("Received escalation hint: %s", hint[:200])
                return hint
        except Exception as exc:
            self.orch.log.warning("Escalation failed: %s", exc)
        
        return None
    
    async def apply_hint(self, hint: str) -> bool:
        """Apply an escalation hint and update the context."""
        if not hint:
            return False
        
        # Add hint to reflexions
        self.orch.frame.add_reflection(f"Human hint: {hint}")
        
        # Add hint to messages
        self.orch.frame.messages.append({
            "role": "user",
            "content": (
                f"A human operator reviewed the failures and provided this hint: "
                f"{hint}\nUse it to fix the code, then call finish."
            ),
        })
        
        # Increase retry budget by a reasonable fixed amount
        self.orch.frame.max_retries += 2
        
        # Store in memory
        self.orch.memory.add(hint, kind="lesson", task=self.orch.frame.task_description)
        self.orch._audit("escalation_hint", hint=hint[:500])
        self.orch.emit("escalation_resolved", hint=hint)
        
        return True


class ReviewerAgent:
    """
    Agent responsible for verification, evaluation, and self-healing (reflexion).
    Refactored version with improved separation of concerns.
    """
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
        self._context = EvaluationContext()
        
        # Initialize components
        self._validator = EvaluatorValidator(orchestrator)
        self._reflexion_engine = ReflexionCoordinator(orchestrator)
        self._checklist_refiner = ChecklistRefiner(orchestrator)
        self._escalation_handler = EscalationHandler(orchestrator)
    
    async def execute_evaluation(self) -> None:
        """
        EVALUATING state: run the tests/checks and transition to DONE or REFLEXING.
        """
        self.orch.log.info("Starting evaluation")
        
        # Run evaluation
        result = await self._run_evaluation()
        
        # Validate result with business rules
        result = self._validator.validate(result)
        
        # Display results
        self._display_evaluation(result)
        
        # Log and audit
        self._log_evaluation(result)
        self.orch.emit("evaluation", passed=result.passed, summary=result.summary)
        
        # Store in context
        self._context.add_evaluation(result.passed, result.summary, result.details)
        
        # Transition based on result
        if result.passed:
            self.orch.fsm.transition("passed")
        else:
            self.orch.frame.last_error_summary = result.summary
            self.orch.frame.metadata["last_eval"] = result
            self.orch.fsm.transition("failed")
    
    async def execute_reflexion(self) -> None:
        """
        REFLEXING state: diagnose the failure, record a lesson, and retry or give up.
        """
        self.orch.log.info("Starting reflexion (retry %d/%d)", 
                          self.orch.frame.retry_count, self.orch.frame.max_retries)
        
        # Check if retry budget is exhausted
        if self.orch.frame.retry_count >= self.orch.frame.max_retries:
            await self._handle_exhausted_budget()
            return

        eval_result = self.orch.frame.metadata.get("last_eval")

        # No-progress early stop. If the EXACT same tests keep failing on consecutive
        # retries, more attempts won't help — stop now (honestly) instead of burning
        # the whole budget on an unchanging failure. (Measured: a stuck run ground
        # through all 8 retries on an identical failing set for 68 minutes.)
        if self._is_stalled(eval_result):
            self.orch.log.info(
                "No-progress stop at retry %d/%d — the failing-test count stopped "
                "improving, or the suite could not collect a single test across "
                "consecutive build+eval cycles. Stopping early instead of burning the "
                "remaining budget.",
                self.orch.frame.retry_count, self.orch.frame.max_retries,
            )
            self.orch._audit(
                "no_progress_stop",
                retry=self.orch.frame.retry_count,
                failing=list(self.orch.frame.metadata.get("_last_fail_sig") or ()),
            )
            self.orch.emit("no_progress_stop", retry=self.orch.frame.retry_count)
            await self._handle_exhausted_budget()
            return

        # Increment retry counter
        self.orch.frame.retry_count += 1

        # Generate reflexion lesson
        lesson = await self._reflexion_engine.generate_lesson(
            self.orch.frame.task_description,
            eval_result,
            retry_count=self.orch.frame.retry_count,
        )
        
        # Store lesson
        if lesson:
            self._context.add_reflexion(lesson)
            self.orch.frame.add_reflection(lesson)
            self.orch._audit("reflexion", retry=self.orch.frame.retry_count, lesson=lesson[:500])
            self.orch.emit("reflexion", retry=self.orch.frame.retry_count, lesson=lesson)
        
        # Refine checklist if using planner_editor
        if self.orch.config.planner_editor and eval_result:
            await self._refine_checklist(eval_result, lesson)
        
        # Prepare for retry
        self.orch.frame.messages.append(
            {"role": "user", "content": f"The change failed evaluation. {lesson} Fix it and call finish."}
        )
        
        self.orch.fsm.transition("retry")
    
    # ==================== Private Methods ====================
    
    async def _run_evaluation(self) -> EvalResult:
        """Run the actual evaluation."""
        try:
            # Run tests/compile off the event loop
            result = await asyncio.to_thread(
                self.orch.evaluator.evaluate,
                self.orch.workspace
            )
            return result
        except Exception as e:
            self.orch.log.error("Evaluation execution failed: %s", str(e), exc_info=True)
            return EvalResult(
                passed=False,
                summary=f"Evaluation execution failed: {str(e)}",
                details=str(e)
            )
    
    def _display_evaluation(self, result: EvalResult) -> None:
        """Display evaluation results."""
        style = "green" if result.passed else "red"
        console.print(
            Panel(
                escape(result.summary), 
                title="Evaluation", 
                border_style=style
            )
        )
    
    def _log_evaluation(self, result: EvalResult) -> None:
        """Log evaluation results."""
        self.orch.log.info(
            "Evaluation passed=%s: %s", 
            result.passed, 
            result.summary
        )
        self.orch._audit(
            "evaluation",
            passed=result.passed,
            summary=result.summary,
            ran_tests=result.ran_tests,
            # Structured tally so the audit trail shows convergence across retries,
            # not just a repeated passed=False. (getattr keeps this robust if a
            # result type without the fields ever flows through.)
            tests_passed=getattr(result, "tests_passed", 0),
            tests_failed=getattr(result, "tests_failed", 0),
            tests_skipped=getattr(result, "tests_skipped", 0),
            failing=getattr(result, "failing_tests", [])[:20],
        )
    
    async def _handle_exhausted_budget(self) -> None:
        """Handle case when retry budget is exhausted."""
        # Try escalation first
        hint = await self._escalation_handler.escalate(
            self._context.last_error_summary,
            getattr(self.orch.frame.metadata.get("last_eval"), "details", "")[:2000]
        )
        
        if hint:
            # Apply hint and continue
            await self._escalation_handler.apply_hint(hint)
            # Reset retry counter since we have new information
            self.orch.frame.retry_count = 0
            self.orch.fsm.transition("retry")
            return
        
        # No hint available, give up
        self._give_up()
    
    # Consecutive evaluations without a *drop* in the failing-test count tolerated
    # before we stop retrying. One genuine retry is allowed; if the number of
    # failing tests then fails to improve on two more evaluations, the loop is stuck
    # and further retries only waste time/tokens.
    NO_PROGRESS_STOP = 2

    # Consecutive evaluations where the suite cannot collect a SINGLE test (0 passed,
    # 0 failed — a broken import graph) tolerated before giving up. A hair more lenient
    # than NO_PROGRESS_STOP because a weak model often fixes import errors one at a time
    # (whack-a-mole); but if after this many full build+eval cycles not one test can even
    # run, the build is fundamentally broken and 8 retries won't save it. (specs05 burned
    # all 8 retries at 0/0/0 because the count-based stop has no signal to key on here.)
    COLLECTION_STALL_STOP = 3

    # Maximum times the EXACT same error summary can repeat before we stop. When the
    # model flip-flops between two approaches (e.g., "from X import Y" vs
    # "from X.Z import Y"), the summary stays identical across retries. Three repeats
    # of the same error is a strong signal the model is stuck in a loop.
    REPEATED_ERROR_STOP = 3

    def _is_stalled(self, eval_result) -> bool:
        """True once the failing-test COUNT stops improving over consecutive evaluations.

        Keyed on the count of failing tests (reconciled with the FAILED ids), not on
        an exact set match. This was deliberately changed after a real run
        (markdown-converter) ground through all 8 retries with ~20 tests failing the
        whole time: exact-set matching reset on a 1-test churn (20 vs 21) and on the
        interleaved no-signal evaluations, so it never fired. Monotonic-progress
        detection tolerates set churn and small parser noise: the stall counter only
        resets on a genuine improvement (strictly fewer failing than the best seen).

        If there is no failing-test signal at all (non-pytest runner, or a failure
        the parser cannot count), returns False so we never stop on a blind guess.
        """
        failing = tuple(sorted(getattr(eval_result, "failing_tests", None) or ()))
        failed = max(int(getattr(eval_result, "tests_failed", 0) or 0), len(failing))
        passed_n = int(getattr(eval_result, "tests_passed", 0) or 0)
        meta = self.orch.frame.metadata

        # --- Repeated-error detection: same summary across retries → loop ---
        # Only applies when there are no countable failures (collection errors).
        # This catches the import-oscillation case where the model keeps flip-flopping
        # between import styles and the same collection error repeats.
        summary = getattr(eval_result, "summary", "") or ""
        if not isinstance(summary, str):
            summary = str(summary)
        # Normalize summary for comparison (strip variable parts like file paths)
        normalized = re.sub(r"[\w/.-]+\.py", "*.py", summary).strip()
        last_summary = meta.get("_last_error_summary")
        if normalized and normalized == last_summary and failed <= 0 and passed_n == 0:
            meta["_repeated_error_count"] = meta.get("_repeated_error_count", 0) + 1
            if meta["_repeated_error_count"] >= self.REPEATED_ERROR_STOP:
                logger.info(
                    "Repeated-error stop: same error summary %d times in a row",
                    meta["_repeated_error_count"],
                )
                return True
        elif failed > 0 or passed_n > 0:
            # Tests are running — reset repeated error tracking
            meta["_repeated_error_count"] = 0
        else:
            meta["_repeated_error_count"] = 1 if normalized else 0
        meta["_last_error_summary"] = normalized

        if failed <= 0:
            # No countable failing tests. In reflexion (a FAILED eval) that means either
            # the suite could not collect a single test — a broken import graph — or the
            # eval failed for a non-test reason (e.g. missing requested files). Only the
            # former is an unrecoverable stall: if nothing runs (0 passed AND 0 failed)
            # for several full build+eval cycles, the build is broken beyond retrying.
            if passed_n == 0:
                meta["_collect_stall"] = meta.get("_collect_stall", 0) + 1
                if meta["_collect_stall"] >= self.COLLECTION_STALL_STOP:
                    return True
            else:
                meta["_collect_stall"] = 0  # something collected & ran — not this stall
            return False
        meta["_collect_stall"] = 0  # tests are running again — clear the collection stall
        best = meta.get("_best_failed")
        if best is None or failed < best:
            # Genuine progress (or first signal): fewer tests failing than ever before.
            meta["_best_failed"] = failed
            meta["_stall_count"] = 0
            meta["_last_fail_sig"] = failing
            return False
        # No improvement (same or more failing than the best seen) — count it.
        meta["_stall_count"] = meta.get("_stall_count", 0) + 1
        meta["_last_fail_sig"] = failing
        return meta["_stall_count"] >= self.NO_PROGRESS_STOP

    def _give_up(self) -> None:
        """Give up and transition to give_up state."""
        console.print("[yellow]Retry budget exhausted.[/yellow]")
        self.orch.log.info("Retry budget exhausted after %d retries", self.orch.frame.retry_count)
        self.orch._audit("give_up", retries=self.orch.frame.retry_count)
        self.orch.emit(
            "give_up", 
            retries=self.orch.frame.retry_count,
            summary=self._context.last_error_summary or ""
        )
        self.orch.fsm.transition("give_up")
    
    async def _refine_checklist(
        self, 
        eval_result: EvalResult, 
        lesson: str
    ) -> None:
        """Refine the checklist based on evaluation feedback."""
        current_checklist = self.orch.frame.metadata.get("checklist") or []
        
        if not current_checklist:
            self.orch.log.warning("No checklist to refine")
            return
        
        refined_checklist = await self._checklist_refiner.refine(
            current_checklist,
            eval_result,
            lesson
        )
        
        if refined_checklist:
            self.orch.frame.metadata["checklist"] = refined_checklist
            self.orch.frame.plan = json.dumps(refined_checklist, indent=2)
            self.orch.log.info("Refined checklist created with %d tasks", len(refined_checklist))
            self.orch.emit("plan", text=self.orch.frame.plan)
    
    # ==================== Public Utility Methods ====================
    
    def get_evaluation_context(self) -> EvaluationContext:
        """Get the current evaluation context."""
        return self._context
    
    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = EvaluationContext()
        self.orch.frame.metadata["escalated"] = False
    
    async def quick_evaluate(self) -> Tuple[bool, str]:
        """Quick evaluation without state transitions."""
        result = await self._run_evaluation()
        result = self._validator.validate(result)
        return result.passed, result.summary
