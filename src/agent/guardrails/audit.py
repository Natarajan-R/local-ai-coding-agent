"""Append-only audit log of every guarded action the agent takes."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class AuditLogger:
    """Write structured audit records as JSON lines.

    Records are appended to ``<log_dir>/audit.jsonl`` and mirrored to the
    standard logger so they show up in the console/file logs too.
    """

    def __init__(self, log_dir: Path, filename: str = "audit.jsonl") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / filename
        self._lock = threading.Lock()
        # Fields merged into every record (e.g. a run correlation id).
        self.context: Dict[str, Any] = {}

    def record(self, action: str, **fields: Any) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
        }
        entry.update(self.context)
        entry.update(fields)
        line = json.dumps(entry, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        logger.debug("audit: %s", line)
        return entry
