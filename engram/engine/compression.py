# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Neurall. All rights reserved.

"""Memory compression engine - distills raw episodes into semantic facts."""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CompressionEngine:
    """Compresses raw episodic memories into distilled semantic facts."""

    def __init__(self, openai_client=None):
        self.openai_client = openai_client

    def compress_episodes(
        self, user_id: str, min_count: int = 10, max_facts: int = 5
    ) -> dict:
        """Compress episodic memories into semantic facts."""
        from database.connection import get_connection
        from engine.embeddings import embed

        conn = get_connection()
        cursor = conn.cursor()

        # Get episodic memories not yet compressed
        cursor.execute(
            """
            SELECT id, content, created_at, access_count
            FROM episodic_memory
            WHERE user_id = ? AND (content IS NULL OR content != '[COMPRESSED]')
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (user_id, min_count * 2),
        )

        episodes = cursor.fetchall()

        if len(episodes) < min_count:
            return {
                "compressed": False,
                "reason": f"Only {len(episodes)} episodes, need {min_count}",
                "episodes_found": len(episodes),
            }

        episodes_texts = [ep["content"] for ep in episodes]

        # Use LLM or simple compression
        if self.openai_client:
            facts = self._llm_compress(episodes_texts, max_facts)
        else:
            facts = self._simple_compress(episodes_texts, max_facts)

        # Create semantic memories from facts
        created_facts = []
        for fact_content in facts:
            cursor.execute(
                """
                SELECT id FROM semantic_memory
                WHERE user_id = ? AND content = ?
            """,
                (user_id, fact_content),
            )

            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE semantic_memory
                    SET salience = MIN(1.0, salience + 0.1),
                        updated_at = datetime('now')
                    WHERE id = ?
                """,
                    (existing["id"],),
                )
            else:
                try:
                    embedding = embed(fact_content)
                    emb_json = json.dumps(embedding)
                except:
                    emb_json = "[]"

                cursor.execute(
                    """
                    INSERT INTO semantic_memory (
                        id, user_id, content, embedding, salience,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                    (
                        f"sem_{datetime.now().timestamp()}",
                        user_id,
                        fact_content,
                        emb_json,
                        0.8,
                    ),
                )
                created_facts.append(fact_content)

        # Mark episodes as compressed
        episode_ids = [ep["id"] for ep in episodes[:min_count]]
        if episode_ids:
            placeholders = ",".join("?" * len(episode_ids))
            cursor.execute(
                f"""
                UPDATE episodic_memory
                SET content = '[COMPRESSED] ' || COALESCE(content, ''),
                    is_compressed = 1
                WHERE id IN ({placeholders})
            """,
                episode_ids,
            )

        conn.commit()

        return {
            "compressed": True,
            "episodes_processed": min(len(episodes), min_count),
            "facts_created": len(created_facts),
            "facts": created_facts,
            "reduction": f"{min(len(episodes), min_count)} ep -> {len(created_facts)} facts",
        }

    def _llm_compress(self, episodes: list, max_facts: int) -> list:
        """Use LLM to distill facts."""
        if not self.openai_client:
            return self._simple_compress(episodes, max_facts)

        prompt = f"""Analyze these episodes and distill into {max_facts} facts.
Episodes: {chr(10).join(f"- {ep}" for ep in episodes[:20])}
Output ONLY JSON array."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            facts = json.loads(response.choices[0].message.content)
            return facts[:max_facts] if isinstance(facts, list) else []
        except Exception as e:
            logger.error(f"LLM compression failed: {e}")
            return self._simple_compress(episodes, max_facts)

    def _simple_compress(self, episodes: list, max_facts: int) -> list:
        """Simple keyword-based compression."""
        keywords = {}
        stop_words = {
            "user",
            "that",
            "this",
            "with",
            "from",
            "have",
            "been",
            "will",
            "what",
            "when",
        }

        for ep in episodes[:20]:
            words = ep.lower().split()
            for word in words:
                if len(word) > 4 and word not in stop_words:
                    keywords[word] = keywords.get(word, 0) + 1

        top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[
            :max_facts
        ]

        facts = []
        for kw, count in top_keywords:
            if count >= 2:
                facts.append(f"User frequently discusses '{kw}' ({count} times)")

        if len(facts) < 3:
            facts.extend(
                [
                    "User has ongoing conversations with the AI assistant",
                    "User prefers getting direct responses",
                ]
            )

        return facts[:max_facts]

    def get_compression_stats(self, user_id: str) -> dict:
        """Get compression statistics."""
        from database.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as total,
                SUM(CASE WHEN is_compressed = 1 THEN 1 ELSE 0 END) as compressed
            FROM episodic_memory WHERE user_id = ?
        """,
            (user_id,),
        )

        stats = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) FROM semantic_memory WHERE user_id = ?", (user_id,)
        )
        semantic_count = cursor.fetchone()["COUNT(*)"]

        total_ep = stats["total"] or 0
        return {
            "episodes_total": total_ep,
            "episodes_compressed": stats["compressed"] or 0,
            "semantic_facts": semantic_count,
            "compression_ratio": f"{((stats['compressed'] or 0) / max(total_ep, 1)) * 100:.1f}%",
        }


_compression_engine = None


def get_compression_engine():
    global _compression_engine
    if _compression_engine is None:
        _compression_engine = CompressionEngine()
    return _compression_engine
