"""
Proposal Writer – LLM-powered cover letter generation for Upwork jobs.

Takes a JobAnalysis result and produces a personalized, compelling proposal.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from .client import LLMClient, LLMError
from .job_analyzer import JobAnalysis
from .prompts import get_proposal_system, get_proposal_prompt

logger = logging.getLogger("upwork-dna.llm.proposal")


@dataclass
class Proposal:
    """Structured proposal output."""
    job_key: str
    title: str = ""
    cover_letter: str = ""
    bid_amount: str = ""
    bid_rationale: str = ""
    key_differentiators: list[str] = field(default_factory=list)
    estimated_timeline: str = ""
    call_to_action: str = ""
    llm_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_llm_response(cls, job_key: str, title: str, data: dict) -> "Proposal":
        return cls(
            job_key=job_key,
            title=title,
            cover_letter=str(data.get("cover_letter", "")),
            bid_amount=str(data.get("bid_amount", "")),
            bid_rationale=str(data.get("bid_rationale", "")),
            key_differentiators=data.get("key_differentiators", []) or [],
            estimated_timeline=str(data.get("estimated_timeline", "")),
            call_to_action=str(data.get("call_to_action", "")),
        )

    @classmethod
    def error_result(cls, job_key: str, title: str, error: str) -> "Proposal":
        return cls(job_key=job_key, title=title, llm_error=error)


class ProposalWriter:
    """
    Generates personalized Upwork proposals using LLM.

    Usage:
        writer = ProposalWriter(client)
        proposal = await writer.generate(analysis, job_dict)
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self.client = client or LLMClient()

    async def generate(self, analysis: JobAnalysis, job: dict) -> Proposal:
        """
        Generate a proposal for a job based on its analysis.

        Args:
            analysis: JobAnalysis result from JobAnalyzer
            job: Raw job dict with title, description, etc.
        """
        job_key = job.get("job_key", analysis.job_key)
        title = job.get("title", analysis.title)

        try:
            # Build analysis summary for prompt
            analysis_summary = {
                "summary": analysis.summary_1line,
                "technical_fit": analysis.technical_fit,
                "budget_fit": analysis.budget_fit,
                "scope_clarity": analysis.scope_clarity,
                "competition": analysis.competition_signal,
                "effort_hours": analysis.estimated_effort_hours,
                "opening_hook": analysis.opening_hook,
                "questions": analysis.questions_to_ask,
                "deliverables": analysis.deliverables_list,
                "risk_flags": analysis.risk_flags,
                "recommended_bid": analysis.recommended_bid,
            }

            prompt = get_proposal_prompt().format(
                analysis_json=json.dumps(analysis_summary, indent=2),
                title=title,
                description=(job.get("description", "") or "")[:3000],
            )

            data = await self.client.chat_json(
                prompt,
                system=get_proposal_system(),
                temperature=0.5,  # Slightly creative for proposals
                max_tokens=2048,
            )

            proposal = Proposal.from_llm_response(job_key, title, data)

            logger.info(f"Proposal generated for: {job_key} | Bid: {proposal.bid_amount}")
            return proposal

        except LLMError as e:
            logger.error(f"LLM error generating proposal for {job_key}: {e}")
            return Proposal.error_result(job_key, title, str(e))
        except Exception as e:
            logger.error(f"Unexpected error generating proposal for {job_key}: {e}")
            return Proposal.error_result(job_key, title, str(e))
