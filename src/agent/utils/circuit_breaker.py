import time
from enum import Enum
from functools import wraps
from typing import Callable, Awaitable, TypeVar, Dict
import logging

logger = logging.getLogger(__name__)
T = TypeVar("T")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30, name: str = "default"):
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
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "failure_rate": self.failure_count / max(self.total_requests, 1)
        }
    
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self.total_requests += 1
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN")
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception:
                self._on_failure()
                raise
        return wrapper
    
    def _on_success(self):
        self.success_count += 1
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold and self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()