"""Reflexion: turn a failed evaluation into a concrete lesson for the next try."""
from __future__ import annotations

from .evaluator import EvalResult

import logging
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Callable, Awaitable, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Constants
MAX_REFLECTION_DETAILS_LENGTH = 8000
SYMBOL_CACHE_TTL = 300  # 5 minutes
MAX_SYMBOL_FILES = 25
SYMBOL_QUERY_TIMEOUT = 5  # seconds

REFLEXION_PROMPT = """Your previous attempt to solve the task did not pass evaluation.

Task: {task}

Evaluation summary: {summary}

Evaluation output:
{details}
{symbol_context}

In 2-4 sentences, diagnose the most likely root cause and state the specific
change you will make next. Be concrete (file names, functions). Do not call tools.
CRITICAL:
1. Notice which files DEFINE a class/function vs. which files only IMPORT it. Do not advise adding, modifying, or duplicating a class constructor/definition in a file that only imports it.
2. If `add_parameter` was used, a single uniform value is correct. Do not advise hand-editing call sites to pass different values per-site, as this is redundant and breaks the code.
3. Always verify the actual file content before suggesting changes - the symbol context below shows real definitions.
4. If you see imports in a file, do NOT suggest defining that imported symbol in the same file.
5. IMPORT CONSISTENCY: If the error is "cannot import name X from package Y", check whether Y/__init__.py actually re-exports X. Two valid fixes exist — pick ONE and stick with it:
   a) Add `from Y.submodule import X` to Y/__init__.py so the short import works, OR
   b) Change all callers to use the full path `from Y.submodule import X`.
   Do NOT flip-flop between these two approaches across retries — pick one and apply it consistently.
6. __init__.py CONTENT: An `__init__.py` that defines its own classes is almost always wrong. Its job is to re-export public names from submodules (e.g., `from .retry import RetryMiddleware`). If you created a class inside `__init__.py`, move it to a submodule and re-export it.
7. BULK FILE CREATION: The `write_file` tool has a per-phase budget of only a few edits. If you need to create many files (e.g. the evaluator says files are missing), use `run_command` with a shell heredoc to create ALL missing files in ONE command. Example:
   run_command(command='''cat > src/__init__.py << 'PYEOF'\\nfrom .core import *\\nPYEOF\\ncat > src/models/user.py << 'PYEOF'\\nclass User: pass\\nPYEOF''')
   `run_command` does NOT count against the mutation budget. Use it to create boilerplate, __init__.py files, test stubs, and any file that doesn't need complex implementation yet.
8. TEST/IMPLEMENTATION MISMATCH: If tests fail with AttributeError, TypeError, or wrong return values, compare the test assertions against the ACTUAL implementation signatures (shown in the "ACTUAL IMPLEMENTATION SIGNATURES" section below). The test may call a method with the wrong name, wrong arguments, or expect the wrong return type. Fix the TEST to match the real API — do not change the implementation to match wrong tests.
"""


# Simplified prompt for first retry — focused on the most common failure patterns
_REFLEXION_PROMPT_SIMPLE = """Your previous attempt did not pass evaluation.

Task: {task}

Evaluation summary: {summary}

Evaluation output:
{details}
{symbol_context}

Diagnose the root cause in 1-3 sentences and state the specific fix. Do not call tools.
Focus on these common issues FIRST (in order):
1. Import errors: missing __init__.py, wrong import paths, circular imports
2. Missing files: files referenced in imports or __init__.py that don't exist
3. Syntax errors: typos, unclosed strings, invalid Python
4. Wrong test paths: tests importing from wrong locations
5. Test/implementation mismatch: if tests fail with AttributeError or wrong return values, the test assertions may be wrong — compare against the ACTUAL implementation signatures in the output above
"""


