"""A circuit breaker that trips after repeated failures to fail fast."""
import time
from enum import Enum
from functools import wraps
from typing import Callable, Awaitable, TypeVar, Dict
import logging

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised instead of calling through while the breaker is OPEN.

    A distinct type so a caller can tell "we failed fast on purpose" apart from a
    genuine transport error, and degrade accordingly rather than reporting a fault.
    """


class CircuitState(Enum):
    """The three breaker states: healthy, tripped, and probing for recovery."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Decorator that short-circuits an async call once failures exceed a threshold."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30, name: str = "default"):
        """Configure the failure threshold and recovery timeout; start in the CLOSED state."""
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        self.total_requests = 0
        self.last_state_change = time.time()
    
    def get_metrics(self) -> Dict:
        """Return a snapshot of the breaker's state and failure counters."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "failure_rate": self.failure_count / max(self.total_requests, 1)
        }
    
    @property
    def is_open(self) -> bool:
        """True while the breaker is actively rejecting calls (recovery not yet due).

        Lets a caller skip expensive setup it would otherwise do before a call that
        is certain to be rejected.
        """
        if self.state != CircuitState.OPEN:
            return False
        return (time.time() - self.last_failure_time) <= self.recovery_timeout

    def _before_call(self) -> None:
        """Count the attempt, and reject it if the circuit is still open."""
        self.total_requests += 1
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Invoke an async ``func`` through the breaker (non-decorator entry point).

        Raises :class:`CircuitOpenError` without invoking ``func`` while the circuit
        is open.
        """
        self._before_call()
        try:
            result = await func(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        self._on_success()
        return result

    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Wrap an async ``func`` so calls pass through the breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            """Run ``func`` unless the circuit is open; track success/failure."""
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    def _on_success(self):
        """Reset the failure count and close the circuit after a good call."""
        self.success_count += 1
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker '%s' recovered; closing.", self.name)
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()

    def _on_failure(self):
        """Count a failure and trip the circuit open once the threshold is hit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
            logger.warning(
                "Circuit breaker '%s' tripped after %d consecutive failures; "
                "failing fast for %ss.",
                self.name, self.failure_count, self.recovery_timeout,
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()