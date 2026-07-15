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

import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)

DEFAULT_CHARS_PER_TOKEN = 4.0
PER_MESSAGE_OVERHEAD_TOKENS = 4  # role tags, delimiters, etc.
TRUNCATE_FLOOR_CHARS = 200      # never shrink a message's content below this
TRUNCATE_MARKER = "\n[... truncated to fit context ...]"


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
        """Shrink the largest contents until they fit, sparing the system prompt.

        The system message holds the rules and the tool schema — the very things whose
        loss "lobotomizes" the agent (Chapter 32). Picking the globally largest message
        each pass would eat it: once the tool results have been cut down a few times the
        system prompt *becomes* the largest, and the two then alternate, damaging the
        rules while the tool results still had room to shrink. So exhaust everything else
        down to the floor first, and touch the system prompt only if it is the last thing
        left — which means the budget cannot hold the rules at all, and the run is doomed
        whatever we do. Say so loudly rather than silently.
        """
        msgs = [dict(m) for m in messages]
        system = [i for i, m in enumerate(msgs) if m.get("role") == "system"]
        other = [i for i, m in enumerate(msgs) if m.get("role") != "system"]
        exhausted: set = set()

        def pool_of(idxs):
            return [i for i in idxs if i not in exhausted]

        warned = False
        guard = 0
        while self.total_tokens(msgs) > self.budget and guard < 1000:
            guard += 1
            pool = pool_of(other) or pool_of(system)
            if not pool:
                break  # nothing left worth shrinking
            if not pool_of(other) and not warned:
                warned = True
                sys_tokens = sum(self._msg_tokens(msgs[i]) for i in system)
                logger.warning(
                    "Context budget (%d tokens) is too small for the system prompt (~%d). "
                    "Truncating the agent's own rules and tool schema — it will hallucinate "
                    "tool calls and misbehave. Raise the context window to about %d or more.",
                    self.budget, sys_tokens, sys_tokens + self.response_reserve + 512,
                )
            idx = max(pool, key=lambda i: len(str(msgs[i].get("content", ""))))
            content = str(msgs[idx].get("content", ""))
            shrunk = content[:max(TRUNCATE_FLOOR_CHARS, int(len(content) * 0.6))] + TRUNCATE_MARKER
            # The marker is itself ~35 chars, so a message bottoms out a little above the
            # floor. Without this check `len(content) > floor` stays true forever, the
            # rewrite is a no-op, and the loop spins to the guard on every oversized call.
            if len(shrunk) >= len(content):
                exhausted.add(idx)
                continue
            msgs[idx]["content"] = shrunk
        return msgs
