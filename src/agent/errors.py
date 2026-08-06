"""Exception hierarchy shared across the agent."""


class AgentError(Exception):
    """Base class for every error raised by the agent."""


class TransientError(AgentError):
    """A failure that may succeed on retry (e.g. a timeout or flaky call)."""


class SandboxError(AgentError):
    """The sandbox failed to start, run, or clean up a command."""


class ToolError(AgentError):
    """A tool was called with bad arguments or failed while executing."""


class AmbiguousMatchError(ToolError):
    """Multiple identical blocks found, requiring disambiguation."""


class ModelError(TransientError):
    """The model call failed; transient, so the retry layer may recover."""


class RateLimitError(TransientError):
    """The model server returned HTTP 429. Carries the server's Retry-After (seconds), if any.

    Distinct from a generic ModelError so the retry layer can wait the amount the
    server asked for instead of a blind short backoff.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
