import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple, Union

from rich.console import Console
from rich.panel import Panel
from rich.markup import escape

from .. import prompts
from ..fsm import AgentState

console = Console()



@dataclass
class PlanContext:
    """Context for planning operations."""
    task_description: str
    repository_skeleton: str
    memory_text: str
    customizations: List[str]
    exclude_names: Set[str]
    workspace_root: Path
    
    @classmethod
    def from_orchestrator(cls, orchestrator) -> "PlanContext":
        """Create a PlanContext from an orchestrator instance."""
        return cls(
            task_description=orchestrator.frame.task_description,
            repository_skeleton="",  # Will be filled later
            memory_text="",
            customizations=[],
            exclude_names=set(),
            workspace_root=orchestrator.workspace
        )


@dataclass
class ChecklistItem:
    """A single item in the planning checklist."""
    path: str
    change_description: str
    is_new: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], workspace_root: Path) -> Optional["ChecklistItem"]:
        """Create a ChecklistItem from a dictionary with validation."""
        if not isinstance(data, dict):
            return None
        
        path = data.get("path")
        change_description = data.get("change_description")
        
        if not path or not change_description:
            return None
        
        # Validate and resolve path
        resolved_path = cls._resolve_path_safe(path, workspace_root)
        if resolved_path is None:
            return None
        
        return cls(
            path=resolved_path,
            change_description=change_description,
            is_new=data.get("is_new", False),
            metadata={k: v for k, v in data.items() if k not in ("path", "change_description", "is_new")}
        )
    
    @staticmethod
    def _resolve_path_safe(path: str, workspace_root: Path) -> Optional[str]:
        """Resolve a path safely, preventing path traversal."""
        try:
            target_path = (workspace_root / path).resolve()
            workspace_root_resolved = workspace_root.resolve()
            
            # Check if path is inside workspace
            try:
                # Python 3.9+ compatible method
                if not str(target_path).startswith(str(workspace_root_resolved)):
                    return None
            except AttributeError:
                # Fallback for older Python versions
                try:
                    target_path.relative_to(workspace_root_resolved)
                except ValueError:
                    return None
            
            # Return relative path
            return str(target_path.relative_to(workspace_root_resolved))
        except (OSError, ValueError):
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "path": self.path,
            "change_description": self.change_description,
            "is_new": self.is_new,
        }
        result.update(self.metadata)
        return result


