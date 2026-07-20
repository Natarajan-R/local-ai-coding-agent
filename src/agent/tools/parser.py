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
from typing import Any, Dict, List, Optional, Tuple

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


def _repair_docstring_json(chunk: str) -> Optional[str]:
    """Rescue a tool call whose payload contains a raw Python docstring.

    A model asked to add a docstring hand-writes this:

        {"name": "search_replace", "arguments": {"replace": "def f():\n    \"\"\"Doc.\"\"\"\n"}}

    ...except it does NOT escape the triple quotes. The bare `\"\"\"` closes the
    JSON string early, `json.loads` raises, and the call is dropped on the floor
    — so the agent appears to "refuse to write docstrings" while actually
    producing perfectly good ones every single time. Measured: documenting a file
    was 0/9 entirely because of this.

    The repair is safe, and provably so: **three consecutive unescaped quotes
    cannot occur in valid JSON.** After a string closes, JSON permits only `,`
    `:` `}` or `]` — never another `"`. So if we have already failed to parse and
    we see `\"\"\"`, it can only be an embedded docstring. A payload that escaped
    them correctly contains no raw triple quote, so this never fires on it.

    Returns the repaired text, or None if there is nothing here to repair.
    """
    if '"""' not in chunk:
        return None
    return chunk.replace('"""', '\\"\\"\\"')


