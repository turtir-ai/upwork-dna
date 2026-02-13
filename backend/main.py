"""
FastAPI backend for Upwork DNA scraping system
"""
import os
import uuid
import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, TimeoutError as SQLAlchemyTimeoutError
import logging
logger = logging.getLogger(__name__)

from database import (
    SessionLocal,
    get_db,
    init_db,
    QueueItem,
    Job,
    Talent,
    Project,
    ScrapingJob,
)
from models import (
    QueueItemCreate, QueueItemResponse, QueueListResponse,
    ScrapingRequest, ScrapingStatusResponse,
    ResultsResponse, JobResponse, TalentResponse, ProjectResponse,
    SystemStatusResponse, ErrorResponse,
    KeywordRecommendationResponse, JobOpportunityResponse, JobEnrichedResponse,
    ProposalDraftResponse, QueueTelemetryResponse,
    QueueTelemetryUpdateRequest, IngestScanResponse,
    OrchestratorSummaryResponse, RunIngestRequest, RunIngestResponse
)
from orchestrator import OrchestratorService
from llm.router import router as llm_router
from dotenv import load_dotenv
import sys
sys.path.insert(0, '/Users/dev/Documents/upworkextension/backend/scrapers')
from upwork_scraper import UpworkScraper, ScraperConfig

# Load environment variables
load_dotenv()

# Global state
active_scraping_jobs = {}
scraping_tasks = {}
orchestrator_task: Optional[asyncio.Task] = None
ingest_retry_thread: Optional[threading.Thread] = None
orchestrator = OrchestratorService()

# Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["http://localhost:3000","http://localhost:3001"]')
API_VERSION = "1.0.0"
START_TIME = datetime.utcnow()
DB_RETRY_ATTEMPTS = max(1, int(os.getenv("DB_RETRY_ATTEMPTS", "4")))
DB_RETRY_BASE_DELAY_SECONDS = max(0.1, float(os.getenv("DB_RETRY_BASE_DELAY_SECONDS", "0.4")))
DB_LOCK_TOKENS = (
    "database is locked",
    "database schema is locked",
    "queuepool limit",
    "connection timed out",
    "db_write_lock_timeout",
)
DB_WRITE_LOCK_TIMEOUT_SECONDS = max(5, int(os.getenv("DB_WRITE_LOCK_TIMEOUT_SECONDS", "45")))
RUN_INGEST_MIN_PROCESS_SECONDS = max(1, int(os.getenv("RUN_INGEST_MIN_PROCESS_SECONDS", "12")))
RUN_INGEST_REFRESH_SECONDS = max(5, int(os.getenv("RUN_INGEST_REFRESH_SECONDS", "90")))
RUN_INGEST_MIN_NEW_ITEMS = max(1, int(os.getenv("RUN_INGEST_MIN_NEW_ITEMS", "20")))
RUN_INGEST_TRACKER_MAX = max(100, int(os.getenv("RUN_INGEST_TRACKER_MAX", "1000")))
RUN_INGEST_RETRY_INTERVAL_SECONDS = max(1, int(os.getenv("RUN_INGEST_RETRY_INTERVAL_SECONDS", "2")))
RUN_INGEST_RETRY_MAX_BACKOFF_SECONDS = max(5, int(os.getenv("RUN_INGEST_RETRY_MAX_BACKOFF_SECONDS", "60")))
RUN_INGEST_RETRY_MAX_QUEUE = max(100, int(os.getenv("RUN_INGEST_RETRY_MAX_QUEUE", "3000")))
RUN_INGEST_WRITE_TIMEOUT_FINAL_SECONDS = max(2.0, float(os.getenv("RUN_INGEST_WRITE_TIMEOUT_FINAL_SECONDS", "4.0")))
RUN_INGEST_WRITE_TIMEOUT_PROGRESS_SECONDS = max(0.5, float(os.getenv("RUN_INGEST_WRITE_TIMEOUT_PROGRESS_SECONDS", "1.0")))

T = TypeVar("T")
DB_WRITE_LOCK = threading.Lock()
RUN_INGEST_TRACKER_LOCK = threading.Lock()
RUN_INGEST_TRACKER: dict[str, dict] = {}
RUN_INGEST_RETRY_QUEUE_LOCK = threading.Lock()
RUN_INGEST_RETRY_QUEUE: dict[str, dict] = {}
RUN_INGEST_RETRY_STOP_EVENT = threading.Event()
READ_CACHE_LOCK = threading.Lock()
READ_CACHE: dict[str, object] = {}
BACKGROUND_REFRESH_LOCK = threading.Lock()
BACKGROUND_REFRESH_IN_FLIGHT = False

FINAL_RUN_STATUSES = {"complete", "completed", "stopped", "done", "finished"}
DEFAULT_SUMMARY = {
    "jobs_raw": 0,
    "talent_raw": 0,
    "projects_raw": 0,
    "keywords": 0,
    "opportunities": 0,
    "last_ingest_at": None,
}
DEFAULT_QUEUE = {
    "total": 0,
    "pending": 0,
    "running": 0,
    "completed": 0,
    "error": 0,
    "last_cycle_at": None,
}


def is_retryable_db_error(exc: Exception) -> bool:
    if isinstance(exc, SQLAlchemyTimeoutError):
        return True
    message = str(exc).lower()
    if isinstance(exc, OperationalError) and any(token in message for token in DB_LOCK_TOKENS):
        return True
    return any(token in message for token in DB_LOCK_TOKENS)


def run_with_retry(
    operation_name: str,
    fn: Callable[[], T],
    attempts: Optional[int] = None,
) -> T:
    max_attempts = max(1, attempts if attempts is not None else DB_RETRY_ATTEMPTS)
    last_error: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not is_retryable_db_error(exc) or attempt >= max_attempts - 1:
                raise
            delay_seconds = DB_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            logger.warning(
                "[DB Retry] %s failed (%s/%s): %s; retrying in %.2fs",
                operation_name,
                attempt + 1,
                max_attempts,
                exc,
                delay_seconds,
            )
            time.sleep(delay_seconds)
    if last_error:
        raise last_error
    raise RuntimeError(f"{operation_name} failed without an explicit error")


