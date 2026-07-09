"""Command guardrails: block obviously destructive shell commands."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import List

from .ast_commands import ast_check

# Structural patterns that are dangerous regardless of the executable and have
# near-zero false-positive risk. Always applied.
STRUCTURAL_DENY_PATTERNS: List[str] = [
    r":\(\)\s*\{",                    # fork bomb :(){ :|:& };:
    r">\s*/dev/sd[a-z]",              # write to a raw disk
    r"\bmkfs\b",                       # format a filesystem
]

# Full deny-list, used only as a fallback when the AST guard (bashlex) is not
# available. These executable-name patterns can over-block a command that merely
# *mentions* a word (e.g. `echo sudo`); the AST guard checks the real executable
# instead and is preferred when present.
DEFAULT_DENY_PATTERNS: List[str] = STRUCTURAL_DENY_PATTERNS + [
    r"\brm\s+-rf?\s+/(?:\s|$)",       # rm -rf /
    r"\brm\s+-rf?\s+~",               # rm -rf ~
    r"\brm\s+-rf?\s+\*",              # rm -rf *
    r"\bdd\b.*\bof=/dev/",            # overwrite a device
    r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b",
    r"\bsudo\b",                       # privilege escalation
    r"\bchmod\s+-R?\s*777\s+/",       # loosen perms on root
    r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(sh|bash)\b",  # curl | sh
    r"\b(shred|wipe)\b",
    r"\bgit\s+push\b.*--force",       # destructive history rewrite
]


@dataclass
class CommandDecision:
    allowed: bool
    reason: str = ""
    requires_approval: bool = False


@dataclass
class CommandGuard:
    """Evaluate whether a shell command is safe to execute in the sandbox."""

    deny_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_DENY_PATTERNS))

    def __post_init__(self) -> None:
        self._deny = [re.compile(p) for p in self.deny_patterns]
        self._structural = [re.compile(p) for p in STRUCTURAL_DENY_PATTERNS]

    def check(self, command: str) -> CommandDecision:
        text = (command or "").strip()
        if not text:
            return CommandDecision(False, "Empty command")

        # Reject shell metacharacters that could smuggle a blocked command.
        try:
            shlex.split(text)
        except ValueError as exc:
            return CommandDecision(False, f"Unparseable command: {exc}")

        # Always block structural hazards (fork bomb, raw-disk writes, mkfs).
        for pattern in self._structural:
            if pattern.search(text):
                return CommandDecision(False, f"Command matches blocked pattern: {pattern.pattern}")

        # Prefer the AST guard (bashlex): it checks the real executable of every
        # command node and normalizes quoting, avoiding the regex false-positives
        # on commands that merely mention a word (e.g. `echo sudo`).
        ast_result = ast_check(text)
        if ast_result is not None:
            if not ast_result[0]:
                return CommandDecision(False, f"AST guard: {ast_result[1]}")
            return CommandDecision(True, "ok")

        # Fallback (bashlex unavailable): the full regex deny-list. This may
        # over-block, which is the safe direction.
        for pattern in self._deny:
            if pattern.search(text):
                return CommandDecision(
                    False, f"Command matches blocked pattern: {pattern.pattern}"
                )
        return CommandDecision(True, "ok")

    def is_allowed(self, command: str) -> bool:
        return self.check(command).allowed
