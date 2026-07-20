"""Reflexion: turn a failed evaluation into a concrete lesson for the next try."""
from __future__ import annotations

import logging
from pathlib import Path

from .evaluator import EvalResult

logger = logging.getLogger(__name__)

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
"""


class ReflexionEngine:
    def __init__(self, model, evaluator, sandbox, policy, indexer=None, chat_fn=None) -> None:
        self.model = model
        self.evaluator = evaluator
        self.sandbox = sandbox
        self.policy = policy
        self.indexer = indexer
        self._symbols = None
        if indexer:
            from ..perception.symbols import SymbolIndex
            self._symbols = SymbolIndex(indexer)
        # A resilient (retry + circuit-breaker) chat callable may be injected;
        # otherwise fall back to the raw model client.
        self._chat = chat_fn or model.chat

    def _get_symbol_context(self, task: str, details: str) -> str:
        if not self._symbols:
            return ""
        try:
            conn = self._symbols._ensure()
            # Get definitions
            defs = conn.execute(
                "SELECT path, kind, name, line FROM symbols ORDER BY path, line"
            ).fetchall()
            # Get imports
            imps = conn.execute(
                "SELECT path, module, line FROM imports ORDER BY path, line"
            ).fetchall()
        except Exception as e:
            logger.warning("Failed to retrieve symbol context: %s", e)
            return ""

        if not defs and not imps:
            return ""

        # Group definitions by file
        by_file_defs = {}
        for path, kind, name, line in defs:
            by_file_defs.setdefault(path, []).append((kind, name, line))
            
        # Group imports by file
        by_file_imps = {}
        for path, module, line in imps:
            by_file_imps.setdefault(path, []).append((module, line))
            
        all_files = sorted(set(by_file_defs.keys()) | set(by_file_imps.keys()))
        
        # If there are many files, filter to keep the context compact.
        # We include a file if its path/name appears in the task or details, or if the total number of files is small.
        if len(all_files) > 30:
            relevant_files = []
            for path in all_files:
                path_lower = path.lower()
                name_lower = Path(path).name.lower()
                if (path_lower in task.lower() or 
                    name_lower in task.lower() or 
                    path_lower in details.lower() or 
                    name_lower in details.lower()):
                    relevant_files.append(path)
            # Fallback in case none matched (unlikely, but safe): keep first 10 files
            if not relevant_files:
                relevant_files = all_files[:10]
            all_files = relevant_files

        lines = ["\nHere is the actual symbol structure of the codebase (definitions and imports):"]
        for path in all_files:
            lines.append(f"- File `{path}`:")
            file_defs = by_file_defs.get(path, [])
            if file_defs:
                lines.append("  Definitions:")
                for kind, name, line in file_defs:
                    lines.append(f"    - {kind} `{name}` (line {line})")
            file_imps = by_file_imps.get(path, [])
            if file_imps:
                lines.append("  Imports:")
                for module, line in file_imps:
                    lines.append(f"    - `{module}` (line {line})")
        return "\n".join(lines)

    async def reflect(self, task: str, eval_result: EvalResult) -> str:
        """Ask the model to produce a short lesson from the failure."""
        details = (eval_result.details or "")[:4000]
        symbol_context = self._get_symbol_context(task, details)
        prompt = REFLEXION_PROMPT.format(
            task=task,
            summary=eval_result.summary,
            details=details,
            symbol_context=symbol_context,
        )
        messages = [
            {"role": "system", "content": "You are a precise debugging assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self._chat(messages)
            lesson = response.content.strip()
        except Exception as exc:  # never let reflection crash the loop
            logger.warning("Reflexion failed: %s", exc)
            lesson = f"Evaluation failed: {eval_result.summary}. Re-examine the last edit."
        logger.info("Reflexion lesson: %s", lesson)
        return lesson

