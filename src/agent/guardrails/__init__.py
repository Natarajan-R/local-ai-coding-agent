"""Security guardrails for the coding agent."""
from .approval import ApprovalGate
from .audit import AuditLogger
from .commands import CommandDecision, CommandGuard
from .paths import is_safe_path, safe_join
from .policy import SecurityPolicy
from .secrets import SecretFinding, SecretsScanner

__all__ = [
    "ApprovalGate",
    "AuditLogger",
    "CommandDecision",
    "CommandGuard",
    "is_safe_path",
    "safe_join",
    "SecurityPolicy",
    "SecretFinding",
    "SecretsScanner",
]
