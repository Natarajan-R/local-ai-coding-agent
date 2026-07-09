"""Lightweight run statistics (token counts and timing) for a task run.

Ollama reports token counts and durations in the final response chunk. We
accumulate them across every model call so the CLI can print a summary. These
are local models, so "cost" is measured in tokens and wall-clock time rather
than dollars.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RunStats:
    model_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_duration_ns: int = 0

    def record(self, raw: Optional[Dict[str, Any]]) -> None:
        """Accumulate the metadata from one Ollama response chunk.

        A missing (``None``) payload is ignored, but an empty dict still counts
        as a model call that simply reported no token metadata.
        """
        if raw is None:
            return
        self.model_calls += 1
        self.prompt_tokens += int(raw.get("prompt_eval_count") or 0)
        self.completion_tokens += int(raw.get("eval_count") or 0)
        self.total_duration_ns += int(raw.get("total_duration") or 0)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def total_seconds(self) -> float:
        return self.total_duration_ns / 1e9

    @property
    def tokens_per_second(self) -> float:
        secs = self.total_seconds
        return self.completion_tokens / secs if secs > 0 else 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model_calls": self.model_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_seconds": round(self.total_seconds, 2),
            "tokens_per_second": round(self.tokens_per_second, 1),
        }