class SymbolContext:
    """Cache and manage symbol context from the codebase."""
    
    def __init__(self, indexer):
        self.indexer = indexer
        self._cache: Optional[str] = None
        self._cache_time: float = 0
        self._cache_key: Optional[str] = None
        
    def get_context(self, task: str, details: str, force_refresh: bool = False) -> str:
        """Get symbol context with caching."""
        cache_key = f"{task[:100]}:{details[:100]}"
        
        # Check cache
        if (not force_refresh and 
            self._cache is not None and 
            cache_key == self._cache_key and
            time.time() - self._cache_time < SYMBOL_CACHE_TTL):
            return self._cache
            
        # Build new context
        context = self._build_context(task, details)
        
        # Update cache
        self._cache = context
        self._cache_time = time.time()
        self._cache_key = cache_key
        
        return context
        
    def _build_context(self, task: str, details: str) -> str:
        """Build the symbol context string."""
        if not self.indexer:
            return ""
            
        try:
            # Get the database connection
            from ..perception.symbols import SymbolIndex
            symbols = SymbolIndex(self.indexer)
            conn = None
            
            try:
                conn = symbols._ensure()
                
                # Set query timeout
                conn.execute(f"PRAGMA query_timeout = {SYMBOL_QUERY_TIMEOUT}")
                
                # Get definitions
                defs = conn.execute(
                    "SELECT path, kind, name, line FROM symbols ORDER BY path, line"
                ).fetchall()
                
                # Get imports
                imps = conn.execute(
                    "SELECT path, module, line FROM imports ORDER BY path, line"
                ).fetchall()
                
            except Exception as e:
                logger.warning(f"Failed to execute symbol queries: {e}")
                return ""
            finally:
                if conn:
                    conn.close()
                    
            if not defs and not imps:
                return ""
                
            # Group definitions by file
            by_file_defs: Dict[str, List[tuple]] = {}
            for path, kind, name, line in defs:
                by_file_defs.setdefault(path, []).append((kind, name, line))
                
            # Group imports by file
            by_file_imps: Dict[str, List[tuple]] = {}
            for path, module, line in imps:
                by_file_imps.setdefault(path, []).append((module, line))
                
            all_files = sorted(set(by_file_defs.keys()) | set(by_file_imps.keys()))
            
            # Filter to relevant files
            filtered_files = self._filter_relevant_files(all_files, task, details)
            
            # Build the context string
            return self._format_symbol_context(filtered_files, by_file_defs, by_file_imps)
            
        except Exception as e:
            logger.warning(f"Failed to retrieve symbol context: {e}")
            return ""
            
    def _filter_relevant_files(self, all_files: List[str], task: str, details: str) -> List[str]:
        """Filter to the most relevant files."""
        if len(all_files) <= MAX_SYMBOL_FILES:
            return all_files
            
        # Priority patterns
        priority_patterns = [
            "__init__.py",
            "/models/",
            "/core/",
            "/src/",
            "/lib/",
            "test_",
            "_test.py",
        ]
        
        relevant_files = []
        task_lower = task.lower()
        details_lower = details.lower()
        
        for path in all_files:
            path_lower = path.lower()
            name_lower = Path(path).name.lower()
            
            # Check if file is in task or details
            if (path_lower in task_lower or 
                name_lower in task_lower or 
                path_lower in details_lower or 
                name_lower in details_lower):
                relevant_files.append(path)
                continue
                
            # Check priority patterns
            for pattern in priority_patterns:
                if pattern in path_lower:
                    relevant_files.append(path)
                    break
                    
        # If still too many, take the most recent looking files (by path)
        if len(relevant_files) > MAX_SYMBOL_FILES:
            # Prefer files in common directories first
            priority_dirs = ["src", "lib", "models", "core"]
            sorted_files = []
            for priority_dir in priority_dirs:
                priority_files = [f for f in relevant_files if f.startswith(priority_dir)]
                sorted_files.extend(priority_files)
                relevant_files = [f for f in relevant_files if f not in priority_files]
                
            sorted_files.extend(relevant_files)
            relevant_files = sorted_files[:MAX_SYMBOL_FILES]
            
        return relevant_files
        
    def _format_symbol_context(self, files: List[str], 
                               by_file_defs: Dict[str, List[tuple]],
                               by_file_imps: Dict[str, List[tuple]]) -> str:
        """Format the symbol context as a string."""
        if not files:
            return ""
            
        lines = ["\nHere is the actual symbol structure of the codebase (definitions and imports):"]
        
        for path in files:
            lines.append(f"- File `{path}`:")
            
            # Add definitions
            file_defs = by_file_defs.get(path, [])
            if file_defs:
                lines.append("  Definitions:")
                for kind, name, line in file_defs:
                    # Clean up kind name
                    kind_str = kind.lower()
                    if kind_str == "class":
                        kind_str = "Class"
                    elif kind_str == "function":
                        kind_str = "Function"
                    elif kind_str == "method":
                        kind_str = "Method"
                    elif kind_str == "variable":
                        kind_str = "Variable"
                    lines.append(f"    - {kind_str} `{name}` (line {line})")
                    
            # Add imports
            file_imps = by_file_imps.get(path, [])
            if file_imps:
                lines.append("  Imports:")
                for module, line in file_imps:
                    lines.append(f"    - `{module}` (line {line})")
                    
        return "\n".join(lines)


