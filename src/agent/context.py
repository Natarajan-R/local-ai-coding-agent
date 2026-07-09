"""Token-budget management: keep prompts within the model's context window.

Local models have a fixed context window (Ollama's ``num_ctx``, default 8192).
When the running conversation (system prompt + plan + growing tool history)
exceeds it, Ollama silently drops the *oldest* tokens — which usually includes
the system prompt and rules, causing the model to hallucinate tool calls or loop.

This module keeps a call under budget by pinning the important anchors (system
prompt + the task/plan primer) and the most recent turns, dropping the oldest
middle history (with an elision marker), and hard-truncating as a last resort.

Token counts are estimated with a dependency-free char heuristic (~4 chars/token),
which is conservative enough for budgeting without pulling in a tokenizer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

DEFAULT_CHARS_PER_TOKEN = 4.0
PER_MESSAGE_OVERHEAD_TOKENS = 4  # role tags, delimiters, etc.


@dataclass
class TrimResult:
    messages: List[Dict]
    trimmed: bool
    dropped: int
    est_tokens: int


class ContextManager:
    def __init__(
        self,
        max_tokens: int = 8192,
        response_reserve: int = 1024,
        keep_recent: int = 6,
        chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    ) -> None:
        self.max_tokens = max_tokens
        self.response_reserve = response_reserve
        self.keep_recent = keep_recent
        self.chars_per_token = chars_per_token

    @property
    def budget(self) -> int:
        """Tokens available for the prompt (context window minus response reserve)."""
        return max(512, self.max_tokens - self.response_reserve)

    # -- estimation ----------------------------------------------------------
    def estimate(self, text: str) -> int:
        if not text:
            return PER_MESSAGE_OVERHEAD_TOKENS
        return int(len(text) / self.chars_per_token) + PER_MESSAGE_OVERHEAD_TOKENS

    def _msg_tokens(self, message: Dict) -> int:
        return self.estimate(str(message.get("content", "")))

    def total_tokens(self, messages: List[Dict]) -> int:
        return sum(self._msg_tokens(m) for m in messages)

    # -- fitting -------------------------------------------------------------
    def fit(self, messages: List[Dict]) -> TrimResult:
        """Return a copy of ``messages`` trimmed to fit the token budget."""
        total = self.total_tokens(messages)
        if total <= self.budget or len(messages) <= 2:
            return TrimResult(list(messages), False, 0, total)

        n = len(messages)

        # Head: leading system messages + the first message after them (the
        # task/plan primer). These are never dropped.
        head_end = 0
        while head_end < n and messages[head_end].get("role") == "system":
            head_end += 1
        if head_end < n:
            head_end += 1
        head = messages[:head_end]

        # Tail: the most recent turns, always kept.
        tail_start = max(head_end, n - self.keep_recent)
        tail = messages[tail_start:]
        middle = list(messages[head_end:tail_start])

        # Drop oldest middle messages until head + middle + tail fit.
        dropped = 0
        marker_tokens = 20
        while middle and (
            self.total_tokens(head) + self.total_tokens(middle)
            + self.total_tokens(tail) + marker_tokens > self.budget
        ):
            middle.pop(0)
            dropped += 1

        rebuilt: List[Dict] = list(head)
        if dropped:
            rebuilt.append({
                "role": "user",
                "content": f"[... {dropped} earlier step(s) omitted to fit the context window ...]",
            })
        rebuilt.extend(middle)
        rebuilt.extend(tail)

        # Last resort: head + tail alone still too big -> shrink largest contents.
        if self.total_tokens(rebuilt) > self.budget:
            rebuilt = self._hard_truncate(rebuilt)

        return TrimResult(rebuilt, True, dropped, self.total_tokens(rebuilt))

    def _hard_truncate(self, messages: List[Dict]) -> List[Dict]:
        msgs = [dict(m) for m in messages]
        guard = 0
        while self.total_tokens(msgs) > self.budget and guard < 1000:
            guard += 1
            idx = max(range(len(msgs)), key=lambda i: len(str(msgs[i].get("content", ""))))
            content = str(msgs[idx].get("content", ""))
            if len(content) <= 200:
                break  # nothing left worth shrinking
            new_len = max(200, int(len(content) * 0.6))
            msgs[idx]["content"] = content[:new_len] + "\n[... truncated to fit context ...]"
        return msgs
