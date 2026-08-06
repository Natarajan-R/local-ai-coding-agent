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
import re
from dataclasses import dataclass
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

DEFAULT_CHARS_PER_TOKEN = 4.0
PER_MESSAGE_OVERHEAD_TOKENS = 4  # role tags, delimiters, etc.
TRUNCATE_FLOOR_CHARS = 200      # never shrink a message's content below this
TRUNCATE_MARKER = "\n[... truncated to fit context ...]"

SUMMARY_MAX_CHARS = 800         # cap the digest so it can never dominate the budget
SUMMARY_MAX_FILES = 15
# A code-ish path token: has a dir separator or a source-y suffix.
_PATH_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]+")
# Strong test/error signals worth carrying forward from dropped history.
_SIGNAL_RE = re.compile(
    r"Traceback|No module named|ModuleNotFoundError|SyntaxError|ImportError|"
    r"\bError\b|\bException\b|\d+\s+(?:failed|passed|error)|AssertionError"
)


@dataclass
class TrimResult:
    """The outcome of a trim: the messages, whether trimming happened, and token totals."""

    messages: List[Dict]
    trimmed: bool
    dropped: int
    est_tokens: int


class ContextManager:
    """Trims a message list to fit the model's token budget, pinning key anchors."""

    def __init__(
        self,
        max_tokens: int = 8192,
        response_reserve: int = 1024,
        keep_recent: int = 6,
        chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    ) -> None:
        """Configure the window size, response reserve, and how many recent turns to keep."""
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
        """Estimate the token count of ``text`` via the chars-per-token heuristic."""
        if not text:
            return PER_MESSAGE_OVERHEAD_TOKENS
        return int(len(text) / self.chars_per_token) + PER_MESSAGE_OVERHEAD_TOKENS

    def _msg_tokens(self, message: Dict) -> int:
        """Estimate the token cost of a single chat message."""
        return self.estimate(str(message.get("content", "")))

    def total_tokens(self, messages: List[Dict]) -> int:
        """Estimate the combined token cost of a whole message list."""
        return sum(self._msg_tokens(m) for m in messages)

    def _is_pinned(self, idx: int, msg: Dict, first_non_sys_idx: int) -> bool:
        """Return True if a message must never be trimmed (system anchors, task primer)."""
        if idx <= first_non_sys_idx:
            return True
        content = str(msg.get("content", ""))
        if content.startswith("# Project memory (facts learned"):
            return True
        if content.startswith("Lesson from a previous attempt:"):
            return True
        if content.startswith("The change failed evaluation."):
            return True
        return False

    # -- fitting -------------------------------------------------------------
    def fit(self, messages: List[Dict]) -> TrimResult:
        """Return a copy of ``messages`` trimmed to fit the token budget."""
        total = self.total_tokens(messages)
        if total <= self.budget or len(messages) <= 2:
            return TrimResult(list(messages), False, 0, total)

        n = len(messages)

        # Identify the first user/assistant/tool message (first non-system message)
        first_non_sys_idx = 0
        while first_non_sys_idx < n and messages[first_non_sys_idx].get("role") == "system":
            first_non_sys_idx += 1

        # Tail: the most recent turns, always kept.
        tail_start = max(first_non_sys_idx + 1, n - self.keep_recent)

        # Candidates for dropping: messages before tail_start that are not pinned
        candidates = []
        for i in range(n):
            if i < tail_start and not self._is_pinned(i, messages[i], first_non_sys_idx):
                candidates.append(i)

        dropped_indices = set()
        current_tokens = total
        # Leave room for the digest that replaces the dropped block (bounded by
        # SUMMARY_MAX_CHARS), so we don't drop too little and immediately hard-truncate.
        marker_tokens = self.estimate("x" * SUMMARY_MAX_CHARS)

        # Drop oldest candidates first
        for idx in candidates:
            if current_tokens + (marker_tokens if not dropped_indices else 0) <= self.budget:
                break
            current_tokens -= self._msg_tokens(messages[idx])
            dropped_indices.add(idx)

        # Rebuild messages list. Instead of a bare "N omitted" marker (pure FIFO, which
        # discards which files were touched and the last error seen), replace the dropped
        # block with a compact extractive digest of it.
        dropped_msgs = [messages[i] for i in range(n) if i in dropped_indices]
        rebuilt = []
        has_dropped = False
        for i in range(n):
            if i in dropped_indices:
                if not has_dropped:
                    rebuilt.append({
                        "role": "user",
                        "content": self._summarize_dropped(dropped_msgs),
                    })
                    has_dropped = True
                continue
            rebuilt.append(messages[i])

        # Last resort: if still too big, apply hard truncate on rebuilt list
        if self.total_tokens(rebuilt) > self.budget:
            rebuilt = self._hard_truncate(rebuilt)

        return TrimResult(rebuilt, True, len(dropped_indices), self.total_tokens(rebuilt))

    def _summarize_dropped(self, dropped: List[Dict]) -> str:
        """Build a compact, deterministic digest of the messages being dropped.

        Pure FIFO trimming replaces old turns with a bare "N omitted" marker, discarding
        the two things a mid-task agent most needs to retain: which files it has already
        touched, and the last test/error signal it saw. (Its goals, plan and lessons are
        pinned and survive trimming anyway.) This extracts exactly those from the dropped
        text with no LLM call — so it is free, deterministic, and cannot itself fail or
        rate-limit on the very turn the window is already under pressure. An LLM-written
        summary would be richer but adds cost and a new failure mode on the hot path;
        the state that actually drives recovery is captured well enough by extraction.
        Capped at SUMMARY_MAX_CHARS so the digest can never dominate the budget.
        """
        files: List[str] = []
        seen: Set[str] = set()
        last_signal = ""
        for m in dropped:
            content = str(m.get("content", ""))
            for tok in _PATH_RE.findall(content):
                if tok in seen or ".." in tok:
                    continue
                if "/" in tok or tok.endswith(
                    (".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml")
                ):
                    seen.add(tok)
                    files.append(tok)
            for line in content.splitlines():
                line = line.strip()
                if line and len(line) < 200 and _SIGNAL_RE.search(line):
                    last_signal = line  # keep the most recent signal across dropped turns

        parts = [
            f"[... {len(dropped)} earlier step(s) summarized to fit the context window ...]"
        ]
        if files:
            shown = ", ".join(files[:SUMMARY_MAX_FILES])
            extra = len(files) - SUMMARY_MAX_FILES
            more = f" (+{extra} more)" if extra > 0 else ""
            parts.append(f"Files touched in the omitted steps: {shown}{more}.")
        if last_signal:
            parts.append(f"Most recent earlier test/error signal: {last_signal[:180]}")
        summary = "\n".join(parts)
        if len(summary) > SUMMARY_MAX_CHARS:
            summary = summary[:SUMMARY_MAX_CHARS] + " ..."
        return summary

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
            """Return the indices still eligible to be shrunk this pass."""
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