class PlanParser:
    """Handles parsing and validation of plans from model responses."""
    
    # Known wrapper keys for plan extraction
    WRAPPER_KEYS = {"tasks", "checklist", "plan", "steps", "items"}
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    async def parse_checklist(
        self, 
        content: str, 
        workspace_root: Path
    ) -> Tuple[Optional[List[ChecklistItem]], Optional[str]]:
        """
        Parse checklist from model response.
        
        Returns:
            Tuple of (checklist_items, error_message)
        """
        try:
            # Extract JSON from content
            json_text = self._extract_json(content)
            if not json_text:
                return None, "No JSON found in response"
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Unwrap common wrapper structures
            if isinstance(data, dict):
                for key in self.WRAPPER_KEYS:
                    if isinstance(data.get(key), list):
                        data = data[key]
                        break
            
            if not isinstance(data, list):
                return None, f"Expected JSON array, got {type(data).__name__}"
            
            # Convert to ChecklistItem objects
            items = []
            for item_data in data:
                item = ChecklistItem.from_dict(item_data, workspace_root)
                if item:
                    items.append(item)
                else:
                    self.orch.log.warning("Invalid checklist item: %s", item_data)
            
            if not items:
                return None, "No valid checklist items found"
            
            return items, None
            
        except json.JSONDecodeError as e:
            return None, f"JSON parsing error: {str(e)}"
        except Exception as e:
            self.orch.log.error("Unexpected error parsing checklist: %s", str(e), exc_info=True)
            return None, f"Unexpected error: {str(e)}"
    
    def _extract_json(self, content: str) -> Optional[str]:
        """Extract JSON from content, handling markdown code blocks."""
        content = content.strip()
        
        # Try to extract from markdown code blocks
        code_block_match = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*(.*?)\s*```", content, re.DOTALL)
        if code_block_match:
            return code_block_match.group(1).strip()
        
        # Try to find JSON-like content
        json_match = re.search(r'\{.*\}|\[.*\]', content, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return content if content.startswith(('{', '[')) else None
    
    def validate_checklist(self, checklist: List[ChecklistItem]) -> bool:
        """Validate a complete checklist."""
        if not checklist:
            return False
        
        # Check for required fields
        for item in checklist:
            if not item.path or not item.change_description:
                return False
        
        # Check for duplicate paths
        paths = [item.path for item in checklist]
        if len(paths) != len(set(paths)):
            self.orch.log.warning("Duplicate paths found in checklist")
            # Not a critical error, but worth noting
        
        return True


class PlanGenerator:
    """Generates plans using different strategies."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
        self._parser = PlanParser(orchestrator)
    
    async def generate_checklist(
        self,
        context: PlanContext
    ) -> Tuple[Optional[List[ChecklistItem]], Optional[str]]:
        """Generate a checklist plan."""
        # Build messages
        messages = prompts.planner_messages(
            context.task_description,
            context.repository_skeleton,
            context.memory_text,
            customizations=context.customizations
        )
        
        # Get response from model
        response = await self.orch._model_turn(messages, label="Planning Checklist...")
        
        # Parse checklist
        items, error = await self._parser.parse_checklist(
            response.content,
            context.workspace_root
        )
        
        if error:
            self.orch.log.warning("Checklist parsing failed: %s", error)
            return None, error
        
        # Validate
        if not self._parser.validate_checklist(items):
            return None, "Checklist validation failed"
        
        # Update is_new status for existing files
        for item in items:
            if item.path:
                target_file = context.workspace_root / item.path
                if target_file.exists():
                    item.is_new = False
        
        return items, None
    
    async def generate_text_plan(
        self,
        context: PlanContext
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate a text-based plan."""
        messages = prompts.planning_messages(
            context.task_description,
            context.repository_skeleton,
            context.memory_text,
            customizations=context.customizations
        )
        
        response = await self.orch._model_turn(messages, label="Planning...")
        
        if not response.content or len(response.content.strip()) < 10:
            return None, "Generated plan is too short or empty"
        
        return response.content.strip(), None




class FallbackPlanGenerator:
    """Generates fallback plans when the primary plan generation fails."""
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
    
    async def generate_fallback_checklist(self, task_description: str) -> List[ChecklistItem]:
        """Generate a simple fallback checklist."""
        fallback_file = self.orch._find_target_file() or "solution.py"
        fallback_path = self.orch.workspace / fallback_file
        
        # Check if file exists
        exists = await asyncio.to_thread(fallback_path.exists)
        
        item = ChecklistItem(
            path=fallback_file,
            change_description=f"Implement the requested task: {task_description}",
            is_new=not exists
        )
        
        return [item]


class PlannerAgent:
    """
    Agent responsible for high-level strategizing and breaking tasks into actionable checklists.
    Refactored version with improved separation of concerns.
    """
    
    def __init__(self, orchestrator):
        self.orch = orchestrator
        
        # Initialize components
        self._parser = PlanParser(orchestrator)
        self._generator = PlanGenerator(orchestrator)
        
        self._fallback_generator = FallbackPlanGenerator(orchestrator)
        
        # Configuration
        self._max_plan_length = 10000
        self._cache_customizations = True
    
    async def execute(self) -> None:
        """
        PLANNING state: scan the workspace and produce a plan or Planner checklist.
        """
        self.orch.log.info("Starting planning phase")
        
        try:
            # Load context
            context = await self._build_plan_context()
            
            # Generate plan
            if self.orch.config.milestones:
                await self._execute_milestone_planning(context)
            elif self.orch.config.planner_editor:
                await self._execute_checklist_planning(context)
            else:
                await self._execute_text_planning(context)
            
            # Prepare for execution
            await self._prepare_execution_context()
            
            # Transition to ready state
            self.orch.fsm.transition("plan_ready")
            
        except Exception as e:
            self.orch.log.error("Planning failed: %s", str(e), exc_info=True)
            await self._handle_planning_failure(e)
    
    # ==================== Private Methods ====================

    async def _execute_milestone_planning(self, context: PlanContext) -> None:
        """Milestone planning: ask for ordered, independently-verifiable layers."""
        self.orch.log.info("Generating milestone plan")
        messages = prompts.milestone_planner_messages(
            context.task_description,
            context.repository_skeleton,
            context.memory_text,
            customizations=context.customizations,
        )
        response = await self.orch._model_turn(messages, label="Planning milestones...")
        milestones = self._parse_milestones(response.content, context.workspace_root)
        # The model plans in source layers and routinely omits files the task named
        # outright (test files, setup.py, entrypoints). Guarantee they are build
        # targets before anything else runs.
        milestones = self._ensure_requested_files_planned(milestones, context.workspace_root)
        # The model rarely maps tests to layers itself, so attach them by name — this
        # is what makes each milestone actually self-verify (per-layer error catching).
        milestones = self._attach_tests_by_name(milestones)

        if not milestones:
            self.orch.log.warning("Milestone parse failed; falling back to a single milestone")
            fb = await self._fallback_generator.generate_fallback_checklist(context.task_description)
            milestones = [{"name": "implement", "files": [i.to_dict() for i in fb], "tests": []}]

        # Flatten to a checklist too, so missing-files / refinement machinery still works.
        flat = [f for m in milestones for f in m.get("files", [])]
        self.orch.frame.metadata["milestones"] = milestones
        self.orch.frame.metadata["checklist"] = flat
        self.orch.frame.plan = json.dumps(milestones, indent=2)
        self.orch.log.info("Milestone plan: %d milestone(s), %d file(s)", len(milestones), len(flat))
        self.orch._audit("plan_created", plan_type="milestones",
                         milestones=len(milestones), tasks_count=len(flat))
        self._display_plan(self.orch.frame.plan)

    def _ensure_requested_files_planned(
        self, milestones: List[Dict[str, Any]], workspace_root: Path
    ) -> List[Dict[str, Any]]:
        """Guarantee every explicitly-requested file is a build target.

        The milestone model plans in source layers and routinely drops files the task
        named outright — test files, setup.py, entrypoints. Those then never get built,
        the requested-files gate fails at evaluation, and (because their milestone does
        not exist) no retry can recover: the milestone executor only rebuilds layers it
        knows about. Appending a final milestone with any requested-but-unplanned file
        makes the deliverables the user asked for always get built, and — since the
        skip-satisfied retry check keys off file existence — makes recovery work too.
        """
        # At planning time nothing is built yet, so this is the full requested set.
        requested = self.orch._missing_requested_files()
        if not requested:
            return milestones
        planned = {f.get("path") for m in milestones for f in m.get("files", [])}
        # Tasks routinely list files as a tree/basename ("auth.py", "user.py"), which
        # the extractor cannot map back to their planned "src/routes/auth.py" home.
        # Treat a BARE requested filename as already covered when a planned file has
        # that basename — the same basename tolerance the eval-time gate uses. Without
        # this we would re-create the whole source tree as root-level duplicates.
        planned_basenames = {Path(p).name for p in planned if p}
        extra: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for rel in requested:
            if rel in planned:
                continue
            if "/" not in rel and Path(rel).name in planned_basenames:
                continue
            item = ChecklistItem.from_dict(
                {"path": rel,
                 "change_description": f"Create {rel} exactly as required by the task.",
                 "is_new": True},
                workspace_root,
            )
            if item and item.path not in planned and item.path not in seen:
                seen.add(item.path)
                extra.append(item.to_dict())
        if not extra:
            return milestones
        # If any of the missing deliverables are tests, make them this milestone's
        # scoped verification so the layer actually runs what it just wrote.
        tests = sorted(
            f["path"] for f in extra
            if Path(f["path"]).name.lower().startswith("test_")
            or Path(f["path"]).name.lower().endswith("_test.py")
        )
        milestones.append({"name": "required deliverables", "files": extra, "tests": tests})
        self.orch.log.info(
            "Added 'required deliverables' milestone with %d requested file(s): %s",
            len(extra), ", ".join(f["path"] for f in extra))
        return milestones

    @staticmethod
    def _test_stems(path: str) -> Set[str]:
        """Comparable name-stems for a path, e.g. 'src/models/user.py' -> {user, users}."""
        stem = Path(path).stem
        stem = stem[5:] if stem.startswith("test_") else stem   # drop test_ prefix
        parts = {stem} | set(stem.split("_"))
        return {p for p in parts | {p.rstrip("s") for p in parts} if p}

    def _attach_tests_by_name(self, milestones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Give each milestone the test files whose names relate to its source files.

        The milestone model rarely maps tests to layers, so per-layer verification
        was firing on almost nothing. This matches test files (by shared name-stems)
        to the layer they cover. `_verify_scope` only runs tests that exist at the
        time, so attaching a test created in a later layer is harmless.
        """
        all_tests = sorted({
            f["path"] for m in milestones for f in m["files"]
            if Path(f["path"]).name.lower().startswith("test_")
            or Path(f["path"]).name.lower().endswith("_test.py")
        })
        if not all_tests:
            return milestones
        for m in milestones:
            if m.get("tests"):
                continue
            src_stems: Set[str] = set()
            for f in m["files"]:
                if not Path(f["path"]).name.lower().startswith("test_"):
                    src_stems |= self._test_stems(f["path"])
            matched = [t for t in all_tests if self._test_stems(t) & src_stems]
            if matched:
                m["tests"] = matched
        return milestones

    def _parse_milestones(self, content: str, workspace_root: Path) -> List[Dict[str, Any]]:
        """Parse + validate the milestone JSON; each file goes through ChecklistItem.from_dict."""
        text = self._parser._extract_json(content)
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            for key in ("milestones", "plan", "steps", "tasks"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            return []
        out: List[Dict[str, Any]] = []
        for m in data:
            if not isinstance(m, dict):
                continue
            files: List[Dict[str, Any]] = []
            seen: Set[str] = set()
            for rf in (m.get("files") or []):
                item = ChecklistItem.from_dict(rf, workspace_root)
                if item and item.path not in seen:
                    seen.add(item.path)
                    files.append(item.to_dict())
            if not files:
                continue
            tests = [str(t) for t in (m.get("tests") or []) if isinstance(t, str) and t.strip()]
            name = str(m.get("name") or f"milestone {len(out) + 1}")
            out.append({"name": name, "files": files, "tests": tests})
        return out

    async def _build_plan_context(self) -> PlanContext:
        """Build the planning context."""
        # Load repository skeleton
        skeleton = await asyncio.to_thread(self.orch.indexer.get_repo_skeleton)
        
        # Load memory
        memory_text = self.orch.memory.format_for_prompt()
        if memory_text:
            self.orch.log.info("Loaded %d memory entrie(s) into context", self.orch.memory.count())
            self.orch.emit("memory_loaded", count=self.orch.memory.count())
        
        # Load customizations
        rules = await asyncio.to_thread(self.orch.customizations.load_rules)
        skills = await asyncio.to_thread(self.orch.customizations.load_skills, self.orch.frame.task_description)
        customizations = rules + skills
        
        # Determine excluded tools
        exclude_names = set()
        if self.orch._is_single_file_workspace():
            exclude_names.update({"rename_symbol", "add_parameter", "add_docstring"})
        
        return PlanContext(
            task_description=self.orch.frame.task_description,
            repository_skeleton=skeleton,
            memory_text=memory_text,
            customizations=customizations,
            exclude_names=exclude_names,
            workspace_root=self.orch.workspace
        )
    
    async def _execute_checklist_planning(self, context: PlanContext) -> None:
        """Execute checklist-based planning."""
        self.orch.log.info("Generating checklist plan")
        
        # Generate checklist
        checklist, error = await self._generator.generate_checklist(context)
        
        if error or not checklist:
            self.orch.log.warning("Checklist generation failed: %s. Using fallback.", error)
            checklist = await self._fallback_generator.generate_fallback_checklist(
                context.task_description
            )
            if not checklist:
                raise ValueError("Failed to generate checklist with fallback")
        
        # Store checklist
        checklist_dicts = [item.to_dict() for item in checklist]
        self.orch.frame.metadata["checklist"] = checklist_dicts
        self.orch.frame.plan = json.dumps(checklist_dicts, indent=2)
        
        self.orch.log.info("Planner checklist created with %d tasks", len(checklist))
        self.orch._audit("plan_created", plan_type="checklist", tasks_count=len(checklist))
        
        # Display plan
        self._display_plan(self.orch.frame.plan)
    
    async def _execute_text_planning(self, context: PlanContext) -> None:
        """Execute text-based planning."""
        self.orch.log.info("Generating text plan")
        
        # Generate text plan
        plan, error = await self._generator.generate_text_plan(context)
        
        if error or not plan:
            self.orch.log.warning("Text plan generation failed: %s", error)
            plan = f"Plan to implement: {context.task_description[:100]}..."
        
        # Store plan
        self.orch.frame.plan = plan
        self.orch.log.info("Plan created (%d chars)", len(self.orch.frame.plan))
        self.orch._audit("plan_created", plan_type="text", plan_chars=len(self.orch.frame.plan))
        
        # Display plan
        self._display_plan(self.orch.frame.plan)
    
    async def _prepare_execution_context(self) -> None:
        """Prepare the execution context for the agent."""
        # Build system prompt
        exclude_names = set()
        if self.orch._is_single_file_workspace():
            exclude_names.update({"rename_symbol", "add_parameter", "add_docstring"})
        
        system_content = prompts.system_prompt(exclude_names=exclude_names)
        
        # Add customizations
        rules = await asyncio.to_thread(self.orch.customizations.load_rules)
        skills = await asyncio.to_thread(self.orch.customizations.load_skills, self.orch.frame.task_description)
        customizations = rules + skills
        if customizations:
            system_content += "\n\nAdditional instructions and guidelines for this workspace/task:\n"
            system_content += "\n\n".join(customizations)
        
        # Build messages
        messages = [
            {"role": "system", "content": system_content},
            prompts.execution_primer(
                self.orch.frame.task_description,
                self.orch.frame.plan or ""
            ),
        ]
        
        # Add memory
        memory_text = self.orch.memory.format_for_prompt()
        if memory_text:
            messages.append({"role": "user", "content": memory_text})
        
        # Add reflections
        for lesson in self.orch.frame.reflections:
            messages.append({
                "role": "user",
                "content": f"Lesson from a previous attempt: {lesson}"
            })
        
        self.orch.frame.messages = messages
    
    def _display_plan(self, plan: str) -> None:
        """Display the plan to the user."""
        if not self.orch._stream:
            console.print(
                Panel(
                    escape(plan or "(no plan)"),
                    title="Plan",
                    border_style="cyan"
                )
            )
        
        self.orch.emit("plan", text=plan)
    
    async def _handle_planning_failure(self, error: Exception) -> None:
        """Handle planning failures gracefully."""
        self.orch.log.error("Planning failed: %s", str(error))
        self.orch._audit("planning_failed", error=str(error))
        self.orch.emit("planning_failed", error=str(error))
        
        # Create emergency fallback plan
        fallback_checklist = await self._fallback_generator.generate_fallback_checklist(
            self.orch.frame.task_description
        )
        
        if fallback_checklist:
            checklist_dicts = [item.to_dict() for item in fallback_checklist]
            self.orch.frame.metadata["checklist"] = checklist_dicts
            self.orch.frame.plan = json.dumps(checklist_dicts, indent=2)
            self.orch.log.info("Emergency fallback plan created with %d tasks", len(fallback_checklist))
            
            # Continue with execution
            await self._prepare_execution_context()
            self.orch.fsm.transition("plan_ready")
        else:
            # Critical failure - cannot recover. Re-raise the original error so
            # run_task's handler transitions to ERROR. ("planning_failed" was never
            # a valid FSM event: transitioning on it here raised InvalidTransition
            # and masked the real error; the bare `raise` was also unreachable.)
            raise error
    
    # ==================== Utility Methods ====================
    
    def reset(self) -> None:
        """Reset the planner for a new task."""
        pass
    
    async def regenerate_plan(self) -> bool:
        """Regenerate the plan based on current context."""
        try:
            context = await self._build_plan_context()
            
            if self.orch.planner_editor:
                await self._execute_checklist_planning(context)
            else:
                await self._execute_text_planning(context)
            
            await self._prepare_execution_context()
            return True
            
        except Exception as e:
            self.orch.log.error("Plan regeneration failed: %s", str(e))
            return False
    
    def get_checklist_items(self) -> List[ChecklistItem]:
        """Get the current checklist items as objects."""
        checklist_data = self.orch.frame.metadata.get("checklist", [])
        items = []
        
        for item_data in checklist_data:
            item = ChecklistItem.from_dict(item_data, self.orch.workspace)
            if item:
                items.append(item)
        
        return items
    
    def get_checklist_summary(self) -> str:
        """Get a summary of the current checklist."""
        items = self.get_checklist_items()
        if not items:
            return "No checklist items"
        
        summary = f"Checklist ({len(items)} tasks):\n"
        for i, item in enumerate(items, 1):
            status = "[NEW]" if item.is_new else "[EXISTING]"
            summary += f"  {i}. {status} {item.path}: {item.change_description[:50]}...\n"
        
        return summary
