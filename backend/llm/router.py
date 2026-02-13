"""
LLM API Router – Endpoints for AI-powered job analysis, decision engine,
proposal generation, and keyword discovery.

Mounted at /v1/llm/* in the main FastAPI app.
"""
from __future__ import annotations

import json
import logging
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, JobRaw, JobOpportunity, ProposalDraft, KeywordMetric, TalentRaw
from llm.client import LLMClient, LLMError, LLMConnectionError
from llm.job_analyzer import JobAnalyzer, JobAnalysis
from llm.decision_engine import DecisionEngine, DecisionBatch
from llm.proposal_writer import ProposalWriter
from llm.keyword_discoverer import KeywordDiscoverer
from llm.keyword_strategy import KeywordStrategyAdvisor
from llm.profile_config import PROFILE, get_profile_summary, get_effective_profile, get_dynamic_profile_snapshot
from llm.profile_sync import sync_profile_from_upwork, save_dynamic_profile, build_profile_payload_from_text
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


class ProfileSyncRequest(BaseModel):
    upwork_url: str = ""
    profile_text: str = ""
    headline: str = ""


class ProfileSyncResponse(BaseModel):
    status: str = "ok"
    synced_at: str = ""
    upwork_url: str = ""
    extracted_keywords: list[str] = []
    detected_skills: list[str] = []
    headline: str = ""
    overview: str = ""


def _parse_skill_values(raw_value) -> list[str]:
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return [str(v).strip() for v in raw_value if str(v).strip()]
    text = str(raw_value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
    except Exception:
        pass
    return [s.strip() for s in text.replace(";", ",").split(",") if s.strip()]


def _parse_hourly_value(raw_value, fallback: float = 0.0) -> float:
    if raw_value is None:
        return fallback
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    digits = [c if c.isdigit() or c == "." else " " for c in str(raw_value)]
    tokens = [t for t in "".join(digits).split() if t]
    if not tokens:
        return fallback
    numbers = []
    for token in tokens:
        try:
            numbers.append(float(token))
        except Exception:
            continue
    if not numbers:
        return fallback
    return sum(numbers) / len(numbers)


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

            from orchestrator import parse_int_value

            # Recent-first selection: analyze newest unanalyzed jobs first.
            recent_raw = query.order_by(JobRaw.scraped_at.desc()).limit(limit * 20).all()
            jobs = []
            for j in recent_raw:
                if j.job_key in llm_analyzed_keys:
                    continue
                proposals_num = parse_int_value(j.proposals)
                if proposals_num is not None and proposals_num >= 50:
                    continue
                jobs.append(j)
                if len(jobs) >= limit:
                    break
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

        job_rows = query.order_by(
            JobRaw.scraped_at.desc(),
            JobOpportunity.fit_score.desc(),
        ).limit(limit).all()

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
    effective = get_effective_profile()
    return ProfileResponse(
        name=effective.get("name", ""),
        title=effective.get("title", ""),
        hourly_rate=effective.get("hourly_rate", 0),
        hourly_range=effective.get("hourly_range", ""),
        core_skills=effective.get("core_skills", []),
        secondary_skills=effective.get("secondary_skills", []),
        service_lines=effective.get("service_lines", []),
        portfolio_projects=effective.get("portfolio_projects", []),
        ideal_job_keywords=effective.get("ideal_job_keywords", []),
        avoid_keywords=effective.get("avoid_keywords", []),
        strategy=effective.get("strategy", {}),
        total_upwork_jobs=effective.get("total_upwork_jobs", 0),
        profile_summary=get_profile_summary(),
    )


@router.get("/profile/live", response_model=dict)
async def get_live_profile_snapshot():
    """Return latest dynamic profile sync payload (if available)."""
    return get_dynamic_profile_snapshot()


@router.get("/profile/competitive-live", response_model=dict)
async def get_live_competitive_profile_analysis():
    """Live competitive benchmark from synced profile + ingested talent pool."""
    db = get_db_session()
    try:
        profile = get_effective_profile()
        dynamic = get_dynamic_profile_snapshot() or {}

        profile_skills = {
            str(s).strip().lower()
            for s in [
                *(profile.get("core_skills", []) or []),
                *(profile.get("secondary_skills", []) or []),
                *(profile.get("dynamic_keywords", []) or []),
            ]
            if str(s).strip()
        }

        talents = (
            db.query(TalentRaw)
            .order_by(TalentRaw.scraped_at.desc())
            .limit(400)
            .all()
        )

        competitors = []
        all_rates: list[float] = []
        all_ratings: list[float] = []
        all_jobs: list[int] = []

        for t in talents:
            t_rate = _parse_hourly_value(getattr(t, "hourly_rate_value", None), _parse_hourly_value(t.hourly_rate, 0.0))
            t_rating = float(t.rating or 0.0)
            t_jobs = int(t.jobs_completed or 0)

            if t_rate > 0:
                all_rates.append(t_rate)
            if t_rating > 0:
                all_ratings.append(t_rating)
            if t_jobs > 0:
                all_jobs.append(t_jobs)

            t_skills = {s.lower() for s in _parse_skill_values(t.skills)}
            if not t_skills or not profile_skills:
                overlap_ratio = 0.0
                overlap_hits = 0
            else:
                overlap_hits = len(profile_skills & t_skills)
                overlap_ratio = overlap_hits / max(1, len(profile_skills))

            score = (
                overlap_ratio * 60.0
                + min(t_rating, 5.0) / 5.0 * 25.0
                + min(t_jobs, 200) / 200.0 * 15.0
            )

            competitors.append(
                {
                    "name": t.name or "Unknown",
                    "title": t.title or "",
                    "hourly_rate": t.hourly_rate or (f"${int(t_rate)}/hr" if t_rate > 0 else ""),
                    "rating": round(t_rating, 2),
                    "jobs_completed": t_jobs,
                    "skill_overlap": overlap_hits,
                    "skill_overlap_ratio": round(overlap_ratio, 3),
                    "competitive_score": round(score, 2),
                }
            )

        competitors.sort(key=lambda x: x["competitive_score"], reverse=True)
        top_competitors = competitors[:12]

        user_hourly = _parse_hourly_value(profile.get("hourly_rate"), _parse_hourly_value(profile.get("hourly_range"), 0.0))
        user_jobs = int(profile.get("total_upwork_jobs", 0) or 0)

        median_rate = round(sum(all_rates) / len(all_rates), 2) if all_rates else 0.0
        median_rating = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else 0.0
        median_jobs = round(sum(all_jobs) / len(all_jobs), 1) if all_jobs else 0.0

        high_fit_jobs = db.query(JobOpportunity).filter(JobOpportunity.fit_score >= 70).count()
        hot_apply_jobs = db.query(JobOpportunity).filter(JobOpportunity.apply_now == True).count()

        actions = []
        if user_jobs < max(3, int(median_jobs)):
            actions.append("Kısa ve hızlı tamamlanabilir 3-5 işe öncelik ver; social proof açığını kapat.")
        if user_hourly > 0 and median_rate > 0 and user_hourly > median_rate * 1.25:
            actions.append("Kazanç yerine itibar fazındasın: teklifleri bir süre pazar medianına yaklaştır.")
        if hot_apply_jobs < 5:
            actions.append("Pipeline dar: yeni keyword sync + ingest sonrası LLM batch analizi otomatik tetikle.")
        if not actions:
            actions.append("Profil-pazar uyumu sağlıklı; APPLY havuzunda hız/kalite optimizasyonuna odaklan.")

        return {
            "synced_at": dynamic.get("synced_at") or profile.get("dynamic_synced_at"),
            "profile_live": {
                "title": profile.get("title", ""),
                "hourly_range": profile.get("hourly_range", ""),
                "total_upwork_jobs": user_jobs,
                "dynamic_keywords": profile.get("dynamic_keywords", []) or [],
                "dynamic_keyword_count": len(profile.get("dynamic_keywords", []) or []),
            },
            "market_snapshot": {
                "talent_scanned": len(talents),
                "high_fit_jobs": int(high_fit_jobs),
                "hot_apply_jobs": int(hot_apply_jobs),
                "median_hourly_rate": median_rate,
                "median_rating": median_rating,
                "median_jobs_completed": median_jobs,
            },
            "benchmark": {
                "experience_gap": round(median_jobs - user_jobs, 1),
                "rate_gap": round(user_hourly - median_rate, 2) if user_hourly and median_rate else 0.0,
                "readiness_score": round(min(100.0, (hot_apply_jobs * 12.0) + (len(profile_skills) * 1.2)), 1),
            },
            "top_competitors": top_competitors,
            "priority_actions": actions,
        }
    finally:
        db.close()


@router.post("/profile/sync", response_model=ProfileSyncResponse)
async def sync_profile(payload: ProfileSyncRequest):
    """Fetch public Upwork profile and update dynamic keyword model."""
    upwork_url = payload.upwork_url.strip() or PROFILE.get("upwork_url", "")
    manual_text = payload.profile_text.strip()

    if not upwork_url and not manual_text:
        raise HTTPException(status_code=400, detail="Missing upwork_url or profile_text")

    try:
        if manual_text:
            synced = build_profile_payload_from_text(
                profile_text=manual_text,
                upwork_url=upwork_url,
                headline=payload.headline,
            )
            await asyncio.to_thread(save_dynamic_profile, synced)
        else:
            synced = await asyncio.to_thread(sync_profile_from_upwork, upwork_url)

        return ProfileSyncResponse(
            status="ok",
            synced_at=synced.get("synced_at", ""),
            upwork_url=synced.get("upwork_url", ""),
            extracted_keywords=synced.get("extracted_keywords", []),
            detected_skills=synced.get("detected_skills", []),
            headline=synced.get("headline", ""),
            overview=synced.get("overview", ""),
        )
    except Exception as e:
        logger.error(f"Profile sync failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=(
                f"Profile sync failed: {e}. "
                "If Upwork blocks server-side fetch (403), call this endpoint with profile_text to sync dynamically."
            ),
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
