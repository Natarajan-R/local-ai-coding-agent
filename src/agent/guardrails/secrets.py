"""Secret scanning: detect and redact credentials before they leak."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# (name, compiled pattern) pairs for common secret shapes.
_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("generic_secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{12,}"
    )),
]


@dataclass
class SecretFinding:
    kind: str
    match: str
    start: int
    end: int


class SecretsScanner:
    """Find and redact secrets in arbitrary text (tool output, diffs, ...)."""

    def scan(self, text: str) -> List[SecretFinding]:
        findings: List[SecretFinding] = []
        if not text:
            return findings
        for kind, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                findings.append(SecretFinding(kind, m.group(0), m.start(), m.end()))
        return findings

    def has_secrets(self, text: str) -> bool:
        return bool(self.scan(text))

    def redact(self, text: str, placeholder: str = "[REDACTED]") -> str:
        if not text:
            return text
        redacted = text
        for _, pattern in _PATTERNS:
            redacted = pattern.sub(placeholder, redacted)
        return redacted
