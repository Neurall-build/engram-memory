# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neurall. All rights reserved.

"""Auto importance scoring - automatically scores memory importance using LLM."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ImportanceScorer:
    """Automatically scores memory importance using LLM analysis."""

    def __init__(self, openai_client=None):
        self.openai_client = openai_client

    def score(self, content: str, user_provided: Optional[float] = None) -> float:
        """Score memory importance.

        Args:
            content: Memory content to score
            user_provided: User-provided importance (override)

        Returns:
            float: Importance score 0.0 to 1.0
        """
        if user_provided is not None:
            return min(1.0, max(0.0, user_provided))

        if not self.openai_client:
            return 0.5

        return self._llm_score(content)

    def _llm_score(self, content: str) -> float:
        """Use LLM to score importance."""
        prompt = f"""Analyze this memory and assign an importance score from 0.0 to 1.0.

Score guide:
- 0.1: Greetings, small talk, casual acknowledgments
- 0.3: Casual info, preferences mentioned in passing
- 0.5: Regular conversation, non-critical facts
- 0.7: Important preferences, decisions, commitments
- 0.9: Critical info, personal data, security-related
- 1.0: Never forget - API keys, passwords, identity

Memory: "{content}"

Output ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10,
            )

            result = response.choices[0].message.content.strip()
            score = float(result)
            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.error(f"LLM importance scoring failed: {e}")
            return 0.5

    def score_batch(self, contents: list) -> list:
        """Score multiple memories at once."""
        if not self.openai_client:
            return [0.5] * len(contents)

        prompt = f"""Analyze these memories and assign importance scores (0.0 to 1.0).
Return a JSON array of numbers.

Memories:
{chr(10).join(f"{i + 1}. {mem}" for i, mem in enumerate(contents))}

Output ONLY JSON array."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            scores = json.loads(response.choices[0].message.content)
            return [min(1.0, max(0.0, float(s))) for s in scores[: len(contents)]]

        except Exception as e:
            logger.error(f"LLM batch scoring failed: {e}")
            return [0.5] * len(contents)


_scorer = None


def get_importance_scorer():
    global _scorer
    if _scorer is None:
        _scorer = ImportanceScorer()
    return _scorer
