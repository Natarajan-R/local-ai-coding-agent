"""Agent configuration constants, run states, and exceptions."""
from __future__ import annotations

from enum import Enum


class AgentConfig:
    MAX_SUBTASK_STEPS = 15
    MILESTONE_SUBTASK_STEPS = 6
    MAX_MILESTONE_RETRIES = 2
    MAX_MUTATIONS_PER_SUBTASK = 8
    THRASH_DETECTION_THRESHOLD = 3
    MAX_REDUNDANT_REPEATS = 3
    MAX_BLOCKED_FINISHES = 2
    FILE_CACHE_MAX_SIZE = 100
    LSP_DIAGNOSTICS_TIMEOUT = 2.0

    MUTATING_TOOLS = frozenset({
        "write_file", "search_replace", "replace_all",
        "add_docstring", "add_parameter", "rename_symbol",
    })

    VERIFY_TOOLS = frozenset({
        "run_command", "get_diagnostics", "read_file",
        "list_files", "outline", "search_text", "read_symbol",
    })

    BLOCKED_SYSTEM_PATHS = {"/etc", "/proc", "/sys", "/dev", "/bin", "/usr/bin"}

    @classmethod
    def configure(cls, *, max_mutations: int = 8) -> None:
        """Override runtime defaults (called once from Orchestrator.__init__)."""
        cls.MAX_MUTATIONS_PER_SUBTASK = max_mutations


class CoderRunState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class AgentStoppedError(Exception):
    """Raised when execution is stopped or paused."""