def run_db_operation_with_new_session(
    operation_name: str,
    operation: Callable[[Session], T],
    write: bool = False,
    retry_attempts: Optional[int] = None,
    write_lock_timeout_seconds: Optional[float] = None,
) -> T:
    def _run_once() -> T:
        lock_acquired = False
        if write:
            lock_timeout = (
                write_lock_timeout_seconds
                if write_lock_timeout_seconds is not None
                else DB_WRITE_LOCK_TIMEOUT_SECONDS
            )
            lock_acquired = DB_WRITE_LOCK.acquire(timeout=lock_timeout)
            if not lock_acquired:
                raise RuntimeError("db_write_lock_timeout")
        db = SessionLocal()
        try:
            return operation(db)
        except Exception:  # noqa: BLE001
            db.rollback()
            raise
        finally:
            db.close()
            if lock_acquired:
                DB_WRITE_LOCK.release()

    return run_with_retry(operation_name, _run_once, attempts=retry_attempts)


def run_orchestrator_cycle_sync() -> dict:
    """Run a full orchestrator cycle in a dedicated DB session with retry."""
    return run_db_operation_with_new_session(
        "orchestrator_cycle",
        lambda db: orchestrator.scan_and_ingest(db),
        write=False,
        retry_attempts=1,
    )


def run_orchestrator_refresh_sync() -> dict:
    """Run only scoring/recommendation refresh without re-scanning files."""
    return run_db_operation_with_new_session(
        "orchestrator_refresh",
        lambda db: {
            "updated_metrics_at": orchestrator.refresh_metrics_and_opportunities(db).isoformat()
        },
        write=False,
        retry_attempts=1,
    )


def _run_payload_stats(run_payload: dict) -> dict:
    data = run_payload.get("data") if isinstance(run_payload, dict) else {}
    data = data if isinstance(data, dict) else {}
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    talent = data.get("talent") if isinstance(data.get("talent"), list) else []
    projects = data.get("projects") if isinstance(data.get("projects"), list) else []
    detail_count = 0
    for row in jobs + talent + projects:
        if isinstance(row, dict) and row.get("detail_status"):
            detail_count += 1
    return {
        "jobs": len(jobs),
        "talent": len(talent),
        "projects": len(projects),
        "total": len(jobs) + len(talent) + len(projects),
        "detail": detail_count,
    }


def _run_status_value(run_payload: dict) -> str:
    if not isinstance(run_payload, dict):
        return ""
    return str(run_payload.get("status", "")).strip().lower()


def _is_final_run(run_payload: dict) -> bool:
    return _run_status_value(run_payload) in FINAL_RUN_STATUSES


def _build_run_signature(run_payload: dict) -> str:
    stats = _run_payload_stats(run_payload)
    status = _run_status_value(run_payload)
    return (
        f"{status}|{stats['jobs']}|{stats['talent']}|{stats['projects']}|{stats['detail']}"
    )


def _default_run_ingest_response(run_id: str, run_payload: dict) -> dict:
    stats = _run_payload_stats(run_payload)
    keyword = ""
    if isinstance(run_payload, dict):
        keyword = str(run_payload.get("keyword", "")).strip() or "general"
    return {
        "run_id": run_id,
        "keyword": keyword or "general",
        "jobs_ingested": stats["jobs"],
        "talent_ingested": stats["talent"],
        "projects_ingested": stats["projects"],
        "updated_metrics_at": datetime.utcnow().isoformat(),
    }


def _update_run_ingest_tracker(run_id: str, update: dict) -> None:
    with RUN_INGEST_TRACKER_LOCK:
        current = RUN_INGEST_TRACKER.get(run_id, {})
        merged = {**current, **update}
        merged["updated_at"] = time.time()
        RUN_INGEST_TRACKER[run_id] = merged
        if len(RUN_INGEST_TRACKER) <= RUN_INGEST_TRACKER_MAX:
            return
        # prune oldest entries
        sorted_items = sorted(
            RUN_INGEST_TRACKER.items(),
            key=lambda item: item[1].get("updated_at", 0),
            reverse=True,
        )
        RUN_INGEST_TRACKER.clear()
        for key, value in sorted_items[:RUN_INGEST_TRACKER_MAX]:
            RUN_INGEST_TRACKER[key] = value


def _persist_run_ingest(run_id: str, payload_dump: dict, is_final: bool) -> dict:
    write_timeout = (
        RUN_INGEST_WRITE_TIMEOUT_FINAL_SECONDS
        if is_final
        else RUN_INGEST_WRITE_TIMEOUT_PROGRESS_SECONDS
    )
    return run_db_operation_with_new_session(
        "v1_ingest_run",
        lambda db: orchestrator.ingest_run_payload(
            db=db,
            run_id=run_id,
            run_payload=payload_dump,
            refresh_metrics=False,
        ),
        write=True,
        retry_attempts=1,
        write_lock_timeout_seconds=write_timeout,
    )


def _record_run_ingest_success(
    run_id: str,
    signature: str,
    stats: dict,
    response: dict,
    processed_at: float,
    is_final: bool,
    did_refresh: bool,
) -> None:
    update = {
        "signature": signature,
        "last_processed_at": processed_at,
        "last_total": stats["total"],
        "last_response": response,
    }
    if did_refresh:
        update["last_refresh_at"] = processed_at

    if is_final:
        with RUN_INGEST_TRACKER_LOCK:
            RUN_INGEST_TRACKER.pop(run_id, None)
        return
    _update_run_ingest_tracker(run_id, update)


