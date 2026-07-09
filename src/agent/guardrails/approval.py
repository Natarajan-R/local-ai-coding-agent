"""Human-in-the-loop approval gate for risky actions."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from rich.console import Console
from rich.prompt import Confirm

logger = logging.getLogger(__name__)


class ApprovalGate:
    """Ask the operator to approve an action.

    When ``enabled`` is False (``--auto`` mode) every request is auto-approved.
    A custom ``prompt_fn`` can be injected for testing or non-interactive use.
    """

    def __init__(
        self,
        enabled: bool = True,
        prompt_fn: Optional[Callable[[str, str], bool]] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.enabled = enabled
        self._console = console or Console()
        self._prompt_fn = prompt_fn

    def request(self, action: str, detail: str = "") -> bool:
        """Return True if the action is approved."""
        if not self.enabled:
            logger.debug("Auto-approving '%s' (approval gate disabled)", action)
            return True

        if self._prompt_fn is not None:
            return self._prompt_fn(action, detail)

        self._console.print(
            f"[yellow]Approval required:[/yellow] [bold]{action}[/bold]"
        )
        if detail:
            self._console.print(detail)
        try:
            return Confirm.ask("Proceed?", default=False, console=self._console)
        except (EOFError, KeyboardInterrupt):
            return False
