"""Sandbox configuration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type alias for backend options
BackendType = Literal["auto", "docker", "local"]


class SandboxConfig(BaseModel):
    """Configuration for the execution sandbox.

    ``backend`` selects how commands run:
      * ``"auto"``   - use Docker when available, otherwise fall back to local.
      * ``"docker"`` - always use Docker (raises if unavailable).
      * ``"local"``  - run commands directly on the host inside the workspace.
    """

    workspace: Path = Field(..., description="Working directory for the sandbox")
    backend: BackendType = Field(default="auto", description="Sandbox backend selection")
    image: str = Field(default="ai-agent-sandbox:latest", description="Docker image to use")
    network_disabled: bool = Field(default=True, description="Disable network access in Docker")
    mem_limit: str = Field(default="2g", description="Memory limit for Docker container")
    cpu_limit: float = Field(default=2.0, description="CPU limit for Docker container (cores)")
    timeout: int = Field(
        default=120, 
        ge=1, 
        le=3600,  # Max 1 hour
        description="Per-command timeout in seconds"
    )
    docker_socket: Optional[str] = Field(
        default=None,
        description="Docker socket path (e.g., unix:///var/run/docker.sock)"
    )
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables to pass to commands"
    )
    working_dir: Optional[str] = Field(
        default="/workspace",
        description="Working directory inside the container"
    )


    @field_validator("workspace", mode="before")
    @classmethod
    def validate_workspace(cls, v):
        """Ensure workspace is a valid path and create it if needed."""
        if isinstance(v, str):
            v = Path(v)
        if not isinstance(v, Path):
            raise ValueError(f"workspace must be a Path, got {type(v)}")
        
        # Resolve and expand user home
        workspace = v.expanduser().resolve()
        
        # Check if we have write permissions
        try:
            workspace.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise ValueError(f"Permission denied: cannot create workspace at {workspace}")
        except OSError as e:
            raise ValueError(f"Invalid workspace path: {e}")
            
        return workspace

    @field_validator("mem_limit")
    @classmethod
    def validate_memory_limit(cls, v):
        """Validate memory limit format."""
        import re
        pattern = r'^(\d+)(b|k|m|g|t)?$'
        if not re.match(pattern, v.lower()):
            raise ValueError(f"Invalid memory limit format: {v}. Use formats like '512m', '2g'")
        return v

    @field_validator("cpu_limit")
    @classmethod
    def validate_cpu_limit(cls, v):
        """Validate CPU limit is positive."""
        if v <= 0:
            raise ValueError(f"CPU limit must be positive, got {v}")
        if v > 100:  # Docker supports up to 100 cores
            raise ValueError(f"CPU limit exceeds maximum (100), got {v}")
        return v

    @field_validator("image")
    @classmethod
    def validate_image_name(cls, v):
        """Validate Docker image name format."""
        import re
        # Basic Docker image name validation
        # Allows: repository/image:tag or image:tag
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*([/:][a-zA-Z0-9_.-]+)*(:[a-zA-Z0-9_.-]+)?$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid Docker image name format: {v}")
        return v

    def get_docker_environment(self) -> dict:
        """Get Docker-specific environment variables."""
        env = self.environment.copy()
        if self.docker_socket:
            env["DOCKER_HOST"] = self.docker_socket
        return env

    def get_sandbox_env(self) -> dict:
        """Get environment variables for the sandbox."""
        import os
        env = os.environ.copy()
        env.update(self.environment)
        return env

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "workspace": "/path/to/workspace",
                    "backend": "auto",
                    "image": "python:3.11-slim",
                    "mem_limit": "4g",
                    "cpu_limit": 4.0,
                    "timeout": 300,
                }
            ]
        },
    )
