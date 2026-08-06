"""Central security policy wiring together every guardrail."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, List, Optional

from .approval import ApprovalGate
from .audit import AuditLogger
from .commands import CommandDecision, CommandGuard
from .paths import is_safe_path, safe_join
from .secrets import SecretsScanner

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """A generic allow/deny outcome with an explanatory reason."""

    allowed: bool
    reason: str = "ok"


class SecurityPolicy:
    """Single entry point the rest of the agent uses to stay safe.

    Combines path confinement, command allow/deny checks, secret scanning,
    human approval and an append-only audit trail.
    """

    def __init__(
        self,
        workspace: Path,
        interactive: bool = True,
        log_dir: Optional[Path] = None,
        approval_prompt: Optional[Callable[[str, str], bool]] = None,
        protected_paths: Optional[List[str]] = None,
    ) -> None:
        """Assemble the guard, scanner, approval gate and audit log for one workspace.

        ``protected_paths`` are glob patterns, relative to the workspace, that the
        agent may read but must never write (e.g. ``migrations/**``, ``*.lock``).
        """
        self.workspace = Path(workspace).resolve()
        self.command_guard = CommandGuard()
        self.secrets_scanner = SecretsScanner()
        self.approval = ApprovalGate(enabled=interactive, prompt_fn=approval_prompt)
        self.protected_paths: List[str] = list(protected_paths or [])
        # Default to ./logs so the audit trail sits alongside the app log
        # (agent.log), regardless of where the workspace lives.
        self.audit = AuditLogger(log_dir or Path("logs"))

    # -- paths ---------------------------------------------------------------
    def validate_path(self, target: str) -> bool:
        """Return True if ``target`` stays inside the workspace; audit denials."""
        ok = is_safe_path(self.workspace, target)
        if not ok:
            self.audit.record("path_denied", target=target)
        return ok

    def resolve_path(self, target: str) -> Path:
        """Resolve ``target`` to an absolute path safely confined to the workspace."""
        return safe_join(self.workspace, target)

    def _relative(self, target) -> str:
        """Return ``target`` as a workspace-relative posix path for pattern matching."""
        p = Path(target)
        if not p.is_absolute():
            p = self.workspace / p
        try:
            return p.resolve().relative_to(self.workspace).as_posix()
        except ValueError:
            # Outside the workspace entirely -- validate_path is what rejects that.
            return p.as_posix()

    def is_protected(self, target) -> bool:
        """Return True if ``target`` matches a protected pattern (read ok, write not).

        Matches both the plain pattern and a ``**/``-prefixed form, so ``*.lock``
        catches a lock file at any depth while ``migrations/**`` still scopes to a
        directory. Directory patterns also match the directory itself.
        """
        if not self.protected_paths:
            return False
        rel = self._relative(target)
        for pattern in self.protected_paths:
            pat = pattern.strip().rstrip("/")
            if not pat:
                continue
            if fnmatch(rel, pat) or fnmatch(rel, f"**/{pat}"):
                return True
            # `migrations/**` should also protect `migrations` itself, and a bare
            # `migrations` should protect everything beneath it.
            if fnmatch(rel, f"{pat}/**") or fnmatch(rel, pat.removesuffix("/**")):
                return True
        return False

    def validate_write(self, target) -> bool:
        """Return True if the agent may WRITE ``target``; audit every refusal.

        Path confinement alone was never enough: it keeps edits inside the
        workspace, but a task saying "do not modify X" had no enforcement behind it
        at all, so the instruction was advisory. On 2026-07-23 the agent modified
        tracked files it had been told to leave alone in 2 of 6 runs. This is the
        mechanism that makes such an instruction real.
        """
        if not self.is_protected(target):
            return True
        self.audit.record("write_denied", target=str(target), reason="protected path")
        return False

    # -- commands ------------------------------------------------------------
    def validate_command(self, command: str) -> CommandDecision:
        """Check a command against the guard and record the decision in the audit log."""
        decision = self.command_guard.check(command)
        self.audit.record(
            "command_check",
            command=command,
            allowed=decision.allowed,
            reason=decision.reason,
        )
        return decision

    def approve_command(self, command: str) -> bool:
        """Validate a command and, if allowed, obtain human approval."""
        decision = self.validate_command(command)
        if not decision.allowed:
            return False
        approved = self.approval.request("run_command", command)
        self.audit.record("command_approval", command=command, approved=approved)
        return approved

    async def approve_command_async(self, command: str, approver) -> bool:
        """Async approval path: validate via the deny-list, then await ``approver``.

        Used by the web UI, where the human decision arrives over a socket and
        cannot block the event loop. ``approver(action, detail) -> Awaitable[bool]``.
        """
        decision = self.validate_command(command)
        if not decision.allowed:
            return False
        approved = bool(await approver("run_command", command))
        self.audit.record("command_approval", command=command, approved=approved)
        return approved

    # -- secrets -------------------------------------------------------------
    def scrub(self, text: str) -> str:
        """Redact any secrets in ``text`` before it is logged or displayed."""
        return self.secrets_scanner.redact(text)

    def contains_secrets(self, text: str) -> bool:
        """Return True if ``text`` contains a detectable secret."""
        return self.secrets_scanner.has_secrets(text)