def _trim_ingest_retry_queue_unlocked() -> None:
    if len(RUN_INGEST_RETRY_QUEUE) <= RUN_INGEST_RETRY_MAX_QUEUE:
        return

    non_final_ids = [
        item[0]
        for item in sorted(
            RUN_INGEST_RETRY_QUEUE.items(),
            key=lambda entry: entry[1].get("queued_at", 0),
        )
        if not entry[1].get("is_final")
    ]
    for run_id in non_final_ids:
        if len(RUN_INGEST_RETRY_QUEUE) <= RUN_INGEST_RETRY_MAX_QUEUE:
            return
        RUN_INGEST_RETRY_QUEUE.pop(run_id, None)

    if len(RUN_INGEST_RETRY_QUEUE) <= RUN_INGEST_RETRY_MAX_QUEUE:
        return
    oldest = sorted(
        RUN_INGEST_RETRY_QUEUE.items(),
        key=lambda entry: entry[1].get("queued_at", 0),
    )
    while len(RUN_INGEST_RETRY_QUEUE) > RUN_INGEST_RETRY_MAX_QUEUE and oldest:
        run_id, _ = oldest.pop(0)
        RUN_INGEST_RETRY_QUEUE.pop(run_id, None)


def _enqueue_run_ingest_retry(
    run_id: str,
    payload_dump: dict,
    run_payload: dict,
    is_final: bool,
    error: str,
) -> None:
    now = time.time()
    signature = _build_run_signature(run_payload)
    stats = _run_payload_stats(run_payload)

    with RUN_INGEST_RETRY_QUEUE_LOCK:
        current = RUN_INGEST_RETRY_QUEUE.get(run_id, {})
        current_stats = current.get("stats", {})
        current_total = int(current_stats.get("total", 0))
        if current and not is_final and current_total > stats["total"]:
            return

        RUN_INGEST_RETRY_QUEUE[run_id] = {
            "payload": payload_dump,
            "signature": signature,
            "stats": stats,
            "is_final": bool(is_final or current.get("is_final")),
            "queued_at": current.get("queued_at", now),
            "last_queued_at": now,
            "attempts": int(current.get("attempts", 0)),
            "next_retry_at": now,
            "last_error": error,
        }
        _trim_ingest_retry_queue_unlocked()


def _pop_ready_ingest_retry_unlocked(now: float) -> tuple[Optional[str], Optional[dict]]:
    ready_items = [
        (run_id, payload)
        for run_id, payload in RUN_INGEST_RETRY_QUEUE.items()
        if float(payload.get("next_retry_at", 0)) <= now
    ]
    if not ready_items:
        return None, None

    ready_items.sort(
        key=lambda item: (
            0 if item[1].get("is_final") else 1,
            item[1].get("queued_at", 0),
        )
    )
    run_id, payload = ready_items[0]
    RUN_INGEST_RETRY_QUEUE.pop(run_id, None)
    return run_id, payload


def _requeue_ingest_retry(run_id: str, payload: dict, error: str) -> None:
    attempts = int(payload.get("attempts", 0)) + 1
    backoff_seconds = min(
        RUN_INGEST_RETRY_MAX_BACKOFF_SECONDS,
        RUN_INGEST_RETRY_INTERVAL_SECONDS * (2 ** min(attempts, 6)),
    )
    payload["attempts"] = attempts
    payload["last_error"] = error
    payload["next_retry_at"] = time.time() + backoff_seconds
    payload["last_queued_at"] = time.time()
    with RUN_INGEST_RETRY_QUEUE_LOCK:
        RUN_INGEST_RETRY_QUEUE[run_id] = payload
        _trim_ingest_retry_queue_unlocked()


def _ingest_retry_queue_size() -> int:
    with RUN_INGEST_RETRY_QUEUE_LOCK:
        return len(RUN_INGEST_RETRY_QUEUE)


def ingest_retry_worker_loop() -> None:
    logger.info(
        "[IngestRetry] Worker started (interval=%ss, max_backoff=%ss)",
        RUN_INGEST_RETRY_INTERVAL_SECONDS,
        RUN_INGEST_RETRY_MAX_BACKOFF_SECONDS,
    )
    while not RUN_INGEST_RETRY_STOP_EVENT.wait(RUN_INGEST_RETRY_INTERVAL_SECONDS):
        run_id: Optional[str] = None
        queued_payload: Optional[dict] = None
        now = time.time()
        with RUN_INGEST_RETRY_QUEUE_LOCK:
            run_id, queued_payload = _pop_ready_ingest_retry_unlocked(now)

        if not run_id or not queued_payload:
            continue

        payload_dump = queued_payload.get("payload") if isinstance(queued_payload, dict) else {}
        payload_dump = payload_dump if isinstance(payload_dump, dict) else {}
        run_payload = payload_dump.get("run") if isinstance(payload_dump.get("run"), dict) else {}
        is_final = bool(queued_payload.get("is_final"))
        signature = _build_run_signature(run_payload)
        stats = _run_payload_stats(run_payload)

        with RUN_INGEST_TRACKER_LOCK:
            tracker = RUN_INGEST_TRACKER.get(run_id, {}).copy()
        last_refresh_at = float(tracker.get("last_refresh_at", 0))
        do_refresh = is_final or (now - last_refresh_at >= RUN_INGEST_REFRESH_SECONDS)

        try:
            response = _persist_run_ingest(run_id, payload_dump, is_final=is_final)
            _record_run_ingest_success(
                run_id=run_id,
                signature=signature,
                stats=stats,
                response=response,
                processed_at=now,
                is_final=is_final,
                did_refresh=do_refresh,
            )
            if do_refresh:
                trigger_background_refresh(f"ingest_retry:{run_id}", mode="refresh")
            logger.info(
                "[IngestRetry] Persisted queued run %s (final=%s, total=%s)",
                run_id,
                is_final,
                stats["total"],
            )
        except Exception as exc:  # noqa: BLE001
            _requeue_ingest_retry(run_id, queued_payload, str(exc))
            logger.warning(
                "[IngestRetry] Retry failed for %s (attempt=%s): %s",
                run_id,
                int(queued_payload.get("attempts", 0)),
                exc,
            )


