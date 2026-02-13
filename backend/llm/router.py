"""
LLM API Router – Endpoints for AI-powered job analysis, decision engine,
proposal generation, and keyword discovery.

Mounted at /v1/llm/* in the main FastAPI app.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, JobRaw, JobOpportunity, ProposalDraft, KeywordMetric
from llm.client import LLMClient, LLMError, LLMConnectionError
from llm.job_analyzer import JobAnalyzer, JobAnalysis
from llm.decision_engine import DecisionEngine, DecisionBatch
from llm.proposal_writer import ProposalWriter
from llm.keyword_discoverer import KeywordDiscoverer
from llm.keyword_strategy import KeywordStrategyAdvisor
from llm.profile_config import PROFILE, get_profile_summary
from llm.notifier import get_notifier

logger = logging.getLogger("upwork-dna.llm.api")

router = APIRouter(prefix="/v1/llm", tags=["LLM Intelligence"])

# ---------------------------------------------------------------------------
# Shared client instance (lazy init)
# ---------------------------------------------------------------------------
_client: Optional[LLMClient] = None


def get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def get_db_session() -> Session:
    return SessionLocal()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    provider: str = ""
    model: str = ""
    error: str = ""


class JobAnalysisResponse(BaseModel):
    job_key: str
    title: str = ""
    summary_1line: str = ""
    scope_clarity: float = 0
    budget_fit: float = 0
    technical_fit: float = 0
    risk_flags: list[str] = []
    estimated_effort_hours: float = 0
    competition_signal: str = "medium"
    client_quality: float = 0
    recommended_action: str = "WATCH"
    recommended_bid: str = ""
    opening_hook: str = ""
    questions_to_ask: list[str] = []
    deliverables_list: list[str] = []
    reasoning: str = ""
    composite_score: float = 0
    llm_error: str = ""


class BatchAnalysisResponse(BaseModel):
    total: int = 0
    analyzed: int = 0
    errors: int = 0
    analyses: list[JobAnalysisResponse] = []


class DecisionResponse(BaseModel):
    timestamp: str = ""
    total_jobs: int = 0
    hot_count: int = 0
    warm_count: int = 0
    cold_count: int = 0
    skip_count: int = 0
    decisions: list[dict] = []


class ProposalResponse(BaseModel):
    job_key: str
    title: str = ""
    cover_letter: str = ""
    bid_amount: str = ""
    bid_rationale: str = ""
    key_differentiators: list[str] = []
    estimated_timeline: str = ""
    call_to_action: str = ""
    llm_error: str = ""


class KeywordSuggestionResponse(BaseModel):
    keyword: str
    rationale: str = ""
    expected_competition: str = "medium"
    relevance_to_skills: float = 0


class HotJobsResponse(BaseModel):
    timestamp: str = ""
    hot_count: int = 0
    hot_jobs: list[dict] = []
    warm_count: int = 0
    warm_jobs: list[dict] = []


class ProfileResponse(BaseModel):
    name: str = ""
    title: str = ""
    hourly_rate: int = 0
    hourly_range: str = ""
    core_skills: list[str] = []
    secondary_skills: list[str] = []
    service_lines: list[str] = []
    portfolio_projects: list[str] = []
    ideal_job_keywords: list[str] = []
    avoid_keywords: list[str] = []
    strategy: dict = {}
    total_upwork_jobs: int = 0
    profile_summary: str = ""


class KeywordFitResponse(BaseModel):
    keyword: str
    fit_score: float = 0.0
    fit_reason: str = ""
    is_ideal: bool = False
    is_avoid: bool = False


class KeywordStrategyResponse(BaseModel):
    keep: list[str] = []
    modify: list[dict] = []
    drop: list[dict] = []
    add: list[dict] = []
    overall_strategy: str = ""
    llm_error: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def llm_health():
    """Check if glm-bridge LLM service is available."""
    client = get_client()
    try:
        h = await client.health()
        return HealthResponse(
            status=h.get("status", "unknown"),
            provider=h.get("provider", ""),
            model=h.get("model", ""),
        )
    except LLMConnectionError as e:
        return HealthResponse(status="unavailable", error=str(e))


@router.post("/analyze-job/{job_key}", response_model=JobAnalysisResponse)
async def analyze_job(job_key: str):
    """
    Analyze a single job posting using LLM.
    Fetches job from database by job_key and returns structured analysis.
    """
    db = get_db_session()
    try:
        job_row = db.query(JobRaw).filter(JobRaw.job_key == job_key).first()
        if not job_row:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_key}")

        job_dict = _row_to_dict(job_row)
        client = get_client()
        analyzer = JobAnalyzer(client)
        result = await analyzer.analyze(job_dict)

        # Persist analysis to job_opportunities table
        _persist_analysis(db, result)

        return JobAnalysisResponse(**result.to_dict())

    except HTTPException:
        raise
    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error analyzing job {job_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/batch-analyze", response_model=BatchAnalysisResponse)
async def batch_analyze(
    limit: int = Query(default=10, ge=1, le=50, description="Max jobs to analyze"),
    keyword: Optional[str] = Query(default=None, description="Filter by keyword"),
    unanalyzed_only: bool = Query(default=True, description="Only analyze jobs not yet scored by LLM"),
):
    """
    Batch-analyze recent jobs using LLM.
    Fetches unanalyzed jobs from database and returns structured analyses.
    """
    db = get_db_session()
    try:
        query = db.query(JobRaw)
        if keyword:
            query = query.filter(JobRaw.keyword == keyword)

        if unanalyzed_only:
            # Get job_keys already LLM-analyzed (check reasons for llm_action)
            import json as _json
            llm_analyzed_keys = set()
            for row in db.query(JobOpportunity).all():
                try:
                    r = _json.loads(row.reasons or "{}")
                    if isinstance(r, dict) and r.get("llm_action"):
                        llm_analyzed_keys.add(row.job_key)
                except Exception:
                    pass

            # Get best candidates by rule-based fit_score (most likely profile match)
            from orchestrator import parse_int_value
            best_opps = db.query(JobOpportunity).order_by(
                JobOpportunity.fit_score.desc()
            ).limit(limit * 10).all()
            
            # Filter for unanalyzed, non-dead jobs
            candidate_keys = []
            for opp in best_opps:
                if opp.job_key in llm_analyzed_keys:
                    continue
                candidate_keys.append(opp.job_key)
                if len(candidate_keys) >= limit * 3:
                    break

            # Fetch raw jobs for candidates
            if keyword:
                all_jobs = query.filter(JobRaw.job_key.in_(candidate_keys)).all()
            else:
                all_jobs = db.query(JobRaw).filter(
                    JobRaw.job_key.in_(candidate_keys)
                ).all()
            
            # Filter out 50+ proposal (dead) jobs
            jobs = []
            for j in all_jobs:
                proposals_num = parse_int_value(j.proposals)
                if proposals_num is not None and proposals_num >= 50:
                    continue
                jobs.append(j)
            
            # Sort by fit_score (best first)
            opp_scores = {opp.job_key: opp.fit_score or 0 for opp in best_opps}
            jobs.sort(key=lambda j: opp_scores.get(j.job_key, 0), reverse=True)
            jobs = jobs[:limit]
        else:
            jobs = query.order_by(JobRaw.scraped_at.desc()).limit(limit).all()

        if not jobs:
            return BatchAnalysisResponse(total=0, analyzed=0, errors=0, analyses=[])

        job_dicts = [_row_to_dict(j) for j in jobs]

        client = get_client()
        analyzer = JobAnalyzer(client)
        results = await analyzer.analyze_batch(job_dicts)

        # Persist all analyses
        for result in results:
            _persist_analysis(db, result)

        analyses = [JobAnalysisResponse(**r.to_dict()) for r in results]
        errors = sum(1 for r in results if r.llm_error)

        return BatchAnalysisResponse(
            total=len(job_dicts),
            analyzed=len(results) - errors,
            errors=errors,
            analyses=analyses,
        )

    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/decide", response_model=DecisionResponse)
async def decide_jobs(
    limit: int = Query(default=20, ge=1, le=100, description="Max jobs to evaluate"),
    keyword: Optional[str] = Query(default=None, description="Filter by keyword"),
    use_llm_ranking: bool = Query(default=False, description="Use LLM for strategic ranking"),
):
    """
    Run the Decision Engine on analyzed jobs.
    Returns prioritized HOT/WARM/COLD queue.
    """
    db = get_db_session()
    try:
        # Get jobs that have been analyzed (have opportunity records)
        query = db.query(JobRaw).join(
            JobOpportunity, JobRaw.job_key == JobOpportunity.job_key
        )
        if keyword:
            query = query.filter(JobRaw.keyword == keyword)

        job_rows = query.order_by(JobOpportunity.fit_score.desc()).limit(limit).all()

        if not job_rows:
            return DecisionResponse(timestamp=datetime.utcnow().isoformat())

        # Re-analyze or use cached analyses
        job_dicts = [_row_to_dict(j) for j in job_rows]
        client = get_client()
        analyzer = JobAnalyzer(client)
        analyses = await analyzer.analyze_batch(job_dicts)

        # Run decision engine
        engine = DecisionEngine(client=client, use_llm_ranking=use_llm_ranking)
        batch = await engine.decide(analyses)

        # Trigger HOT/WARM notifications
        notifier = get_notifier()
        await notifier.notify_batch(batch.to_dict()["decisions"])

        return DecisionResponse(**batch.to_dict())

    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error in decision engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/hot", response_model=HotJobsResponse)
async def hot_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    keyword: Optional[str] = Query(default=None),
):
    """
    Quick endpoint: Get HOT and WARM jobs from the latest decision batch.
    This is a lightweight version of /decide that uses cached opportunity scores.
    """
    db = get_db_session()
    try:
        query = db.query(JobOpportunity).filter(JobOpportunity.apply_now == True)
        if keyword:
            query = query.filter(JobOpportunity.keyword == keyword)

        opportunities = query.order_by(
            JobOpportunity.fit_score.desc()
        ).limit(limit).all()

        hot = []
        warm = []
        for opp in opportunities:
            item = {
                "job_key": opp.job_key,
                "title": opp.title,
                "keyword": opp.keyword,
                "opportunity_score": opp.opportunity_score,
                "safety_score": opp.safety_score,
                "fit_score": opp.fit_score,
                "reasons": json.loads(opp.reasons) if opp.reasons else [],
            }
            if opp.fit_score >= 70:
                hot.append(item)
            else:
                warm.append(item)

        return HotJobsResponse(
            timestamp=datetime.utcnow().isoformat(),
            hot_count=len(hot),
            hot_jobs=hot,
            warm_count=len(warm),
            warm_jobs=warm,
        )
    finally:
        db.close()


@router.post("/generate-proposal/{job_key}", response_model=ProposalResponse)
async def generate_proposal(job_key: str):
    """
    Generate a personalized Upwork proposal for a specific job.
    Requires the job to be analyzed first (or analyzes it automatically).
    """
    db = get_db_session()
    try:
        job_row = db.query(JobRaw).filter(JobRaw.job_key == job_key).first()
        if not job_row:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_key}")

        job_dict = _row_to_dict(job_row)
        client = get_client()

        # First analyze the job
        analyzer = JobAnalyzer(client)
        analysis = await analyzer.analyze(job_dict)

        if analysis.recommended_action == "SKIP":
            logger.warning(f"Generating proposal for SKIP job: {job_key}")

        # Generate proposal
        writer = ProposalWriter(client)
        proposal = await writer.generate(analysis, job_dict)

        # Persist proposal draft
        _persist_proposal(db, proposal)

        return ProposalResponse(**proposal.to_dict())

    except HTTPException:
        raise
    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error generating proposal for {job_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/discover-keywords", response_model=list[KeywordSuggestionResponse])
async def discover_keywords():
    """
    Discover new keyword suggestions based on current market data.
    """
    db = get_db_session()
    try:
        metrics = db.query(KeywordMetric).order_by(
            KeywordMetric.opportunity_score.desc()
        ).limit(30).all()

        metrics_dicts = [
            {
                "keyword": m.keyword,
                "demand": m.demand,
                "supply": m.supply,
                "gap_ratio": m.gap_ratio,
                "opportunity_score": m.opportunity_score,
            }
            for m in metrics
        ]

        client = get_client()
        discoverer = KeywordDiscoverer(client)
        suggestions = await discoverer.suggest(metrics_dicts)

        return [KeywordSuggestionResponse(**s.to_dict()) for s in suggestions]

    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error in keyword discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Profile & Keyword Strategy Endpoints
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=ProfileResponse)
async def get_profile():
    """Get the freelancer profile configuration used for all LLM analyses."""
    return ProfileResponse(
        name=PROFILE.get("name", ""),
        title=PROFILE.get("title", ""),
        hourly_rate=PROFILE.get("hourly_rate", 0),
        hourly_range=PROFILE.get("hourly_range", ""),
        core_skills=PROFILE.get("core_skills", []),
        secondary_skills=PROFILE.get("secondary_skills", []),
        service_lines=PROFILE.get("service_lines", []),
        portfolio_projects=PROFILE.get("portfolio_projects", []),
        ideal_job_keywords=PROFILE.get("ideal_job_keywords", []),
        avoid_keywords=PROFILE.get("avoid_keywords", []),
        strategy=PROFILE.get("strategy", {}),
        total_upwork_jobs=PROFILE.get("total_upwork_jobs", 0),
        profile_summary=get_profile_summary(),
    )


@router.get("/keyword-fit", response_model=list[KeywordFitResponse])
async def keyword_fit():
    """
    Score all currently tracked keywords for profile fit (no LLM needed).
    Returns fit scores based on skill matching and market data.
    """
    db = get_db_session()
    try:
        metrics = db.query(KeywordMetric).order_by(
            KeywordMetric.opportunity_score.desc()
        ).limit(50).all()

        metrics_dicts = [
            {
                "keyword": m.keyword,
                "demand": m.demand,
                "supply": m.supply,
                "gap_ratio": m.gap_ratio,
                "opportunity_score": m.opportunity_score,
            }
            for m in metrics
        ]

        advisor = KeywordStrategyAdvisor(get_client())
        fits = advisor.score_keywords_fit(metrics_dicts)

        return [KeywordFitResponse(**f.to_dict()) for f in fits]
    finally:
        db.close()


@router.post("/keyword-strategy", response_model=KeywordStrategyResponse)
async def keyword_strategy():
    """
    LLM-powered keyword strategy analysis.
    Recommends which keywords to keep, modify, drop, or add based on profile fit and market data.
    """
    db = get_db_session()
    try:
        metrics = db.query(KeywordMetric).order_by(
            KeywordMetric.opportunity_score.desc()
        ).limit(30).all()

        metrics_dicts = [
            {
                "keyword": m.keyword,
                "demand": m.demand,
                "supply": m.supply,
                "gap_ratio": m.gap_ratio,
                "opportunity_score": m.opportunity_score,
            }
            for m in metrics
        ]

        advisor = KeywordStrategyAdvisor(get_client())
        result = await advisor.analyze_strategy(metrics_dicts)

        return KeywordStrategyResponse(**result.to_dict())

    except LLMConnectionError as e:
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"Error in keyword strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: JobRaw) -> dict:
    """Convert a SQLAlchemy JobRaw row to a plain dict for the analyzer."""
    return {
        "job_key": row.job_key,
        "title": row.title,
        "description": row.description or "",
        "budget": row.budget or "",
        "budget_value": row.budget_value,
        "client_spend": row.client_spend,
        "payment_verified": row.payment_verified,
        "proposals": row.proposals or "0",
        "skills": row.skills or "",
        "keyword": row.keyword or "",
        "url": row.url or "",
    }


def _persist_analysis(db: Session, analysis: JobAnalysis):
    """Save or update LLM analysis into job_opportunities table."""
    try:
        from orchestrator import parse_int_value, PROPOSALS_STALE_THRESHOLD
        existing = db.query(JobOpportunity).filter(
            JobOpportunity.job_key == analysis.job_key
        ).first()

        # Check staleness from raw job
        raw_job = db.query(JobRaw).filter(JobRaw.job_key == analysis.job_key).first()
        proposals_num = parse_int_value(raw_job.proposals) if raw_job else None
        is_stale = proposals_num is not None and proposals_num >= PROPOSALS_STALE_THRESHOLD

        reasons = json.dumps({
            "llm_summary": analysis.summary_1line,
            "llm_action": analysis.recommended_action,
            "llm_reasoning": analysis.reasoning,
            "risk_flags": analysis.risk_flags,
            "composite_score": analysis.composite_score,
            "opening_hook": analysis.opening_hook,
        })

        # Even if LLM says APPLY, don't recommend stale jobs
        effective_apply = analysis.recommended_action == "APPLY" and not is_stale

        if existing:
            existing.fit_score = analysis.composite_score * 100
            existing.apply_now = effective_apply
            existing.reasons = reasons
            existing.last_updated = datetime.utcnow()
        else:
            opp = JobOpportunity(
                job_key=analysis.job_key,
                title=analysis.title,
                keyword=raw_job.keyword if raw_job else "",
                opportunity_score=analysis.composite_score * 100,
                safety_score=analysis.client_quality * 100,
                fit_score=analysis.composite_score * 100,
                apply_now=effective_apply,
                reasons=reasons,
            )
            db.add(opp)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist analysis for {analysis.job_key}: {e}")


def _persist_proposal(db: Session, proposal):
    """Save or update LLM-generated proposal into proposal_drafts table."""
    try:
        existing = db.query(ProposalDraft).filter(
            ProposalDraft.job_key == proposal.job_key
        ).first()

        hook_points = json.dumps(proposal.key_differentiators)
        caution_notes = json.dumps([proposal.bid_rationale, proposal.estimated_timeline])

        if existing:
            existing.cover_letter_draft = proposal.cover_letter
            existing.hook_points = hook_points
            existing.caution_notes = caution_notes
            existing.updated_at = datetime.utcnow()
        else:
            draft = ProposalDraft(
                job_key=proposal.job_key,
                cover_letter_draft=proposal.cover_letter,
                hook_points=hook_points,
                caution_notes=caution_notes,
            )
            db.add(draft)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist proposal for {proposal.job_key}: {e}")


# ---------------------------------------------------------------------------
# Notification Endpoints
# ---------------------------------------------------------------------------

class NotificationsResponse(BaseModel):
    count: int = 0
    notifications: list[dict] = []


@router.get("/notifications", response_model=NotificationsResponse)
async def get_notifications(
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get recent HOT/WARM job notifications (for dashboard polling)."""
    notifier = get_notifier()
    recent = notifier.get_recent(limit)
    return NotificationsResponse(count=len(recent), notifications=recent)


@router.delete("/notifications")
async def clear_notifications():
    """Clear all notifications."""
    notifier = get_notifier()
    notifier.clear()
    return {"ok": True, "message": "Notifications cleared"}
