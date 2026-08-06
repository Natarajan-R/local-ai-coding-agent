"""Factory for creating orchestrator sub-components."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from .memory import MemoryStore
from .model.client import OllamaClient
from .perception.indexer import WorkspaceIndexer
from .perception.lsp import LSPManager
from .sandbox.config import SandboxConfig
from .sandbox.manager import SandboxManager
from .guardrails.policy import SecurityPolicy
from .tools.registry import ToolRegistry

if TYPE_CHECKING:
    from .orchestrator import OrchestratorConfig


class ComponentFactory:
    """Factory for creating orchestrator components."""

    @staticmethod
    def create_model(config: OrchestratorConfig) -> OllamaClient:
        """Create the model client."""
        return OllamaClient(
            model_name=config.model_name,
            host=config.host,
            options={"temperature": config.temperature, "num_ctx": config.num_ctx},
            min_request_interval=config.request_interval,
        )

    @staticmethod
    def create_sandbox(config: OrchestratorConfig) -> SandboxManager:
        """Create the sandbox manager."""
        return SandboxManager(
            SandboxConfig(
                workspace=config.workspace,
                backend=config.sandbox_backend,
                network_disabled=not config.sandbox_network,
            )
        )

    @staticmethod
    def create_policy(config: OrchestratorConfig) -> SecurityPolicy:
        """Create the security policy."""
        return SecurityPolicy(
            config.workspace,
            interactive=config.interactive,
            log_dir=config.log_dir,
            protected_paths=config.protected_paths,
        )

    @staticmethod
    def create_indexer(config: OrchestratorConfig) -> WorkspaceIndexer:
        """Create the workspace indexer."""
        return WorkspaceIndexer(config.workspace)

    @staticmethod
    def create_lsp(config: OrchestratorConfig) -> Optional[LSPManager]:
        """Create the LSP manager if available."""
        return LSPManager(config.workspace) if LSPManager.is_available(config.workspace) else None

    @staticmethod
    def create_tools(
        sandbox: SandboxManager,
        policy: SecurityPolicy,
        workspace: Path,
        lsp: Optional[LSPManager],
        indexer: WorkspaceIndexer,
        memory: MemoryStore,
        approval_callback: Optional[Callable],
    ) -> ToolRegistry:
        """Create the tool registry."""
        return ToolRegistry(
            sandbox, policy, workspace,
            lsp=lsp,
            approval_callback=approval_callback,
            indexer=indexer,
            memory=memory,
        )
