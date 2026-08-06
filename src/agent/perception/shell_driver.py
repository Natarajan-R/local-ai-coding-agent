"""Shell language profile: skeleton of function definitions."""
from __future__ import annotations

import re
from typing import List

from .languages import LanguageProfile

_FUNC_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\s*\)\s*\{?")


class ShellProfile(LanguageProfile):
    """Regex-based shell profile used when tree-sitter's Bash grammar is unavailable."""

    @property
    def name(self) -> str:
        """Language name (``shell``)."""
        return "shell"

    @property
    def extensions(self) -> List[str]:
        """Extensions handled by this profile (``.sh``, ``.bash``)."""
        return [".sh", ".bash"]

    def generate_skeleton(self, content: str) -> str:
        """Return a skeleton listing the shell function definitions in ``content``."""
        lines: List[str] = []
        for raw in content.splitlines():
            m = _FUNC_RE.match(raw)
            if m:
                lines.append(f"{m.group(1)}() {{ ... }}")
        return "\n".join(lines)
