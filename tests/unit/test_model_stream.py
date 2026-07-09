import json

import httpx

from agent.model.client import OllamaClient


def _ndjson(*objs) -> bytes:
    return "\n".join(json.dumps(o) for o in objs).encode()


async def test_chat_stream_accumulates_tokens_and_tool_calls():
    body = _ndjson(
        {"message": {"content": "Hel"}},
        {"message": {"content": "lo"}},
        {"message": {"content": "", "tool_calls": [
            {"function": {"name": "finish", "arguments": {"summary": "ok"}}}
        ]}},
        {"done": True, "message": {"content": ""}},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, content=body)

    client = OllamaClient(transport=httpx.MockTransport(handler))
    tokens: list[str] = []
    try:
        resp = await client.chat_stream(
            [{"role": "user", "content": "hi"}], on_token=tokens.append
        )
    finally:
        await client.close()

    assert "".join(tokens) == "Hello"
    assert resp.content == "Hello"
    assert resp.tool_calls and resp.tool_calls[0]["function"]["name"] == "finish"


async def test_chat_stream_survives_malformed_lines():
    body = b'not-json\n' + _ndjson(
        {"message": {"content": "ok"}},
        {"done": True, "message": {"content": ""}},
    )

    client = OllamaClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    try:
        resp = await client.chat_stream([{"role": "user", "content": "x"}])
    finally:
        await client.close()

    assert resp.content == "ok"