class ReflexionEngine:
    """Diagnoses a failed evaluation and produces a lesson to guide the next attempt."""

    def __init__(self, model, evaluator, sandbox, policy, 
                 indexer=None, chat_fn: Optional[Callable[[List[Dict]], Awaitable[Any]]] = None) -> None:
        """Wire in the model, evaluator, sandbox and policy, plus optional symbol index and chat callable."""
        self.model = model
        self.evaluator = evaluator
        self.sandbox = sandbox
        self.policy = policy
        
        # Initialize symbol context manager
        self._symbol_context = SymbolContext(indexer) if indexer else None
        
        # A resilient (retry + circuit-breaker) chat callable may be injected;
        # otherwise fall back to the raw model client.
        self._chat = chat_fn or model.chat
        
        # Track reflections to prevent loops
        self._reflection_history: List[str] = []
        self._max_history = 5
        
        # Track detected contradictions for escalation
        self._contradictions_found: int = 0

        # AC-10: Oscillation Freezer — detect and break stuck cycles
        self._oscillation_history: List[Dict[str, Any]] = []  # each entry: {"error_fingerprint": str, "lesson": str}
        self._frozen: bool = False
        self._freeze_reason: Optional[str] = None

    def _detect_contradictions(self, new_lesson: str) -> List[str]:
        """Detect if a new lesson contradicts previous ones.

        Returns a list of contradiction descriptions for warning the model.
        """
        contradictions = []
        if not self._reflection_history:
            return contradictions

        # Patterns indicating import-related directives
        do_patterns = [
            (r"(?:change|replace|update)\s+['\"]?from\s+(\S+)\s+import", "from_import"),
            (r"(?:add|put|place)\s+.*(?:in|to|into)\s+['\"]?(\S*__init__\.py)['\"]?", "init_export"),
            (r"(?:use|prefer)\s+['\"]?(from\s+\S+\s+import\s+\S+)['\"]?", "import_style"),
            (r"(?:change|fix|update)\s+['\"]?(\S+__init__\.py)['\"]?", "init_file"),
        ]

        # Extract import-related directives from the new lesson
        new_imports = set()
        for pattern, kind in do_patterns:
            for match in re.finditer(pattern, new_lesson, re.IGNORECASE):
                new_imports.add((kind, match.group(1).lower()))

        if not new_imports:
            return contradictions

        # Check against previous lessons
        for prev_lesson in self._reflection_history[-3:]:
            prev_imports = set()
            for pattern, kind in do_patterns:
                for match in re.finditer(pattern, prev_lesson, re.IGNORECASE):
                    prev_imports.add((kind, match.group(1).lower()))

            # Detect flip-flop: same kind but different target
            for new_kind, new_target in new_imports:
                for prev_kind, prev_target in prev_imports:
                    if new_kind == prev_kind and new_target != prev_target:
                        contradictions.append(
                            f"Previous lesson said '{prev_target}', now saying '{new_target}' — "
                            f"this is a flip-flop. Pick ONE approach and stick with it."
                        )

        return contradictions

    def _extract_oscillation_fingerprint(self, eval_result: EvalResult) -> str:
        """Extract a compact fingerprint of the error for oscillation detection.

        Groups errors into categories so small wording differences don't
        break detection:
          - "import": import errors, ModuleNotFoundError
          - "syntax": SyntaxError, indentation errors
          - "attr": AttributeError, method not found
          - "type": TypeError, wrong argument count
          - "name": NameError, not defined
          - "file": FileNotFoundError, missing files
          - "test": test collection failure, pytest errors
          - "assert": AssertionError, wrong values
          - "other": everything else
        """
        details = (eval_result.details or "") + (eval_result.summary or "")
        details_lower = details.lower()

        if "module not found" in details_lower or "import error" in details_lower or "cannot import" in details_lower or "no module" in details_lower:
            return "import"
        if "syntax" in details_lower and "error" in details_lower:
            return "syntax"
        if "attributeerror" in details_lower or "attribute error" in details_lower or "has no attribute" in details_lower:
            return "attr"
        if "typeerror" in details_lower or "type error" in details_lower or "missing required positional argument" in details_lower or "takes x" in details_lower:
            return "type"
        if "nameerror" in details_lower or "name error" in details_lower or "is not defined" in details_lower:
            return "name"
        if "filenotfound" in details_lower or "file not found" in details_lower or "no such file" in details_lower:
            return "file"
        if "none could be collected" in details_lower or "pytest" in details_lower:
            return "test"
        if "assert" in details_lower or "assertionerror" in details_lower:
            return "assert"
        if "valueerror" in details_lower or "value error" in details_lower:
            return "value"
        return "other"

    def _detect_oscillation(self) -> Optional[str]:
        """Detect if the model is stuck oscillating between the same error types.

        Returns a freeze directive string if oscillation is detected, None otherwise.
        """
        history = self._oscillation_history
        if len(history) < 3:
            return None

        # Pattern 1: Same error type 3+ times in a row
        fingerprints = [h["fingerprint"] for h in history[-5:]]
        if len(fingerprints) >= 3:
            for i in range(len(fingerprints) - 2):
                if fingerprints[i] == fingerprints[i + 1] == fingerprints[i + 2]:
                    fp = fingerprints[i]
                    directives = {
                        "import": (
                            "STOP flipping between import approaches. "
                            "Use `run_command` with heredocs to update ALL __init__.py files and ALL "
                            "import statements in ONE command. Inherit from existing classes; "
                            "do not redefine them."
                        ),
                        "syntax": (
                            "STOP making syntax errors. Read the code you just wrote carefully "
                            "before submitting. Check for: unclosed brackets, missing colons, "
                            "wrong indentation, string delimiters."
                        ),
                        "attr": (
                            "The test is calling a method name that does not exist on your class. "
                            "Look at the ACTUAL implementation signatures in the symbol context above. "
                            "Either rename your implementation method OR rename the test call. "
                            "Pick one and apply it consistently — do NOT flip-flop."
                        ),
                        "type": (
                            "Your function signature does not match how it is called. "
                            "Check the number and order of parameters. Add default values "
                            "for optional parameters rather than changing call sites."
                        ),
                        "name": (
                            "You're using names that are not defined in scope. "
                            "Add the missing import OR define the name in the correct file. "
                            "Do NOT define something twice."
                        ),
                        "file": (
                            "Files are missing. Use a SINGLE `run_command` with heredocs "
                            "to create ALL missing files at once: "
                            "cat > path1 << 'EOF'\\ncode\\nEOF\\ncat > path2 << 'EOF'\\ncode\\nEOF"
                        ),
                        "test": (
                            "Tests are failing to collect or run. Check that test fixture names "
                            "match, imports resolve, and the test directory has __init__.py. "
                            "If pytest isn't installed, install it via pip."
                        ),
                        "assert": (
                            "Your code runs but produces wrong values. Compare the test assertions "
                            "against your implementation's actual return values and types."
                        ),
                    }
                    return directives.get(fp, "STOP repeating the same approach. Make a concrete, different fix.")
                break

        # Pattern 2: Alternating between 2 fingerprints 4+ times
        if len(fingerprints) >= 4:
            alt_patterns = [
                (fingerprints[i], fingerprints[i + 1], fingerprints[i + 2], fingerprints[i + 3])
                for i in range(len(fingerprints) - 3)
            ]
            for a, b, c, d in alt_patterns:
                if a == c and b == d and a != b:
                    return (
                        f"You are oscillating between '{a}' and '{b}' errors. "
                        "Fix BOTH in one pass. Identify the root cause connecting them "
                        "(e.g., a missing file can cause both import and name errors). "
                        "Use `run_command` with heredocs to fix everything at once."
                    )

        # Pattern 3: Same lesson content repeating (verbatim or near-verbatim)
        if len(history) >= 3:
            recent_lessons = [h["lesson"][:200] for h in history[-3:]]
            if len(set(recent_lessons)) == 1:
                return (
                    "You keep generating the SAME reflection. That means your fix did not work. "
                    "DO NOT repeat the same change. Instead, read the ACTUAL error output carefully "
                    "and try a DIFFERENT approach. Use symbol context to verify file contents."
                )

        return None

    async def reflect(self, task: str, eval_result: EvalResult, retry_count: int = 0) -> str:
        """Ask the model to produce a short lesson from the failure."""
        # Truncate details if needed
        details = (eval_result.details or "")[:MAX_REFLECTION_DETAILS_LENGTH]
        
        # Get symbol context with caching
        symbol_context = ""
        if self._symbol_context:
            symbol_context = self._symbol_context.get_context(task, details)
        
        # Use simple prompt for first retry, full prompt for later retries
        if retry_count <= 1:
            prompt = _REFLEXION_PROMPT_SIMPLE.format(
                task=task,
                summary=eval_result.summary,
                details=details,
                symbol_context=symbol_context,
            )
        else:
            prompt = REFLEXION_PROMPT.format(
                task=task,
                summary=eval_result.summary,
                details=details,
                symbol_context=symbol_context,
            )
        
        # Add history context if available
        if self._reflection_history:
            history_context = "\nPrevious reflection attempts (avoid repeating similar lessons):\n"
            for i, prev_lesson in enumerate(self._reflection_history[-3:], 1):
                history_context += f"{i}. {prev_lesson}\n"
            prompt += history_context
        
        messages = [
            {"role": "system", "content": "You are a precise debugging assistant."},
            {"role": "user", "content": prompt},
        ]
        
        # Attempt to get reflection from model
        try:
            # Add timeout to chat call
            response = await self._chat(messages)
            lesson = response.content.strip()
        except Exception as exc:
            logger.warning(f"Reflexion failed: {exc}")
            lesson = self._fallback_lesson(task, eval_result)
            
        # Validate lesson isn't too long
        if len(lesson) > 1000:
            lesson = lesson[:1000] + "..."

        # AC-10: Oscillation Freezer — detect stuck cycles
        fingerprint = self._extract_oscillation_fingerprint(eval_result)
        self._oscillation_history.append({
            "fingerprint": fingerprint,
            "lesson": lesson,
            "retry_count": retry_count,
        })
        if not self._frozen:
            freeze_directive = self._detect_oscillation()
            if freeze_directive:
                self._frozen = True
                self._freeze_reason = freeze_directive
                logger.warning(
                    "AC-10: Oscillation detected after %d retries. Freezing with: %s",
                    retry_count, freeze_directive[:120],
                )

        # If frozen, prepend the freeze directive to the lesson
        if self._frozen and self._freeze_reason:
            freeze_header = (
                "*** OSCILLATION DETECTED: You have been repeating the same approach "
                "across multiple retries without progress. "
                "ACTIVATE FREEZE MODE:\n\n"
                f"{self._freeze_reason}\n\n"
                "---\n"
            )
            lesson = freeze_header + lesson
            # Reset freeze so next retry can start fresh — but if it oscillates again,
            # _detect_oscillation will fire again.
            self._frozen = False
            self._freeze_reason = None

        # Detect contradictions with previous lessons and prepend warning
        contradictions = self._detect_contradictions(lesson)
        if contradictions:
            self._contradictions_found += len(contradictions)
            warning = (
                "*** CONTRADICTION DETECTED: Your recent lessons flip-flopped on the same import path. "
                "STOP changing it back and forth. Pick ONE approach:\n"
                "  a) Fix __init__.py to re-export the needed names, OR\n"
                "  b) Use the full submodule import path everywhere.\n"
                "Apply that choice to ALL affected files in one pass.\n\n"
            )
            for c in contradictions:
                warning += f"- {c}\n"
            lesson = warning + lesson
            logger.warning(
                "Contradiction detected in reflexion history (%d total)",
                self._contradictions_found,
            )
            
        # Add to history
        self._reflection_history.append(lesson)
        if len(self._reflection_history) > self._max_history:
            self._reflection_history.pop(0)
            
        logger.info(f"Reflexion lesson: {lesson}")
        return lesson
        
    def _fallback_lesson(self, task: str, eval_result: EvalResult) -> str:
        """Generate a fallback lesson when model call fails."""
        # Extract key info from evaluation
        details = eval_result.details or ""
        
        # Check for common patterns
        if "import" in details.lower() and "error" in details.lower():
            return "Import error detected. Check module imports and ensure all dependencies are installed."
        elif "syntax" in details.lower() and "error" in details.lower():
            return "Syntax error detected. Review the code for typos and invalid Python syntax."
        elif "none could be collected" in eval_result.summary.lower():
            return "Test collection failed. Check test file imports and fixtures. Make sure test modules can be imported."
        else:
            return f"Evaluation failed: {eval_result.summary}. Review the code carefully and fix any issues."

    def get_reflection_history(self) -> List[str]:
        """Get the history of reflections."""
        return self._reflection_history.copy()

    def clear_history(self) -> None:
        """Clear the reflection history."""
        self._reflection_history = []

    def reset(self) -> None:
        """Reset the reflexion engine state."""
        self.clear_history()
        if self._symbol_context:
            self._symbol_context._cache = None
            self._symbol_context._cache_time = 0
            self._symbol_context._cache_key = None
        # AC-10: Reset oscillation state
        self._oscillation_history.clear()
        self._frozen = False
        self._freeze_reason = None
