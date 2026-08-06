"""Mutable execution state for a single CoderAgent run."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ExecutionContext:
    step: int = 0
    mutations: int = 0
    redundant_repeats: int = 0
    blocked_finishes: int = 0
    mutation_steps: int = 0
    subtask_success: bool = False
    checkpoint: Optional[Dict[str, Any]] = None

    def reset_for_subtask(self):
        self.mutation_steps = 0
        self.subtask_success = False
