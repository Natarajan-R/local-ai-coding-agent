"""Analyse task descriptions to extract requested file paths."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .file_utils import FileSystemHelper


class TaskAnalyzer:
    """Analyzes task descriptions to extract requirements."""

    FORBIDDEN_PATTERN = re.compile(
        r"\b(?:do\s*n[o']?t|don't|never|avoid|refrain|must\s+not|should\s+not|"
        r"no\s+need\s+to|without\s+creating|except|other\s+than|rather\s+than|"
        r"instead\s+of|leave\s+(?:alone|untouched)|unchanged|unmodified)\b",
        re.IGNORECASE,
    )

    @classmethod
    def extract_requested_files(cls, task: str, workspace: Path) -> List[str]:
        """Extract file paths requested in the task description."""
        text = re.sub(r"\w+://\S+|\bwww\.\S+", " ", task)

        text = " ".join(
            part for part in re.split(r"(?<=[.;!?])\s+|\n", text)
            if not cls.FORBIDDEN_PATTERN.search(part)
        )

        candidates = set()
        for token in re.findall(r"[\w./-]+", text):
            token = token.strip(".,;:")

            if not any(token.endswith(ext) for ext in FileSystemHelper.ALL_EXTENSIONS):
                continue

            if "/" not in token and not token.endswith(".py"):
                continue

            if token.startswith(("/", "..")) or ".." in token:
                continue

            candidates.add(token)

        missing = []
        for rel_path in sorted(candidates):
            try:
                if (workspace / rel_path).exists():
                    continue
                if "/" not in rel_path:
                    filename = Path(rel_path).name
                    if any(workspace.rglob(filename)):
                        continue
                missing.append(rel_path)
            except (OSError, ValueError):
                continue

        return missing
