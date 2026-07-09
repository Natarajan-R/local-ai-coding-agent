import asyncio

import pytest

from agent.utils.circuit_breaker import CircuitBreaker, CircuitState


async def test_success_keeps_closed():
    cb = CircuitBreaker(failure_threshold=3, name="t")

    @cb
    async def ok():
        return 42

    assert await ok() == 42
    assert cb.state == CircuitState.CLOSED


async def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60, name="t")

    @cb
    async def boom():
        raise ValueError("nope")

    for _ in range(2):
        with pytest.raises(ValueError):
            await boom()

    assert cb.state == CircuitState.OPEN
    # While open, calls are rejected without invoking the function.
    with pytest.raises(Exception):
        await boom()


async def test_half_open_recovers():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0, name="t")
    calls = {"n": 0}

    @cb
    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("first fails")
        return "ok"

    with pytest.raises(ValueError):
        await flaky()
    assert cb.state == CircuitState.OPEN

    await asyncio.sleep(0.01)  # recovery_timeout=0 elapsed
    assert await flaky() == "ok"
    assert cb.state == CircuitState.CLOSED


async def test_metrics():
    cb = CircuitBreaker(name="m")

    @cb
    async def ok():
        return 1

    await ok()
    metrics = cb.get_metrics()
    assert metrics["name"] == "m"
    assert metrics["total_requests"] == 1