def trigger_background_refresh(reason: str, mode: str = "scan") -> None:
    global BACKGROUND_REFRESH_IN_FLIGHT
    with BACKGROUND_REFRESH_LOCK:
        if BACKGROUND_REFRESH_IN_FLIGHT:
            return
        BACKGROUND_REFRESH_IN_FLIGHT = True

    def _worker() -> None:
        global BACKGROUND_REFRESH_IN_FLIGHT
        mode_name = "refresh" if mode == "refresh" else "scan"
        runner = run_orchestrator_refresh_sync if mode_name == "refresh" else run_orchestrator_cycle_sync
        try:
            runner()
            logger.info("[Refresh] background %s completed (%s)", mode_name, reason)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Refresh] background %s failed (%s): %s", mode_name, reason, exc)
        finally:
            with BACKGROUND_REFRESH_LOCK:
                BACKGROUND_REFRESH_IN_FLIGHT = False

    thread = threading.Thread(
        target=_worker,
        daemon=True,
        name=f"upwork-{mode}-refresh",
    )
    thread.start()


def _get_cached_read(cache_key: str, default):
    with READ_CACHE_LOCK:
        return READ_CACHE.get(cache_key, default)


def _set_cached_read(cache_key: str, value) -> None:
    with READ_CACHE_LOCK:
        READ_CACHE[cache_key] = value


