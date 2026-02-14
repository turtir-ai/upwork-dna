"""
Keyword Discoverer – LLM-powered keyword suggestion for Upwork market exploration.

Analyzes current keyword metrics and suggests new, emerging search terms.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from .client import LLMClient, LLMError
from .prompts import get_keyword_discovery_system, get_keyword_discovery_prompt

logger = logging.getLogger("upwork-dna.llm.keywords")


@dataclass
class KeywordSuggestion:
    """A suggested new keyword to track."""
    keyword: str
    rationale: str = ""
    expected_competition: str = "medium"
    relevance_to_skills: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class KeywordDiscoverer:
    """
    Suggests new keywords to track based on current market data.

    Usage:
        discoverer = KeywordDiscoverer(client)
        suggestions = await discoverer.suggest(current_metrics)
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def suggest(self, current_metrics: list[dict]) -> list[KeywordSuggestion]:
        """
        Suggest new keywords based on current keyword metrics.

        Args:
            current_metrics: List of dicts with keyword, demand, supply, gap_ratio, opportunity_score
        """
        try:
            # Compact metrics for prompt
            compact = [
                {
                    "keyword": m.get("keyword", ""),
                    "demand": m.get("demand", 0),
                    "supply": m.get("supply", 0),
                    "gap_ratio": round(m.get("gap_ratio", 0), 2),
                    "score": round(m.get("opportunity_score", 0), 2),
                }
                for m in current_metrics
            ]

            prompt = get_keyword_discovery_prompt().format(
                keyword_metrics_json=json.dumps(compact, indent=2)
            )

            data = await self.client.chat_json(
                prompt,
                system=get_keyword_discovery_system(),
                temperature=0.6,  # More creative for discovery
            )

            suggestions_raw = data if isinstance(data, list) else data.get("suggestions", [])

            suggestions = []
            existing_kws = {m.get("keyword", "").lower() for m in current_metrics}
            for item in suggestions_raw:
                kw = item.get("keyword", "").strip()
                if not kw or kw.lower() in existing_kws:
                    continue
                suggestions.append(KeywordSuggestion(
                    keyword=kw,
                    rationale=item.get("rationale", ""),
                    expected_competition=item.get("expected_competition", "medium"),
                    relevance_to_skills=min(1.0, max(0.0, float(item.get("relevance_to_skills", 0.5)))),
                ))

            logger.info(f"Keyword discovery: {len(suggestions)} new suggestions")
            return suggestions

        except LLMError as e:
            logger.error(f"LLM error in keyword discovery: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in keyword discovery: {e}")
            return []
