"""
Keyword Strategy Advisor – LLM-powered keyword optimization for the freelancer's profile.

Analyzes current keyword performance and recommends changes (keep, modify, drop, add)
based on profile fit, market data, and reputation-building strategy.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from .client import LLMClient, LLMError
from .prompts import KEYWORD_STRATEGY_SYSTEM, KEYWORD_STRATEGY_PROMPT
from .profile_config import PROFILE, get_ideal_keywords, get_avoid_keywords

logger = logging.getLogger("upwork-dna.llm.keyword_strategy")


@dataclass
class KeywordStrategyResult:
    """Structured output from keyword strategy analysis."""
    keep: list[str] = field(default_factory=list)
    modify: list[dict] = field(default_factory=list)      # [{from, to, reason}]
    drop: list[dict] = field(default_factory=list)         # [{keyword, reason}]
    add: list[dict] = field(default_factory=list)          # [{keyword, reason, expected_competition}]
    overall_strategy: str = ""
    llm_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_llm_response(cls, data: dict) -> "KeywordStrategyResult":
        return cls(
            keep=data.get("keep", []) or [],
            modify=data.get("modify", []) or [],
            drop=data.get("drop", []) or [],
            add=data.get("add", []) or [],
            overall_strategy=str(data.get("overall_strategy", "")),
        )

    @classmethod
    def error_result(cls, error: str) -> "KeywordStrategyResult":
        return cls(llm_error=error)


@dataclass
class ProfileFitScore:
    """Quick profile-fit assessment for a keyword without LLM."""
    keyword: str
    fit_score: float = 0.0     # 0-1
    fit_reason: str = ""
    is_ideal: bool = False
    is_avoid: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class KeywordStrategyAdvisor:
    """
    Advises on keyword strategy based on profile and market data.

    Usage:
        advisor = KeywordStrategyAdvisor(client)
        
        # Quick profile-fit scoring (no LLM needed)
        fits = advisor.score_keywords_fit(current_metrics)
        
        # Full LLM-powered strategy analysis
        strategy = await advisor.analyze_strategy(current_metrics)
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()
        self._ideal_kws = {kw.lower() for kw in get_ideal_keywords()}
        self._avoid_kws = {kw.lower() for kw in get_avoid_keywords()}
        self._all_skills = {s.lower() for s in PROFILE.get("core_skills", []) + PROFILE.get("secondary_skills", [])}

    def score_keywords_fit(self, metrics: list[dict]) -> list[ProfileFitScore]:
        """
        Score each keyword for profile fit WITHOUT using LLM.
        Fast, deterministic, good for dashboard display.
        """
        results = []
        for m in metrics:
            kw = m.get("keyword", "").strip()
            kw_lower = kw.lower()
            kw_words = set(kw_lower.split())

            # Check ideal/avoid
            is_ideal = any(ideal in kw_lower for ideal in self._ideal_kws)
            is_avoid = any(avoid in kw_lower for avoid in self._avoid_kws)

            # Score based on skill word overlap
            skill_overlap = sum(1 for skill in self._all_skills if skill in kw_lower)
            ideal_overlap = sum(1 for ideal in self._ideal_kws if ideal in kw_lower)

            fit = 0.0
            reasons = []

            if is_avoid:
                fit = max(0.0, 0.2 - 0.1 * len([a for a in self._avoid_kws if a in kw_lower]))
                reasons.append("matches avoid list")
            elif is_ideal:
                fit = min(1.0, 0.7 + 0.1 * ideal_overlap)
                reasons.append("ideal keyword")
            elif skill_overlap > 0:
                fit = min(1.0, 0.4 + 0.15 * skill_overlap)
                reasons.append(f"{skill_overlap} skill matches")
            else:
                fit = 0.3
                reasons.append("no direct skill match")

            # Bonus for gap_ratio (market opportunity)
            gap = m.get("gap_ratio", 0) or 0
            if gap > 2.0:
                fit = min(1.0, fit + 0.1)
                reasons.append("high market gap")

            results.append(ProfileFitScore(
                keyword=kw,
                fit_score=round(fit, 2),
                fit_reason="; ".join(reasons),
                is_ideal=is_ideal,
                is_avoid=is_avoid,
            ))

        results.sort(key=lambda x: x.fit_score, reverse=True)
        return results

    async def analyze_strategy(self, current_metrics: list[dict]) -> KeywordStrategyResult:
        """
        Full LLM-powered keyword strategy analysis.
        Recommends which keywords to keep, modify, drop, or add.
        """
        try:
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

            prompt = KEYWORD_STRATEGY_PROMPT.format(
                keyword_metrics_json=json.dumps(compact, indent=2)
            )

            data = await self.client.chat_json(
                prompt,
                system=KEYWORD_STRATEGY_SYSTEM,
                temperature=0.3,
            )

            result = KeywordStrategyResult.from_llm_response(data)
            logger.info(
                f"Keyword strategy: keep={len(result.keep)}, "
                f"modify={len(result.modify)}, drop={len(result.drop)}, add={len(result.add)}"
            )
            return result

        except LLMError as e:
            logger.error(f"LLM error in keyword strategy: {e}")
            return KeywordStrategyResult.error_result(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in keyword strategy: {e}")
            return KeywordStrategyResult.error_result(str(e))
