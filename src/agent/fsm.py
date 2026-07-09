"""Finite state machine that drives the agent's control loop."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REFLEXING = "reflexing"
    DONE = "done"
    ABORTED = "aborted"
    ERROR = "error"


# event -> (from_state -> to_state)
_TRANSITIONS: Dict[Tuple[AgentState, str], AgentState] = {
    (AgentState.IDLE, "start"): AgentState.PLANNING,
    (AgentState.PLANNING, "plan_ready"): AgentState.EXECUTING,
    (AgentState.EXECUTING, "execution_done"): AgentState.EVALUATING,
    (AgentState.EVALUATING, "passed"): AgentState.DONE,
    (AgentState.EVALUATING, "failed"): AgentState.REFLEXING,
    (AgentState.REFLEXING, "retry"): AgentState.EXECUTING,
    (AgentState.REFLEXING, "give_up"): AgentState.ERROR,
    # Errors and aborts can happen from most working states.
    (AgentState.PLANNING, "error"): AgentState.ERROR,
    (AgentState.EXECUTING, "error"): AgentState.ERROR,
    (AgentState.EVALUATING, "error"): AgentState.ERROR,
    (AgentState.REFLEXING, "error"): AgentState.ERROR,
    (AgentState.PLANNING, "abort"): AgentState.ABORTED,
    (AgentState.EXECUTING, "abort"): AgentState.ABORTED,
    (AgentState.EVALUATING, "abort"): AgentState.ABORTED,
    (AgentState.REFLEXING, "abort"): AgentState.ABORTED,
}

TERMINAL_STATES = (AgentState.DONE, AgentState.ABORTED, AgentState.ERROR)


@dataclass
class TransitionRecord:
    from_state: AgentState
    event: str
    to_state: AgentState
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvalidTransition(Exception):
    pass


class FSM:
    def __init__(self, state: AgentState = AgentState.IDLE) -> None:
        self.state = state
        self.history: List[TransitionRecord] = []

    def can(self, event: str) -> bool:
        return (self.state, event) in _TRANSITIONS

    def transition(self, event: str) -> AgentState:
        key = (self.state, event)
        if key not in _TRANSITIONS:
            raise InvalidTransition(f"No transition for '{event}' from {self.state.value}")
        to_state = _TRANSITIONS[key]
        logger.info("FSM %s --%s--> %s", self.state.value, event, to_state.value)
        self.history.append(TransitionRecord(self.state, event, to_state))
        self.state = to_state
        return to_state

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES
