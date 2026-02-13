"""
Decision Engine – Prioritizes analyzed jobs into HOT / WARM / COLD buckets.

Takes a list of JobAnalysis objects and produces a ranked action queue
with time-sensitivity labels and HOT job alerts.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from .client import LLMClient, LLMError
from .job_analyzer import JobAnalysis
from .prompts import BATCH_RANK_SYSTEM, BATCH_RANK_PROMPT

logger = logging.getLogger("upwork-dna.llm.decision")


@dataclass
class JobDecision:
    """Single job decision with priority and context."""
    job_key: str
    title: str = ""
    composite_score: float = 0.0
    recommended_action: str = "WATCH"
    priority_rank: int = 0
    priority_label: str = "COLD"  # HOT | WARM | COLD
    time_sensitivity: str = "normal"  # urgent | normal | flexible
    reason: str = ""
    analysis: Optional[dict] = None  # Full analysis dict for reference

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DecisionBatch:
    """Complete decision output for a batch of jobs."""
    timestamp: str = ""
    total_jobs: int = 0
    hot_count: int = 0
    warm_count: int = 0
    cold_count: int = 0
    skip_count: int = 0
    decisions: list[JobDecision] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "total_jobs": self.total_jobs,
            "hot_count": self.hot_count,
            "warm_count": self.warm_count,
            "cold_count": self.cold_count,
            "skip_count": self.skip_count,
            "decisions": [d.to_dict() for d in self.decisions],
        }

    @property
    def hot_jobs(self) -> list[JobDecision]:
        return [d for d in self.decisions if d.priority_label == "HOT"]

    @property
    def warm_jobs(self) -> list[JobDecision]:
        return [d for d in self.decisions if d.priority_label == "WARM"]


class DecisionEngine:
    """
    Ranks and prioritizes job analyses.

    Two modes:
    1. Rule-based (fast, no LLM call) – uses composite scores from JobAnalysis
    2. LLM-enhanced (optional) – sends batch to LLM for strategic ranking

    Usage:
        engine = DecisionEngine(client)
        batch = await engine.decide(analyses)
        for hot in batch.hot_jobs:
            print(f"🔥 {hot.title} — {hot.reason}")
    """

    def __init__(self, client: Optional[LLMClient] = None, use_llm_ranking: bool = False):
        self.client = client
        self.use_llm_ranking = use_llm_ranking

    async def decide(self, analyses: list[JobAnalysis]) -> DecisionBatch:
        """
        Process a list of job analyses and produce prioritized decisions.
        """
        if not analyses:
            return DecisionBatch(timestamp=datetime.utcnow().isoformat(), total_jobs=0)

        # Step 1: Apply rule-based classification
        decisions = [self._classify(a) for a in analyses]

        # Step 2: (Optional) LLM re-ranking for APPLY/WATCH jobs
        if self.use_llm_ranking and self.client:
            apply_watch = [d for d in decisions if d.recommended_action != "SKIP"]
            if len(apply_watch) >= 2:
                try:
                    decisions = await self._llm_rerank(decisions, analyses)
                except LLMError as e:
                    logger.warning(f"LLM re-ranking failed, using rule-based: {e}")

        # Step 3: Sort by priority
        priority_order = {"HOT": 0, "WARM": 1, "COLD": 2}
        decisions.sort(
            key=lambda d: (priority_order.get(d.priority_label, 3), -d.composite_score)
        )

        # Assign ranks
        for i, d in enumerate(decisions):
            d.priority_rank = i + 1

        # Build batch
        batch = DecisionBatch(
            timestamp=datetime.utcnow().isoformat(),
            total_jobs=len(decisions),
            hot_count=sum(1 for d in decisions if d.priority_label == "HOT"),
            warm_count=sum(1 for d in decisions if d.priority_label == "WARM"),
            cold_count=sum(1 for d in decisions if d.priority_label == "COLD"),
            skip_count=sum(1 for d in decisions if d.recommended_action == "SKIP"),
            decisions=decisions,
        )

        logger.info(
            f"Decision batch: {batch.total_jobs} jobs → "
            f"🔥 {batch.hot_count} HOT, ☀️ {batch.warm_count} WARM, "
            f"❄️ {batch.cold_count} COLD, ⏭️ {batch.skip_count} SKIP"
        )

        return batch

    def _classify(self, analysis: JobAnalysis) -> JobDecision:
        """Rule-based classification into HOT/WARM/COLD."""
        score = analysis.composite_score
        action = analysis.recommended_action

        if action == "SKIP":
            label = "COLD"
            sensitivity = "flexible"
            reason = f"SKIP: {'; '.join(analysis.risk_flags[:2])}" if analysis.risk_flags else "Low match"
        elif action == "APPLY" and score >= 0.70:
            label = "HOT"
            sensitivity = "urgent"
            reason = f"High match ({score:.0%}): {analysis.summary_1line}"
        elif action == "APPLY" and score >= 0.55:
            label = "WARM"
            sensitivity = "normal"
            reason = f"Good match ({score:.0%}): {analysis.summary_1line}"
        elif action == "WATCH":
            label = "WARM" if score >= 0.50 else "COLD"
            sensitivity = "normal" if score >= 0.50 else "flexible"
            reason = f"Watch ({score:.0%}): {analysis.reasoning[:100]}"
        else:
            label = "COLD"
            sensitivity = "flexible"
            reason = f"Low score ({score:.0%})"

        # Boost: low competition + high technical fit → upgrade
        if (
            analysis.competition_signal == "low"
            and analysis.technical_fit >= 0.7
            and label != "HOT"
            and action != "SKIP"
        ):
            label = "HOT" if label == "WARM" else "WARM"
            sensitivity = "urgent" if label == "HOT" else "normal"
            reason = f"Low competition opportunity! {reason}"

        return JobDecision(
            job_key=analysis.job_key,
            title=analysis.title,
            composite_score=score,
            recommended_action=action,
            priority_label=label,
            time_sensitivity=sensitivity,
            reason=reason,
            analysis=analysis.to_dict(),
        )

    async def _llm_rerank(
        self, decisions: list[JobDecision], analyses: list[JobAnalysis]
    ) -> list[JobDecision]:
        """Use LLM to re-rank non-SKIP jobs for strategic prioritization."""
        # Only send APPLY/WATCH jobs to LLM
        valid = [d for d in decisions if d.recommended_action != "SKIP"]
        skipped = [d for d in decisions if d.recommended_action == "SKIP"]

        # Build compact analysis list for LLM
        analyses_for_llm = []
        analysis_map = {a.job_key: a for a in analyses}
        for d in valid:
            a = analysis_map.get(d.job_key)
            if a:
                analyses_for_llm.append({
                    "job_key": a.job_key,
                    "title": a.title,
                    "summary": a.summary_1line,
                    "composite_score": a.composite_score,
                    "technical_fit": a.technical_fit,
                    "budget_fit": a.budget_fit,
                    "competition": a.competition_signal,
                    "estimated_hours": a.estimated_effort_hours,
                    "action": a.recommended_action,
                })

        prompt = BATCH_RANK_PROMPT.format(
            analyses_json=json.dumps(analyses_for_llm, indent=2)
        )

        result = await self.client.chat_json(
            prompt,
            system=BATCH_RANK_SYSTEM,
            temperature=0.3,
        )

        # Parse LLM ranking
        rankings = result if isinstance(result, list) else result.get("rankings", [])
        rank_map = {r["job_key"]: r for r in rankings if "job_key" in r}

        # Update decisions with LLM rankings
        for d in valid:
            if d.job_key in rank_map:
                r = rank_map[d.job_key]
                d.priority_label = r.get("priority_label", d.priority_label)
                d.time_sensitivity = r.get("time_sensitivity", d.time_sensitivity)
                if r.get("reason"):
                    d.reason = r["reason"]

        return valid + skipped
