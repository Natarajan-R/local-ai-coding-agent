"""Shell language profile: skeleton of function definitions."""
from __future__ import annotations

import re
from typing import List

from .languages import LanguageProfile

_FUNC_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\s*\)\s*\{?")


class ShellProfile(LanguageProfile):
    @property
    def name(self) -> str:
        return "shell"

    @property
    def extensions(self) -> List[str]:
        return [".sh", ".bash"]

    def generate_skeleton(self, content: str) -> str:
        lines: List[str] = []
        for raw in content.splitlines():
            m = _FUNC_RE.match(raw)
            if m:
                lines.append(f"{m.group(1)}() {{ ... }}")
        return "\n".join(lines)