def _safe_json(raw):
    """Safe JSON parse — returns dict or empty dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def run_db_read_with_fallback(cache_key: str, operation_name: str, operation: Callable[[Session], T], default):
    try:
        result = run_db_operation_with_new_session(
            operation_name,
            operation,
            write=False,
            retry_attempts=1,
        )
        _set_cached_read(cache_key, result)
        return result
    except Exception as exc:  # noqa: BLE001
        cached = _get_cached_read(cache_key, None)
        if cached is not None:
            logger.warning("[DB Fallback] %s served from cache: %s", operation_name, exc)
            return cached
        logger.warning("[DB Fallback] %s served default: %s", operation_name, exc)
        return default


async def run_llm_analysis_cycle():
    """Autonomous LLM analysis: analyze unscored jobs, run decision engine, notify HOT."""
    from llm.client import LLMClient, LLMConnectionError
    from llm.job_analyzer import JobAnalyzer
    from llm.decision_engine import DecisionEngine
    from llm.notifier import get_notifier
    from database import JobRaw, JobOpportunity

    client = LLMClient()

    # Check if glm-bridge is up
    if not await client.is_available():
        logger.info("[LLM-Auto] glm-bridge unreachable, skipping cycle")
        return

    db = SessionLocal()
    try:
        # Find jobs that need LLM analysis:
        # 1. Not yet LLM-analyzed (check reasons for llm_action, not just fit_score > 0)
        # 2. Prefer fresh jobs (low proposals, recently scraped)
        from orchestrator import parse_int_value, PROPOSALS_DEAD_THRESHOLD
        import json as _json

        # Get keys of already LLM-analyzed jobs
        llm_analyzed_keys = set()
        for row in db.query(JobOpportunity).filter(JobOpportunity.fit_score > 0).all():
            try:
                r = json.loads(row.reasons or "{}")
                if isinstance(r, dict) and r.get("llm_action"):
                    llm_analyzed_keys.add(row.job_key)
            except Exception:
                pass

        # Get fresh jobs (ordered by scraped_at desc, skip 50+ proposals jobs)
        all_jobs = db.query(JobRaw).order_by(JobRaw.scraped_at.desc()).limit(200).all()
        
        unanalyzed = []
        for j in all_jobs:
            if j.job_key in llm_analyzed_keys:
                continue
            # Skip dead/filled jobs (50+ proposals)
            proposals_num = parse_int_value(j.proposals)
            if proposals_num is not None and proposals_num >= PROPOSALS_DEAD_THRESHOLD:
                continue
            unanalyzed.append(j)

        if not unanalyzed:
            logger.info("[LLM-Auto] No fresh unanalyzed jobs to process")
            await client.close()
            return

        batch_size = min(len(unanalyzed), int(os.getenv("LLM_AUTO_BATCH_SIZE", "10")))
        jobs_to_analyze = unanalyzed[:batch_size]

        logger.info(f"[LLM-Auto] Analyzing {len(jobs_to_analyze)} fresh jobs (skipped {len(all_jobs) - len(unanalyzed)} stale/analyzed)...")

        job_dicts = [
            {
                "job_key": j.job_key, "title": j.title, "description": j.description or "",
                "budget": j.budget or "", "budget_value": j.budget_value,
                "client_spend": j.client_spend, "payment_verified": j.payment_verified,
                "proposals": j.proposals or "0", "skills": j.skills or "",
                "keyword": j.keyword or "",
            }
            for j in jobs_to_analyze
        ]

        analyzer = JobAnalyzer(client)
        analyses = await analyzer.analyze_batch(job_dicts)

        # Persist analyses
        for a in analyses:
            # Check if the original job has stale proposals
            orig_job = next((j for j in jobs_to_analyze if j.job_key == a.job_key), None)
            proposals_num = parse_int_value(orig_job.proposals) if orig_job else None
            is_stale = proposals_num is not None and proposals_num >= 30

            existing = db.query(JobOpportunity).filter(JobOpportunity.job_key == a.job_key).first()
            reasons = _json.dumps({
                "llm_summary": a.summary_1line, "llm_action": a.recommended_action,
                "llm_reasoning": a.reasoning, "risk_flags": a.risk_flags,
                "composite_score": a.composite_score, "opening_hook": a.opening_hook,
            })
            # Override: even if LLM says APPLY, don't recommend stale jobs
            effective_apply = a.recommended_action == "APPLY" and not is_stale
            
            if existing:
                existing.fit_score = a.composite_score * 100
                existing.apply_now = effective_apply
                existing.reasons = reasons
                existing.last_updated = datetime.utcnow()
            else:
                db.add(JobOpportunity(
                    job_key=a.job_key, title=a.title, keyword=orig_job.keyword if orig_job else "",
                    opportunity_score=a.composite_score * 100, safety_score=a.client_quality * 100,
                    fit_score=a.composite_score * 100, apply_now=effective_apply,
                    reasons=reasons,
                ))
        db.commit()

        # Run decision engine
        engine = DecisionEngine(client=client, use_llm_ranking=False)
        batch = await engine.decide(analyses)

        # Notify HOT/WARM jobs
        notifier = get_notifier()
        await notifier.notify_batch(batch.to_dict()["decisions"])

        logger.info(
            f"[LLM-Auto] Cycle complete: {len(analyses)} analyzed, "
            f"🔥 {batch.hot_count} HOT, ☀️ {batch.warm_count} WARM"
        )
    except LLMConnectionError:
        logger.info("[LLM-Auto] glm-bridge connection lost during cycle")
    except Exception as exc:
        logger.exception("[LLM-Auto] Cycle error: %s", exc)
    finally:
        db.close()
        await client.close()


async def orchestrator_scheduler_loop():
    """24/7 local analysis loop."""
    interval_seconds = int(os.getenv("ORCHESTRATOR_CYCLE_SECONDS", "300"))
    while True:
        try:
            await asyncio.to_thread(run_orchestrator_cycle_sync)
        except Exception as exc:
            logger.exception("[Orchestrator] Cycle failed: %s", exc)
        # Run LLM analysis after each orchestrator cycle
        try:
            await run_llm_analysis_cycle()
        except Exception as exc:
            logger.exception("[LLM-Auto] Analysis cycle failed: %s", exc)
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    global orchestrator_task, ingest_retry_thread
    # Startup
    init_db()
    RUN_INGEST_RETRY_STOP_EVENT.clear()
    ingest_retry_thread = threading.Thread(
        target=ingest_retry_worker_loop,
        daemon=True,
        name="upwork-ingest-retry",
    )
    ingest_retry_thread.start()
    orchestrator_task = asyncio.create_task(orchestrator_scheduler_loop())
    yield
    # Shutdown
    for task in scraping_tasks.values():
        task.cancel()
    RUN_INGEST_RETRY_STOP_EVENT.set()
    if ingest_retry_thread and ingest_retry_thread.is_alive():
        ingest_retry_thread.join(timeout=2.0)
    if orchestrator_task:
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Upwork DNA API",
    description="Scraping API for Upwork data extraction",
    version=API_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=eval(CORS_ORIGINS) if isinstance(CORS_ORIGINS, str) else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount LLM Intelligence router
app.include_router(llm_router)


async def run_scraping_job(
    job_id: str,
    keyword: str,
    job_type: str,
    max_pages: int,
    db: Session
):
    """Background task for scraping using existing UpworkScraper"""
    try:
        # Update status to running
        scraping_job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
        if scraping_job:
            scraping_job.status = "running"
            scraping_job.started_at = datetime.utcnow()
            db.commit()

        # Configure scraper
        config = ScraperConfig(
            headless=os.getenv("SCRAPER_HEADLESS", "True").lower() == "true",
            max_pages=max_pages,
            save_to_file=False
        )

        results = {'jobs': [], 'talent': [], 'projects': []}
        total_items = 0

        # Run scraper using existing UpworkScraper
        async with UpworkScraper(config) as scraper:
            if job_type in ['jobs', 'all']:
                jobs = await scraper.search_jobs(keyword, max_pages=max_pages)
                for job in jobs:
                    job_dict = job.to_dict()
                    job_dict['keyword'] = keyword
                    existing = db.query(Job).filter(Job.url == job_dict.get('url')).first()
                    if not existing:
                        db_job = Job(**job_dict)
                        db.add(db_job)
                        total_items += 1
                    results['jobs'].append(job_dict)

            if job_type in ['talent', 'all']:
                talents = await scraper.search_talent(keyword, max_pages=max_pages)
                for talent in talents:
                    talent_dict = talent.to_dict()
                    talent_dict['keyword'] = keyword
                    # Map fields to match database schema
                    talent_dict['description'] = talent_dict.get('bio')
                    existing = db.query(Talent).filter(Talent.url == talent_dict.get('url')).first()
                    if not existing:
                        db_talent = Talent(**talent_dict)
                        db.add(db_talent)
                        total_items += 1
                    results['talent'].append(talent_dict)

            if job_type in ['projects', 'all']:
                projects = await scraper.search_projects(keyword, max_pages=max_pages)
                for project in projects:
                    project_dict = project.to_dict()
                    project_dict['keyword'] = keyword
                    existing = db.query(Project).filter(Project.url == project_dict.get('url')).first()
                    if not existing:
                        db_project = Project(**project_dict)
                        db.add(db_project)
                        total_items += 1
                    results['projects'].append(project_dict)

        db.commit()

        # Update queue item
        queue_item = db.query(QueueItem).filter(QueueItem.keyword == keyword).first()
        if queue_item:
            queue_item.status = "completed"
            queue_item.updated_at = datetime.utcnow()

        # Update scraping job
        if scraping_job:
            scraping_job.status = "completed"
            scraping_job.completed_at = datetime.utcnow()
            scraping_job.total_items = total_items
            scraping_job.processed_items = total_items
            db.commit()

    except Exception as e:
        # Update status to failed
        scraping_job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
        if scraping_job:
            scraping_job.status = "failed"
            scraping_job.error_message = str(e)
            scraping_job.completed_at = datetime.utcnow()
            db.commit()

        queue_item = db.query(QueueItem).filter(QueueItem.keyword == keyword).first()
        if queue_item:
            queue_item.status = "failed"
            queue_item.updated_at = datetime.utcnow()
            db.commit()

    finally:
        # Clean up
        if job_id in active_scraping_jobs:
            del active_scraping_jobs[job_id]
        if job_id in scraping_tasks:
            del scraping_tasks[job_id]


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Upwork DNA API",
        "version": API_VERSION,
        "status": "running",
        "docs": "/docs"
    }


# Queue endpoints
@app.post("/queue", response_model=QueueItemResponse, status_code=201)
async def add_to_queue(
    item: QueueItemCreate,
    db: Session = Depends(get_db)
):
    """Add keyword to scraping queue"""
    # Check if already exists
    existing = db.query(QueueItem).filter(QueueItem.keyword == item.keyword).first()
    if existing:
        raise HTTPException(status_code=400, detail="Keyword already in queue")

    queue_item = QueueItem(**item.model_dump())
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    return queue_item


@app.get("/queue", response_model=QueueListResponse)
async def get_queue(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all queue items"""
    query = db.query(QueueItem)

    if status:
        query = query.filter(QueueItem.status == status)

    total = query.count()
    items = query.order_by(QueueItem.priority.desc(), QueueItem.created_at.asc()).offset(offset).limit(limit).all()

    return QueueListResponse(items=items, total=total)


