import pytest

from agent.utils.retry import async_retry


async def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert await flaky() == "ok"
    assert calls["n"] == 3


async def test_retry_exhausts_and_reraises():
    calls = {"n": 0}

    @async_retry(max_attempts=2, base_delay=0.01, exceptions=(ValueError,))
    async def always_fails():
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await always_fails()
    assert calls["n"] == 2  # exactly max_attempts


async def test_retry_ignores_unlisted_exceptions():
    calls = {"n": 0}

    @async_retry(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
    async def wrong_error():
        calls["n"] += 1
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        await wrong_error()
    assert calls["n"] == 1  # not retried
