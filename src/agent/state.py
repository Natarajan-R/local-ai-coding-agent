"""Mutable state carried through the agent's control loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentFrame:
    task_description: str
    plan: Optional[str] = None
    current_file: Optional[Path] = None
    last_diff: Optional[str] = None
    last_error_summary: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    reflections: List[str] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_reflection(self, lesson: str) -> None:
        self.reflections.append(lesson)
