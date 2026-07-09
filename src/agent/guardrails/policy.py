"""Central security policy wiring together every guardrail."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .approval import ApprovalGate
from .audit import AuditLogger
from .commands import CommandDecision, CommandGuard
from .paths import is_safe_path, safe_join
from .secrets import SecretsScanner

logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
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
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.command_guard = CommandGuard()
        self.secrets_scanner = SecretsScanner()
        self.approval = ApprovalGate(enabled=interactive, prompt_fn=approval_prompt)
        # Default to ./logs so the audit trail sits alongside the app log
        # (agent.log), regardless of where the workspace lives.
        self.audit = AuditLogger(log_dir or Path("logs"))

    # -- paths ---------------------------------------------------------------
    def validate_path(self, target: str) -> bool:
        ok = is_safe_path(self.workspace, target)
        if not ok:
            self.audit.record("path_denied", target=target)
        return ok

    def resolve_path(self, target: str) -> Path:
        return safe_join(self.workspace, target)

    # -- commands ------------------------------------------------------------
    def validate_command(self, command: str) -> CommandDecision:
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
        return self.secrets_scanner.redact(text)

    def contains_secrets(self, text: str) -> bool:
        return self.secrets_scanner.has_secrets(text)
