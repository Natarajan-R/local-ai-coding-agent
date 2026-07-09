"""Reflexion: turn a failed evaluation into a concrete lesson for the next try."""
from __future__ import annotations

import logging

from .evaluator import EvalResult

logger = logging.getLogger(__name__)

REFLEXION_PROMPT = """Your previous attempt to solve the task did not pass evaluation.

Task: {task}

Evaluation summary: {summary}

Evaluation output:
{details}

In 2-4 sentences, diagnose the most likely root cause and state the specific
change you will make next. Be concrete (file names, functions). Do not call tools."""


class ReflexionEngine:
    def __init__(self, model, evaluator, sandbox, policy, chat_fn=None) -> None:
        self.model = model
        self.evaluator = evaluator
        self.sandbox = sandbox
        self.policy = policy
        # A resilient (retry + circuit-breaker) chat callable may be injected;
        # otherwise fall back to the raw model client.
        self._chat = chat_fn or model.chat

    async def reflect(self, task: str, eval_result: EvalResult) -> str:
        """Ask the model to produce a short lesson from the failure."""
        prompt = REFLEXION_PROMPT.format(
            task=task,
            summary=eval_result.summary,
            details=(eval_result.details or "")[:4000],
        )
        messages = [
            {"role": "system", "content": "You are a precise debugging assistant."},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self._chat(messages)
            lesson = response.content.strip()
        except Exception as exc:  # never let reflection crash the loop
            logger.warning("Reflexion failed: %s", exc)
            lesson = f"Evaluation failed: {eval_result.summary}. Re-examine the last edit."
        logger.info("Reflexion lesson: %s", lesson)
        return lesson
