import time
import asyncio
import pytest
import httpx

from agent.model.client import OllamaClient
from agent.errors import RateLimitError
from agent.utils.retry import async_retry


@pytest.mark.asyncio
async def test_throttle_spaces_requests():
    """min_request_interval must space consecutive requests apart."""
    calls = []

    def handler(request):
        calls.append(time.monotonic())
        return httpx.Response(200, json={"message": {"content": "ok", "tool_calls": []}})

    transport = httpx.MockTransport(handler)
    client = OllamaClient(host="http://x", client=httpx.AsyncClient(transport=transport),
                          min_request_interval=0.2)
    t0 = time.monotonic()
    await client.chat([{"role": "user", "content": "a"}])
    await client.chat([{"role": "user", "content": "b"}])
    await client.close()
    assert len(calls) == 2
    assert calls[1] - calls[0] >= 0.18   # ~0.2s apart despite back-to-back calls


@pytest.mark.asyncio
async def test_429_raises_ratelimiterror_with_retry_after():
    """A 429 must become RateLimitError carrying the Retry-After seconds."""
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "7"}, text="rate limited")

    transport = httpx.MockTransport(handler)
    client = OllamaClient(host="http://x", client=httpx.AsyncClient(transport=transport))
    with pytest.raises(RateLimitError) as ei:
        await client.chat([{"role": "user", "content": "a"}])
    await client.close()
    assert ei.value.retry_after == 7.0


@pytest.mark.asyncio
async def test_429_without_retry_after_uses_substantial_default():
    """A 429 with no Retry-After header must back off for a real interval, not 1-2s."""
    from agent.model.client import DEFAULT_RATE_LIMIT_BACKOFF

    def handler(request):
        return httpx.Response(429, text="rate limited")   # NO Retry-After header

    transport = httpx.MockTransport(handler)
    client = OllamaClient(host="http://x", client=httpx.AsyncClient(transport=transport))
    with pytest.raises(RateLimitError) as ei:
        await client.chat([{"role": "user", "content": "a"}])
    await client.close()
    assert ei.value.retry_after == DEFAULT_RATE_LIMIT_BACKOFF
    assert DEFAULT_RATE_LIMIT_BACKOFF >= 15   # enough to actually ride out a rate window


@pytest.mark.asyncio
async def test_retry_honors_retry_after(monkeypatch):
    """async_retry must wait at least the exception's retry_after."""
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    monkeypatch.setattr("agent.utils.retry.asyncio.sleep", fake_sleep)
    attempts = {"n": 0}

    @async_retry(max_attempts=2, base_delay=1.0, max_delay=5.0, exceptions=(RateLimitError,))
    async def flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RateLimitError("429", retry_after=30)
        return "ok"

    assert await flaky() == "ok"
    assert slept and slept[0] >= 30   # honored Retry-After beyond max_delay
