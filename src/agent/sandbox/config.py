"""Sandbox configuration."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SandboxConfig(BaseModel):
    """Configuration for the execution sandbox.

    ``backend`` selects how commands run:
      * ``"auto"``   - use Docker when available, otherwise fall back to local.
      * ``"docker"`` - always use Docker (raises if unavailable).
      * ``"local"``  - run commands directly on the host inside the workspace.
    """

    workspace: Path
    backend: str = "auto"
    image: str = "ai-agent-sandbox:latest"
    network_disabled: bool = True
    mem_limit: str = "2g"
    cpu_limit: float = 2.0
    timeout: int = Field(default=120, description="Per-command timeout in seconds")

    model_config = {"arbitrary_types_allowed": True}