@app.delete("/queue/{item_id}")
async def remove_from_queue(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Remove item from queue"""
    item = db.query(QueueItem).filter(QueueItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item removed from queue"}


@app.delete("/queue/keyword/{keyword}")
async def remove_from_queue_by_keyword(
    keyword: str,
    db: Session = Depends(get_db)
):
    """Remove item from queue by keyword"""
    item = db.query(QueueItem).filter(QueueItem.keyword == keyword).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    db.delete(item)
    db.commit()

    return {"message": f"Item '{keyword}' removed from queue"}


# Scraping endpoints
@app.post("/scrape", response_model=ScrapingStatusResponse, status_code=202)
async def start_scraping(
    request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start scraping for a keyword"""
    job_id = str(uuid.uuid4())

    # Create scraping job record
    scraping_job = ScrapingJob(
        job_id=job_id,
        keyword=request.keyword,
        job_type=request.job_type,
        status="pending"
    )
    db.add(scraping_job)

    # Update or create queue item
    queue_item = db.query(QueueItem).filter(QueueItem.keyword == request.keyword).first()
    if queue_item:
        queue_item.status = "pending"
        queue_item.job_type = request.job_type
    else:
        queue_item = QueueItem(
            keyword=request.keyword,
            job_type=request.job_type,
            status="pending"
        )
        db.add(queue_item)

    db.commit()
    db.refresh(scraping_job)

    # Start background task
    task = asyncio.create_task(run_scraping_job(
        job_id, request.keyword, request.job_type, request.max_pages, db
    ))
    scraping_tasks[job_id] = task
    active_scraping_jobs[job_id] = datetime.utcnow()

    return scraping_job


@app.get("/scrape/status/{job_id}", response_model=ScrapingStatusResponse)
async def get_scraping_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status of a scraping job"""
    job = db.query(ScrapingJob).filter(ScrapingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Scraping job not found")

    return job


@app.get("/scrape/active")
async def get_active_jobs():
    """Get all currently active scraping jobs"""
    return {
        "active_jobs": list(active_scraping_jobs.keys()),
        "count": len(active_scraping_jobs)
    }


# Results endpoints
@app.get("/results", response_model=ResultsResponse)
async def get_all_results(
    keyword: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all scraped data"""
    jobs = []
    talent = []
    projects = []

    if job_type in ['jobs', None]:
        query = db.query(Job)
        if keyword:
            query = query.filter(Job.keyword == keyword)
        jobs = query.order_by(Job.scraped_at.desc()).offset(offset).limit(limit).all()

    if job_type in ['talent', None]:
        query = db.query(Talent)
        if keyword:
            query = query.filter(Talent.keyword == keyword)
        talent = query.order_by(Talent.scraped_at.desc()).offset(offset).limit(limit).all()

    if job_type in ['projects', None]:
        query = db.query(Project)
        if keyword:
            query = query.filter(Project.keyword == keyword)
        projects = query.order_by(Project.scraped_at.desc()).offset(offset).limit(limit).all()

    return ResultsResponse(
        jobs=jobs,
        talent=talent,
        projects=projects,
        totals={
            "jobs": db.query(Job).count(),
            "talent": db.query(Talent).count(),
            "projects": db.query(Project).count()
        }
    )


@app.get("/results/{keyword}", response_model=ResultsResponse)
async def get_results_by_keyword(
    keyword: str,
    job_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get scraped data for a specific keyword"""
    jobs = []
    talent = []
    projects = []

    if job_type in ['jobs', None]:
        jobs = db.query(Job).filter(Job.keyword == keyword).order_by(Job.scraped_at.desc()).offset(offset).limit(limit).all()

    if job_type in ['talent', None]:
        talent = db.query(Talent).filter(Talent.keyword == keyword).order_by(Talent.scraped_at.desc()).offset(offset).limit(limit).all()

    if job_type in ['projects', None]:
        projects = db.query(Project).filter(Project.keyword == keyword).order_by(Project.scraped_at.desc()).offset(offset).limit(limit).all()

    return ResultsResponse(
        jobs=jobs,
        talent=talent,
        projects=projects,
        totals={
            "jobs": db.query(Job).filter(Job.keyword == keyword).count(),
            "talent": db.query(Talent).filter(Talent.keyword == keyword).count(),
            "projects": db.query(Project).filter(Project.keyword == keyword).count()
        }
    )


@app.get("/jobs", response_model=list[JobResponse])
async def get_jobs(
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all jobs or filter by keyword"""
    query = db.query(Job)
    if keyword:
        query = query.filter(Job.keyword == keyword)
    return query.order_by(Job.scraped_at.desc()).offset(offset).limit(limit).all()


@app.get("/talent", response_model=list[TalentResponse])
async def get_talent(
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all talent or filter by keyword"""
    query = db.query(Talent)
    if keyword:
        query = query.filter(Talent.keyword == keyword)
    return query.order_by(Talent.scraped_at.desc()).offset(offset).limit(limit).all()


@app.get("/projects", response_model=list[ProjectResponse])
async def get_projects(
    keyword: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all projects or filter by keyword"""
    query = db.query(Project)
    if keyword:
        query = query.filter(Project.keyword == keyword)
    return query.order_by(Project.scraped_at.desc()).offset(offset).limit(limit).all()


# Orchestrator v1 endpoints
@app.post("/v1/ingest/scan", response_model=IngestScanResponse)
def ingest_scan():
    """Scan ~/Downloads/upwork_dna recursively and refresh scoring outputs."""
    return run_db_operation_with_new_session(
        "v1_ingest_scan",
        lambda db: orchestrator.scan_and_ingest(db),
        write=False,
        retry_attempts=1,
    )


@app.post("/v1/ingest/run", response_model=RunIngestResponse)
def ingest_run(payload: RunIngestRequest):
    """Ingest a completed extension run payload directly (no file dependency)."""
    payload_dump = payload.model_dump()
    run_payload = payload.run if isinstance(payload.run, dict) else {}
    run_id = payload.run_id
    now = time.time()
    signature = _build_run_signature(run_payload)
    stats = _run_payload_stats(run_payload)
    is_final = _is_final_run(run_payload)

    tracker: dict = {}
    with RUN_INGEST_TRACKER_LOCK:
        tracker = RUN_INGEST_TRACKER.get(run_id, {}).copy()

    last_processed_at = float(tracker.get("last_processed_at", 0))
    last_total = int(tracker.get("last_total", 0))
    same_signature = signature == tracker.get("signature")
    recent_process = (now - last_processed_at) < RUN_INGEST_MIN_PROCESS_SECONDS
    growth = max(0, stats["total"] - last_total)

    if not is_final and tracker.get("last_response"):
        if same_signature and recent_process:
            return tracker["last_response"]
        if recent_process and growth < RUN_INGEST_MIN_NEW_ITEMS:
            return tracker["last_response"]

    last_refresh_at = float(tracker.get("last_refresh_at", 0))
    do_refresh = is_final or (now - last_refresh_at >= RUN_INGEST_REFRESH_SECONDS)

    try:
        response = _persist_run_ingest(run_id, payload_dump, is_final=is_final)
    except Exception as exc:  # noqa: BLE001
        _enqueue_run_ingest_retry(
            run_id=run_id,
            payload_dump=payload_dump,
            run_payload=run_payload,
            is_final=is_final,
            error=str(exc),
        )
        if tracker.get("last_response") and not is_final:
            logger.warning("[Ingest] Queued retry and using cached response for %s: %s", run_id, exc)
            return tracker["last_response"]
        logger.warning("[Ingest] Queued retry and using default response for %s: %s", run_id, exc)
        return _default_run_ingest_response(run_id, run_payload)

    _record_run_ingest_success(
        run_id=run_id,
        signature=signature,
        stats=stats,
        response=response,
        processed_at=now,
        is_final=is_final,
        did_refresh=do_refresh,
    )

    if do_refresh:
        trigger_background_refresh(f"ingest_run:{run_id}", mode="refresh")

    return response


@app.get("/v1/recommendations/keywords", response_model=list[KeywordRecommendationResponse])
def get_recommendations_keywords(
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    cache_key = f"v1_recommendations_keywords_{limit}"
    return run_db_read_with_fallback(
        cache_key,
        "v1_recommendations_keywords",
        lambda db: orchestrator.get_keyword_recommendations(db, limit=limit),
        default=[],
    )


@app.get("/v1/opportunities/jobs", response_model=list[JobOpportunityResponse])
def get_opportunity_jobs(
    limit: int = 100,
    safe_only: bool = False,
):
    limit = max(1, min(limit, 500))
    cache_key = f"v1_opportunities_jobs_{limit}_{int(bool(safe_only))}"
    return run_db_read_with_fallback(
        cache_key,
        "v1_opportunities_jobs",
        lambda db: orchestrator.get_job_opportunities(db, limit=limit, safe_only=safe_only),
        default=[],
    )


@app.get("/v1/opportunities/enriched", response_model=list[JobEnrichedResponse])
def get_enriched_jobs(
    limit: int = 100,
    safe_only: bool = False,
    keyword: str = None,
    apply_only: bool = False,
    fresh_only: bool = False,
    max_proposals: int = None,
):
    """Enriched jobs: opportunities + raw data (description, url, budget, skills).
    
    - fresh_only: if True, only jobs with < 30 proposals and scraped in last 72h
    - max_proposals: filter out jobs with more proposals than this
    """
    import json as _json
    from orchestrator import parse_int_value, compute_freshness_score
    limit = max(1, min(limit, 500))
    cache_key = f"v1_enriched_{limit}_{int(bool(safe_only))}_{keyword}_{int(bool(apply_only))}_{int(bool(fresh_only))}_{max_proposals}"

    def _read(db):
        from database import JobOpportunity, JobRaw
        query = db.query(JobOpportunity, JobRaw).outerjoin(
            JobRaw, JobOpportunity.job_key == JobRaw.job_key
        )
        if safe_only:
            query = query.filter(JobOpportunity.safety_score >= 70.0)
        if keyword:
            query = query.filter(JobOpportunity.keyword == keyword)
        if apply_only:
            query = query.filter(JobOpportunity.apply_now == True)

        # Fetch more rows than limit so we can re-rank client-side
        rows = query.order_by(
            JobOpportunity.apply_now.desc(),
            JobOpportunity.fit_score.desc(),
            JobOpportunity.opportunity_score.desc(),
        ).limit(limit * 3).all()

        out = []
        for opp, raw in rows:
            proposals_str = raw.proposals or "" if raw else ""
            proposals_num = parse_int_value(proposals_str)
            
            # ─── Freshness filter ─────────────────────
            if max_proposals is not None and proposals_num is not None:
                if proposals_num > max_proposals:
                    continue

            freshness = compute_freshness_score(
                proposals_str=proposals_str,
                scraped_at=raw.scraped_at if raw else None,
            )

            if fresh_only and freshness < 50:
                continue

            # ─── Compute effective display score ──────
            # If LLM-analyzed, use composite_score; else use fit_score with freshness penalty
            reasons_data = {}
            try:
                reasons_data = _json.loads(opp.reasons or "{}")
            except Exception:
                pass

            is_llm_analyzed = bool(
                isinstance(reasons_data, dict) and reasons_data.get("llm_action")
            )
            
            # LLM composite is already good; rule-based needs freshness adjustment
            effective_score = opp.fit_score or 0
            if not is_llm_analyzed:
                # Penalize rule-based scores by freshness lack
                effective_score = (effective_score * freshness) / 100.0

            out.append({
                "job_key": opp.job_key,
                "title": opp.title,
                "keyword": opp.keyword or (raw.keyword if raw else ""),
                "opportunity_score": round(opp.opportunity_score or 0, 2),
                "safety_score": round(opp.safety_score or 0, 2),
                "fit_score": round(effective_score, 2),
                "apply_now": bool(opp.apply_now),
                "reasons": opp.reasons or "[]",
                "description": (raw.description or "")[:500] if raw else "",
                "url": raw.url or "" if raw else "",
                "budget": raw.budget or "" if raw else "",
                "budget_value": raw.budget_value if raw else None,
                "client_spend": raw.client_spend if raw else None,
                "payment_verified": bool(raw.payment_verified) if raw else None,
                "proposals": raw.proposals or "" if raw else "",
                "skills": raw.skills or "" if raw else "",
                "scraped_at": str(raw.scraped_at) if raw and raw.scraped_at else None,
                "freshness": freshness,
            })

        # Re-sort: LLM-analyzed APPLY first, then by effective score
        out.sort(key=lambda x: (
            x["apply_now"],
            1 if (isinstance(_safe_json(x["reasons"]), dict) and _safe_json(x["reasons"]).get("llm_action")) else 0,
            x["fit_score"],
        ), reverse=True)

        return out[:limit]

    return run_db_read_with_fallback(cache_key, "v1_enriched", _read, default=[])


@app.get("/v1/opportunities/jobs/{job_key}/draft", response_model=ProposalDraftResponse)
def get_opportunity_job_draft(
    job_key: str,
):
    cache_key = f"v1_opportunity_job_draft_{job_key}"
    draft = run_db_read_with_fallback(
        cache_key,
        "v1_opportunity_job_draft",
        lambda db: orchestrator.get_job_draft(db, job_key=job_key),
        default=None,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.get("/v1/telemetry/queue", response_model=QueueTelemetryResponse)
def get_queue_telemetry():
    return run_db_read_with_fallback(
        "v1_telemetry_queue_get",
        "v1_telemetry_queue_get",
        lambda db: orchestrator.get_queue_telemetry(db),
        default=DEFAULT_QUEUE.copy(),
    )


@app.post("/v1/telemetry/queue", response_model=QueueTelemetryResponse)
def update_queue_telemetry(
    payload: QueueTelemetryUpdateRequest,
):
    try:
        return run_db_operation_with_new_session(
            "v1_telemetry_queue_post",
            lambda db: orchestrator.update_queue_telemetry(db, payload.model_dump()),
            write=True,
            retry_attempts=1,
            write_lock_timeout_seconds=1.0,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[QueueTelemetry] write skipped due to lock: %s", exc)
        return run_db_read_with_fallback(
            "v1_telemetry_queue_get",
            "v1_telemetry_queue_fallback_read",
            lambda db: orchestrator.get_queue_telemetry(db),
            default=DEFAULT_QUEUE.copy(),
        )


@app.get("/v1/telemetry/summary", response_model=OrchestratorSummaryResponse)
def get_orchestrator_summary():
    return run_db_read_with_fallback(
        "v1_telemetry_summary",
        "v1_telemetry_summary",
        lambda db: orchestrator.get_summary(db),
        default=DEFAULT_SUMMARY.copy(),
    )


@app.get("/v1/telemet")
def telemetry_shortcut():
    """Common typo helper for quick browser checks with live payload."""
    summary = run_db_read_with_fallback(
        "v1_telemetry_summary",
        "v1_telemet_summary",
        lambda db: orchestrator.get_summary(db),
        default=DEFAULT_SUMMARY.copy(),
    )
    queue = run_db_read_with_fallback(
        "v1_telemetry_queue_get",
        "v1_telemet_queue",
        lambda db: orchestrator.get_queue_telemetry(db),
        default=DEFAULT_QUEUE.copy(),
    )
    return {
        "hint": "Use /v1/telemetry/summary or /v1/telemetry/queue",
        "summary_endpoint": "/v1/telemetry/summary",
        "queue_endpoint": "/v1/telemetry/queue",
        "ingest_retry_queue": _ingest_retry_queue_size(),
        "summary": summary,
        "queue": queue,
    }


# System status endpoint
@app.get("/status", response_model=SystemStatusResponse)
def get_system_status():
    """Get system status"""
    # Check playwright installation
    playwright_installed = False
    try:
        from playwright.async_api import async_playwright
        playwright_installed = True
    except ImportError:
        pass

    def _collect_status(db: Session):
        db.execute(text("SELECT 1"))
        return {
            "queue_size": db.query(QueueItem).count(),
            "active_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == "running").count(),
            "completed_jobs": db.query(ScrapingJob).filter(ScrapingJob.status == "completed").count(),
        }

    database_connected = True
    queue_size = 0
    active_jobs = 0
    completed_jobs = 0
    try:
        stats = run_db_operation_with_new_session("status", _collect_status)
        queue_size = stats["queue_size"]
        active_jobs = stats["active_jobs"]
        completed_jobs = stats["completed_jobs"]
    except Exception:
        database_connected = False

    # Uptime
    uptime = str(datetime.utcnow() - START_TIME)

    return SystemStatusResponse(
        status="healthy" if database_connected else "unhealthy",
        version=API_VERSION,
        database_connected=database_connected,
        playwright_installed=playwright_installed,
        queue_size=queue_size,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        uptime=uptime
    )


# Health check
@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    try:
        run_db_operation_with_new_session("health", lambda db: db.execute(text("SELECT 1")))
        return {
            "status": "healthy",
            "database": "connected",
            "ingest_retry_queue": _ingest_retry_queue_size(),
        }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "ingest_retry_queue": _ingest_retry_queue_size(),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "True").lower() == "true"
    )
