"""Audit logger for structured audit trail entries."""
from __future__ import annotations

from typing import Any


class AuditLogger:
    """Structured audit trail recording.

    Wraps ``SecurityPolicy.audit.record`` so the Orchestrator and agents
    don't need to know about the policy object to write audit entries.
    """

    def __init__(self, audit: Any) -> None:
        """
        Args:
            audit: The ``policy.audit`` object that exposes ``record(**fields)``.
        """
        self._audit = audit

    def record(self, action: str, **fields: object) -> None:
        """Record an audit entry."""
        self._audit.record(action, **fields)
