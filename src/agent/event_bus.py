"""Event bus for decoupled event emission."""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class EventBus:
    """Decoupled event emission via a sink callback.

    Replaces the inline ``emit`` logic that was baked into the Orchestrator,
    giving every component a single, focused way to fire structured UI events.
    """

    def __init__(self, run_id: str, sink: Optional[Callable[[Dict], None]] = None) -> None:
        self._run_id = run_id
        self._sink = sink

    def emit(self, event: str, **data: object) -> None:
        """Emit a structured UI event."""
        if self._sink is None:
            return
        try:
            self._sink({"event": event, "run_id": self._run_id, **data})
        except Exception:
            logger.debug("event sink error for %s", event, exc_info=True)
