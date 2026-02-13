"""
Job Analyzer – LLM-powered analysis of individual Upwork job postings.

Takes raw job data from the database and produces structured analysis
with scores, risk flags, effort estimates, and action recommendations.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from .client import LLMClient, LLMError
from .prompts import JOB_ANALYSIS_SYSTEM, JOB_ANALYSIS_PROMPT
from .profile_config import PROFILE, get_skills_for_matching, get_avoid_keywords

logger = logging.getLogger("upwork-dna.llm.analyzer")


@dataclass
class JobAnalysis:
    """Structured output from LLM job analysis."""
    job_key: str
    title: str
    summary_1line: str = ""
    scope_clarity: float = 0.0
    budget_fit: float = 0.0
    technical_fit: float = 0.0
    risk_flags: list[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0
    competition_signal: str = "medium"
    client_quality: float = 0.0
    recommended_action: str = "WATCH"  # APPLY | SKIP | WATCH
    recommended_bid: str = ""
    opening_hook: str = ""
    questions_to_ask: list[str] = field(default_factory=list)
    deliverables_list: list[str] = field(default_factory=list)
    reasoning: str = ""
    composite_score: float = 0.0
    llm_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_llm_response(cls, job_key: str, title: str, data: dict) -> "JobAnalysis":
        """Build JobAnalysis from LLM JSON response with validation."""
        analysis = cls(
            job_key=job_key,
            title=title,
            summary_1line=str(data.get("summary_1line", "")),
            scope_clarity=_clamp(data.get("scope_clarity", 0.0)),
            budget_fit=_clamp(data.get("budget_fit", 0.0)),
            technical_fit=_clamp(data.get("technical_fit", 0.0)),
            risk_flags=data.get("risk_flags", []) or [],
            estimated_effort_hours=max(0.0, float(data.get("estimated_effort_hours", 0))),
            competition_signal=data.get("competition_signal", "medium"),
            client_quality=_clamp(data.get("client_quality", 0.0)),
            recommended_action=data.get("recommended_action", "WATCH").upper(),
            recommended_bid=str(data.get("recommended_bid", "")),
            opening_hook=str(data.get("opening_hook", "")),
            questions_to_ask=data.get("questions_to_ask", []) or [],
            deliverables_list=data.get("deliverables_list", []) or [],
            reasoning=str(data.get("reasoning", "")),
        )

        # Validate action
        if analysis.recommended_action not in ("APPLY", "SKIP", "WATCH"):
            analysis.recommended_action = "WATCH"

        # Validate competition signal
        if analysis.competition_signal not in ("low", "medium", "high", "extreme"):
            analysis.competition_signal = "medium"

        # Compute composite score
        analysis.composite_score = _compute_composite(analysis)

        return analysis

    @classmethod
    def error_result(cls, job_key: str, title: str, error: str) -> "JobAnalysis":
        """Return a minimal analysis when LLM fails."""
        return cls(job_key=job_key, title=title, llm_error=error)


def _clamp(v, lo=0.0, hi=1.0) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _compute_composite(a: JobAnalysis) -> float:
    """
    Composite score formula:
      0.35 * technical_fit
    + 0.25 * budget_fit
    + 0.15 * scope_clarity
    + 0.15 * competition_bonus
    + 0.10 * client_quality
    """
    comp_map = {"low": 1.0, "medium": 0.6, "high": 0.3, "extreme": 0.1}
    competition_bonus = comp_map.get(a.competition_signal, 0.5)

    score = (
        0.35 * a.technical_fit
        + 0.25 * a.budget_fit
        + 0.15 * a.scope_clarity
        + 0.15 * competition_bonus
        + 0.10 * a.client_quality
    )
    return round(score, 4)


class JobAnalyzer:
    """
    Analyzes Upwork jobs using LLM.

    Usage:
        analyzer = JobAnalyzer(client)
        result = await analyzer.analyze(job_dict)
        batch = await analyzer.analyze_batch([job1, job2, ...])
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def analyze(self, job: dict) -> JobAnalysis:
        """
        Analyze a single job posting.

        Args:
            job: Dict with keys: job_key, title, description, budget, budget_value,
                 client_spend, payment_verified, proposals, skills, keyword
        """
        job_key = job.get("job_key", "unknown")
        title = job.get("title", "Untitled")

        try:
            prompt = JOB_ANALYSIS_PROMPT.format(
                title=title,
                budget=job.get("budget", "Not specified"),
                client_spend=job.get("client_spend", 0) or 0,
                payment_verified=job.get("payment_verified", False),
                proposals=job.get("proposals", "Unknown"),
                skills=job.get("skills", "None listed"),
                keyword=job.get("keyword", ""),
                description=(job.get("description", "") or "")[:3000],  # Truncate long descriptions
            )

            data = await self.client.chat_json(
                prompt,
                system=JOB_ANALYSIS_SYSTEM,
                temperature=0.2,
            )

            analysis = JobAnalysis.from_llm_response(job_key, title, data)

            # Apply hard-skip rules on top of LLM recommendation
            analysis = self._apply_hard_rules(analysis, job)

            logger.info(
                f"Job analyzed: {job_key} → {analysis.recommended_action} "
                f"(composite={analysis.composite_score:.2f})"
            )
            return analysis

        except LLMError as e:
            logger.error(f"LLM error analyzing job {job_key}: {e}")
            return JobAnalysis.error_result(job_key, title, str(e))
        except Exception as e:
            logger.error(f"Unexpected error analyzing job {job_key}: {e}")
            return JobAnalysis.error_result(job_key, title, str(e))

    async def analyze_batch(self, jobs: list[dict], max_concurrent: int = 3) -> list[JobAnalysis]:
        """
        Analyze multiple jobs. Processes sequentially to avoid overwhelming glm-bridge.
        """
        import asyncio

        results = []
        for i, job in enumerate(jobs):
            logger.info(f"Analyzing job {i+1}/{len(jobs)}: {job.get('job_key', '?')}")
            result = await self.analyze(job)
            results.append(result)

            # Small delay between requests to not overload glm-bridge
            if i < len(jobs) - 1:
                await asyncio.sleep(1.0)

        # Sort by composite score descending
        results.sort(key=lambda a: a.composite_score, reverse=True)
        return results

    @staticmethod
    def _apply_hard_rules(analysis: JobAnalysis, job: dict) -> JobAnalysis:
        """
        Apply deterministic hard-skip rules that override LLM judgment.
        These are non-negotiable filters + profile-based adjustments.
        """
        import re as _re

        budget_val = job.get("budget_value") or 0
        proposals_str = str(job.get("proposals", "0"))
        # Parse first number only — "20 to 50" → 20, "50+" → 50
        _m = _re.search(r"\d+", proposals_str)
        proposals_num = int(_m.group()) if _m else 0

        # --- Combine job text for keyword matching ---
        job_text = " ".join([
            job.get("title", ""),
            job.get("description", "") or "",
            job.get("skills", "") or "",
        ]).lower()

        # --- Profile-based skill relevance boost ---
        matched_skills = get_skills_for_matching()
        skill_hits = sum(1 for skill in matched_skills if skill.lower() in job_text)
        skill_ratio = skill_hits / max(len(matched_skills), 1)

        # Boost composite for strong skill matches
        if skill_ratio >= 0.3:
            analysis.composite_score = min(1.0, analysis.composite_score + 0.08)
            analysis.risk_flags.append(f"PROFILE_BOOST: {skill_hits} skill matches")
        elif skill_ratio >= 0.15:
            analysis.composite_score = min(1.0, analysis.composite_score + 0.04)
            analysis.risk_flags.append(f"PROFILE_MATCH: {skill_hits} skill matches")

        # --- Avoid keyword detection ---
        avoid_kws = get_avoid_keywords()
        avoid_hits = [kw for kw in avoid_kws if kw.lower() in job_text]
        if avoid_hits:
            analysis.risk_flags.append(f"AVOID_KEYWORD: {', '.join(avoid_hits)}")
            analysis.composite_score = max(0.0, analysis.composite_score - 0.10)

        # --- Hard SKIP: budget < $10 with effort > 3h ---
        if budget_val > 0 and budget_val < 10 and analysis.estimated_effort_hours > 3:
            analysis.recommended_action = "SKIP"
            analysis.risk_flags.append("HARD_RULE: budget < $10 with 3h+ effort")

        # --- Competition graduated penalties (based on first number in proposals) ---
        if proposals_num >= 50:
            # 50+ truly extreme — hard SKIP
            analysis.recommended_action = "SKIP"
            analysis.risk_flags.append(f"HARD_RULE: {proposals_num}+ proposals, extreme competition")
        elif proposals_num >= 30:
            # 30-49: significant penalty, downgrade APPLY→WATCH unless strong match
            analysis.composite_score = max(0.0, analysis.composite_score - 0.10)
            analysis.risk_flags.append(f"COMPETITION: {proposals_num} proposals, high competition")
            if analysis.recommended_action == "APPLY" and skill_ratio < 0.2:
                analysis.recommended_action = "WATCH"
        elif proposals_num >= 15:
            # 15-29: minor penalty
            analysis.composite_score = max(0.0, analysis.composite_score - 0.05)
            analysis.risk_flags.append(f"COMPETITION: {proposals_num} proposals, moderate competition")

        # --- Hard SKIP: unverified payment + no spend + budget < $50 ---
        if not job.get("payment_verified") and (job.get("client_spend") or 0) == 0 and budget_val < 50:
            if analysis.recommended_action == "APPLY":
                analysis.recommended_action = "WATCH"
                analysis.risk_flags.append("CAUTION: unverified, no spend, low budget")

        # --- Early-stage strategy: prefer low-competition verified jobs ---
        if PROFILE.get("total_upwork_jobs", 0) < 5:
            if proposals_num <= 10 and job.get("payment_verified") and skill_ratio >= 0.15:
                analysis.composite_score = min(1.0, analysis.composite_score + 0.08)
                analysis.risk_flags.append("STRATEGY: ideal early-stage job (low comp, verified, skill match)")

        # --- Cap composite for SKIP actions (but not too aggressively) ---
        if analysis.recommended_action == "SKIP" and analysis.composite_score > 0.45:
            analysis.composite_score = 0.40

        return analysis
