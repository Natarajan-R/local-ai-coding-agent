"""Shared runtime state for the orchestrator's execution loop."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class RuntimeState:
    """Mutable control flags shared between the Orchestrator and its agents.

    Groups the scattered ``_stopped``, ``_paused``, ``_paused_event``,
    ``_mutations``, ``_baseline_green``, ``_no_progress_abort`` and callback
    attributes that were previously ad-hoc instance variables on the
    Orchestrator.  Giving these a named home makes ownership explicit and
    prevents the God-Object pattern of agents reaching into private
    orchestrator attributes.
    """

    # ---- pause / stop control ----
    paused: bool = False
    stopped: bool = False
    paused_event: asyncio.Event = field(default_factory=asyncio.Event)

    # ---- progress tracking ----
    mutations: int = 0
    no_progress_abort: bool = False

    # ---- stop-when-green baseline ----
    baseline_green: Optional[bool] = None

    # ---- streaming flag ----
    stream: bool = True

    # ---- callbacks ----
    event_sink: Optional[Callable[[Dict], None]] = None
    escalation_callback: Optional[Callable[[str], Awaitable[Optional[str]]]] = None

    def __post_init__(self) -> None:
        # Ensure the event starts in the "not paused" (set) state.
        self.paused_event.set()
