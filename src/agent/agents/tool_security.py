"""Security validation for tool operations."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import AgentConfig


class ToolSecurity:
    def __init__(self, workspace_root: Path, policy=None):
        self.policy = policy
        self.workspace_root = workspace_root.resolve()

    def validate_path(self, path: str) -> bool:
        try:
            resolved = (self.workspace_root / path).resolve()
            if not resolved.is_relative_to(self.workspace_root):
                return False
            for blocked in AgentConfig.BLOCKED_SYSTEM_PATHS:
                if str(resolved).startswith(blocked):
                    return False
            if ".." in path or "~" in path:
                return False
            return True
        except (OSError, ValueError):
            return False

    def scrub_output(self, content: str, max_length: int = 20000) -> str:
        if self.policy:
            content = self.policy.scrub(content)
        if len(content) > max_length:
            content = content[:max_length] + "..."
        return content
