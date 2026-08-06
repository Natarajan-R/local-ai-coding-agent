"""Java language profile: regex-based skeleton of types and members."""
from __future__ import annotations

import re
from typing import List

from .languages import LanguageProfile

_DECL_RE = re.compile(
    r"^\s*(public|private|protected|static|final|abstract|class|interface|enum|void|[A-Za-z_<>\[\]]+)\b.*",
)
_TYPE_RE = re.compile(r"\b(class|interface|enum)\b")
_METHOD_RE = re.compile(r"[A-Za-z_][\w<>\[\], ]*\s+[A-Za-z_]\w*\s*\([^;{]*\)\s*\{?")


class JavaProfile(LanguageProfile):
    """Regex-based Java profile used when tree-sitter's Java grammar is unavailable."""

    @property
    def name(self) -> str:
        """Language name (``java``)."""
        return "java"

    @property
    def extensions(self) -> List[str]:
        """Extensions handled by this profile (``.java``)."""
        return [".java"]

    def generate_skeleton(self, content: str) -> str:
        """Return a skeleton of Java type and method declarations, bodies elided."""
        lines: List[str] = []
        for raw in content.splitlines():
            line = raw.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "*", "/*")):
                continue
            if _TYPE_RE.search(stripped) and _DECL_RE.match(line):
                lines.append(line.rstrip("{").rstrip() + " { ... }")
            elif _METHOD_RE.search(stripped) and stripped.endswith(("{", ")")):
                lines.append(line.rstrip("{").rstrip() + ";")
        return "\n".join(lines)
