"""Tolerant parser that extracts tool calls from model output.

Local models emit tool calls inconsistently. This parser accepts, in order of
preference:

1. Native Ollama ``tool_calls`` (handled by the model client, passed through here).
2. Fenced ``json`` / ``tool_call`` code blocks containing an object with a
   ``name``/``tool`` key and an ``arguments``/``args`` object.
3. ``<tool_call>{...}</tool_call>`` XML-ish wrappers.
4. A bare JSON object anywhere in the text as a last resort.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"```(?:json|tool_call|tool)?\s*(\{.*?\}|\[.*?\])\s*```",
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"<tool_call>\s*(\{.*?\}|\[.*?\])\s*</tool_call>", re.DOTALL | re.IGNORECASE)


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


class ToolParser:
    def parse(self, text: str) -> List[ToolCall]:
        """Return every tool call found in ``text`` (possibly empty)."""
        if not text:
            return []

        calls: List[ToolCall] = []
        seen: set[str] = set()

        for chunk in self._candidate_chunks(text):
            for obj in self._iter_objects(chunk):
                call = self._to_call(obj)
                if call is None:
                    continue
                key = json.dumps(call.to_dict(), sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    calls.append(call)

        return calls

    def parse_native(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCall]:
        """Convert Ollama-native ``message.tool_calls`` entries to ToolCalls."""
        out: List[ToolCall] = []
        for tc in tool_calls or []:
            fn = tc.get("function", tc)
            name = fn.get("name")
            if not name:
                continue
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            out.append(ToolCall(name=name, arguments=args or {}))
        return out

    # -- internals -----------------------------------------------------------
    def _candidate_chunks(self, text: str) -> List[str]:
        chunks = _FENCE_RE.findall(text) + _TAG_RE.findall(text)
        if chunks:
            return chunks
        # Last resort: try to locate a bare JSON object with a name/tool key.
        brace = self._first_balanced_object(text)
        return [brace] if brace else []

    def _iter_objects(self, chunk: str):
        try:
            data = json.loads(chunk)
        except json.JSONDecodeError:
            return
        if isinstance(data, list):
            yield from (d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            yield data

    @staticmethod
    def _to_call(obj: Dict[str, Any]) -> "ToolCall | None":
        name = obj.get("name") or obj.get("tool") or obj.get("tool_name")
        if not name or not isinstance(name, str):
            return None
        args = obj.get("arguments")
        if args is None:
            args = obj.get("args")
        if args is None:
            # Treat remaining keys as arguments (minus the name key).
            args = {k: v for k, v in obj.items() if k not in {"name", "tool", "tool_name"}}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        if not isinstance(args, dict):
            args = {"value": args}
        return ToolCall(name=name, arguments=args)

    @staticmethod
    def _first_balanced_object(text: str) -> str | None:
        start = text.find("{")
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                ch = text[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        if '"name"' in candidate or '"tool"' in candidate:
                            return candidate
                        break
            start = text.find("{", start + 1)
        return None