class ToolParser:
    def parse(self, text: str) -> List[ToolCall]:
        """Return every tool call found in ``text`` (possibly empty)."""
        if not text:
            return []

        calls: List[ToolCall] = []
        seen: set[str] = set()

        candidates = self._get_candidate_chunks(text)
        for cand in candidates:
            content = cand["content"]
            is_balanced = cand["is_balanced"]

            if not is_balanced:
                logger.warning(
                    "Parser dropped truncated candidate chunk: JSON decoding failed (unbalanced brackets). "
                    "Chunk: %r",
                    content
                )
                continue

            try:
                data = json.loads(content, strict=False)
            except json.JSONDecodeError as exc1:
                import ast
                try:
                    data = ast.literal_eval(content)
                    if not isinstance(data, (dict, list)):
                        raise ValueError("Not a dict or list literal")
                except Exception:
                    repaired = _repair_docstring_json(content)
                    if repaired is None:
                        logger.warning(
                            "Parser dropped candidate chunk: JSON decoding failed. Error: %s. Chunk: %r",
                            exc1, content
                        )
                        continue
                    try:
                        data = json.loads(repaired, strict=False)
                    except json.JSONDecodeError as exc2:
                        try:
                            data = ast.literal_eval(repaired)
                            if not isinstance(data, (dict, list)):
                                raise ValueError("Not a dict or list literal")
                        except Exception:
                            logger.warning(
                                "Parser dropped candidate chunk: JSON decoding failed even after docstring repair. "
                                "Error: %s. Original: %r. Repaired: %r",
                                exc2, content, repaired
                            )
                            continue

            objects = []
            if isinstance(data, list):
                objects = [d for d in data if isinstance(d, dict)]
            elif isinstance(data, dict):
                objects = [data]

            for obj in objects:
                call = self._to_call(obj)
                if call is None:
                    continue
                key = json.dumps(call.to_dict(), sort_keys=True, default=str)
                if key not in seen:
                    seen.add(key)
                    calls.append(call)

        return calls

    def saw_truncated_call(self, text: str) -> bool:
        """True if ``text`` holds a tool-call chunk that was cut off mid-JSON.

        A truncated call (unbalanced brackets) is dropped by ``parse``, yielding an
        empty result that is indistinguishable from "the model wrote only prose".
        But the right feedback is the opposite: not "use a tool" but "your call was
        too long, send a smaller one". Local models otherwise resend the identical
        oversized call and burn the step budget — observed as three consecutive
        drops on one task. This lets the caller detect the truncation case and say
        so specifically.
        """
        if not text:
            return False
        for cand in self._get_candidate_chunks(text):
            if not cand["is_balanced"] and any(
                key in cand["content"] for key in ('"name"', '"tool"', '"tool_name"')
            ):
                return True
        return False

    def parse_native(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCall]:
        """Convert Ollama-native ``message.tool_calls`` entries to ToolCalls."""
        out: List[ToolCall] = []
        for tc in tool_calls or []:
            fn = tc.get("function", tc)
            name = fn.get("name")
            if not name:
                logger.warning("Native tool call ignored: missing function name in %r", tc)
                continue
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args, strict=False)
                except json.JSONDecodeError as exc:
                    logger.warning("Native tool call arguments JSON decoding failed: %s. Raw: %r", exc, args)
                    args = {"_raw": args}
            out.append(ToolCall(name=name, arguments=args or {}))
        return out

    # -- internals -----------------------------------------------------------
    def _get_candidate_chunks(self, text: str) -> List[Dict[str, Any]]:
        candidates = []
        fenced_spans = []

        # 1. Find fenced blocks
        pattern = re.compile(r"```(?:json|tool_call|tool|tool_name)?\s*", re.IGNORECASE)
        pos = 0
        while True:
            match = pattern.search(text, pos)
            if not match:
                break
            start_content = match.end()
            end_match = text.find("```", start_content)
            if end_match != -1:
                content = text[start_content:end_match].strip()
                candidates.append({
                    "content": content,
                    "is_fenced": True,
                    "is_balanced": True,
                    "source": text[match.start():end_match+3]
                })
                fenced_spans.append((match.start(), end_match + 3))
                pos = end_match + 3
            else:
                content = text[start_content:].strip()
                candidates.append({
                    "content": content,
                    "is_fenced": True,
                    "is_balanced": False,
                    "source": text[match.start():]
                })
                fenced_spans.append((match.start(), len(text)))
                break

        # 2. Find bare objects/lists
        bare_objects = self._scan_objects(text)
        for obj_text, is_balanced, start_idx, end_idx in bare_objects:
            inside_fence = False
            for f_start, f_end in fenced_spans:
                if f_start <= start_idx < f_end:
                    inside_fence = True
                    break
            if inside_fence:
                continue

            if '"name"' in obj_text or '"tool"' in obj_text or '"tool_name"' in obj_text:
                candidates.append({
                    "content": obj_text,
                    "is_fenced": False,
                    "is_balanced": is_balanced,
                    "source": obj_text
                })

        return candidates

    @staticmethod
    def _scan_objects(text: str) -> List[Tuple[str, bool, int, int]]:
        results = []
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch in ('{', '['):
                start_idx = i
                start_char = ch
                end_char = '}' if ch == '{' else ']'
                depth = 1
                in_string = False
                escaped = False
                j = i + 1
                while j < n:
                    c = text[j]
                    if escaped:
                        escaped = False
                        j += 1
                        continue
                    if c == '\\':
                        escaped = True
                        j += 1
                        continue
                    if c == '"':
                        in_string = not in_string
                        j += 1
                        continue
                    if not in_string:
                        if c == start_char:
                            depth += 1
                        elif c == end_char:
                            depth -= 1
                            if depth == 0:
                                results.append((text[start_idx:j+1], True, start_idx, j + 1))
                                i = j
                                break
                    j += 1
                else:
                    results.append((text[start_idx:], False, start_idx, n))
                    break
            i += 1
        return results

    @staticmethod
    def _to_call(obj: Dict[str, Any]) -> "ToolCall | None":
        name = obj.get("name") or obj.get("tool") or obj.get("tool_name")
        if not name or not isinstance(name, str):
            logger.warning(
                "Parser ignored valid JSON object (not a tool call: missing or invalid 'name'/'tool' key). "
                "Object: %r",
                obj
            )
            return None
        args = obj.get("arguments")
        if args is None:
            args = obj.get("args")
        if args is None:
            # Treat remaining keys as arguments (minus the name key).
            args = {k: v for k, v in obj.items() if k not in {"name", "tool", "tool_name"}}
        if isinstance(args, str):
            try:
                args = json.loads(args, strict=False)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Parser decoded string arguments as fallback but JSON parsing failed: %s. Raw: %r",
                    exc, args
                )
                args = {"_raw": args}
        if not isinstance(args, dict):
            args = {"value": args}
        return ToolCall(name=name, arguments=args)
