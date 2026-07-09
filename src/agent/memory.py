"""Persistent, per-project memory that survives across runs.

Modelled on an agent-curated memory: one compact fact per entry, stored in the
workspace so it travels with the project, recalled into the planning context on
the next run, and capped so it never overruns the model's context window.

Sources of memory:
- the agent explicitly saving a durable fact via the ``remember`` tool, and
- automatic capture of a human escalation hint.

Storage: ``<workspace>/.ai-agent/memory.jsonl`` (one JSON object per line).
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

KINDS = ("convention", "lesson", "preference", "note")


@dataclass
class MemoryEntry:
    id: str
    kind: str
    text: str
    created: str
    task: Optional[str] = None


class MemoryStore:
    """Append-only, de-duplicated project memory."""

    def __init__(self, workspace: Path, enabled: bool = True, filename: str = "memory.jsonl") -> None:
        self.enabled = enabled
        self.dir = Path(workspace).resolve() / ".ai-agent"
        self.path = self.dir / filename

    # -- io ------------------------------------------------------------------
    def load(self) -> List[MemoryEntry]:
        if not self.enabled or not self.path.exists():
            return []
        entries: List[MemoryEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                entries.append(MemoryEntry(
                    id=d.get("id", ""), kind=d.get("kind", "note"),
                    text=d.get("text", ""), created=d.get("created", ""),
                    task=d.get("task"),
                ))
            except (json.JSONDecodeError, TypeError):
                continue
        return entries

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join((text or "").lower().split())

    def add(self, text: str, kind: str = "note", task: Optional[str] = None) -> Optional[MemoryEntry]:
        """Append a fact, skipping empties and duplicates. Returns the entry or None."""
        text = (text or "").strip()
        if not self.enabled or not text:
            return None
        if kind not in KINDS:
            kind = "note"
        norm = self._norm(text)
        if any(self._norm(e.text) == norm for e in self.load()):
            return None  # already remembered
        entry = MemoryEntry(
            id=uuid.uuid4().hex[:8], kind=kind, text=text,
            created=datetime.now(timezone.utc).isoformat(), task=task,
        )
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")
        logger.info("Remembered [%s]: %s", kind, text[:80])
        return entry

    def clear(self) -> int:
        n = len(self.load())
        if self.path.exists():
            self.path.unlink()
        return n

    def count(self) -> int:
        return len(self.load())

    # -- recall --------------------------------------------------------------
    def format_for_prompt(self, max_entries: int = 25, max_chars: int = 1800) -> str:
        """A compact, most-recent-first block to inject into the planning context."""
        entries = self.load()
        if not entries:
            return ""
        recent = entries[-max_entries:][::-1]
        lines = ["# Project memory (facts learned in previous runs — honor these):"]
        for e in recent:
            lines.append(f"- [{e.kind}] {e.text}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "\n- …"
        return text
