"""
Local orchestrator service for ingest -> scoring -> recommendation cycle.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from database import (
    IngestedFile,
    JobRaw,
    JobOpportunity,
    KeywordMetric,
    KeywordRecommendation,
    PipelineEvent,
    ProposalDraft,
    ProjectRaw,
    QueueItem,
    QueueTelemetry,
    TalentRaw,
)


RECOMMENDATION_LIMIT_DEFAULT = 100
SUSPICIOUS_TERMS = {
    "telegram",
    "whatsapp",
    "crypto wallet",
    "upfront fee",
    "gift card",
    "wire transfer",
}

# ─── Profile-aware fit terms ────────────────────────────────
# These weights match the freelancer's actual skills from profile_config.
# Core skills = 14, secondary = 10, relevant extras = 8
FIT_TERM_WEIGHTS = {
    # Core skills (high weight)
    "python": 14,
    "n8n": 14,
    "fastapi": 14,
    "langchain": 14,
    "rag": 14,
    "ai agent": 14,
    "api integration": 14,
    "automation": 14,
    "web scraping": 14,
    "data extraction": 14,
    "etl": 14,
    "vector database": 14,
    "pinecone": 12,
    "chromadb": 12,
    "prompt engineering": 14,
    "chatbot": 14,
    "sql": 12,

    # Secondary skills (medium weight)
    "openai": 12,
    "workflow automation": 12,
    "data pipeline": 12,
    "automated workflow": 10,
    "process automation": 10,
    "excel automation": 10,
    "google sheets": 10,
    "data cleaning": 10,
    "pdf extraction": 10,
    "email extraction": 10,
    "reporting": 8,

    # Relevant ecosystem
    "llm": 12,
    "gpt": 10,
    "ai": 10,
    "machine learning": 8,
    "nlp": 8,
    "flask": 8,
    "scraping": 10,
    "selenium": 8,
    "beautifulsoup": 8,
    "pandas": 8,
    "agentic": 12,
    "crewai": 10,
    "langgraph": 12,
    "autogen": 10,

    # Negative weights — avoid
    "wordpress theme": -20,
    "graphic design": -20,
    "video editing": -20,
    "social media management": -15,
    "seo writing": -15,
    "content writing": -10,
    "react native": -10,
    "flutter": -10,
    "unity": -15,
    "game development": -15,
    "accounting": -15,
    "bookkeeping": -15,
}

# Staleness thresholds for proposals
PROPOSALS_FRESH_MAX = 15     # 0-15 proposals = fresh job
PROPOSALS_STALE_THRESHOLD = 30   # 30+ proposals = getting stale
PROPOSALS_DEAD_THRESHOLD = 50    # 50+ proposals = likely filled/expired


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def parse_money_value(value: Any) -> Optional[float]:
    """Extract numeric budget/rate value from mixed strings."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()
    if not text:
        return None

    text = text.replace(",", "")
    range_match = re.findall(r"(\d+(?:\.\d+)?)(k)?", text)
    if not range_match:
        return None

    numbers: List[float] = []
    for num, is_k in range_match:
        parsed = float(num)
        if is_k:
            parsed *= 1000
        numbers.append(parsed)

    if not numbers:
        return None
    return float(sum(numbers) / len(numbers))


def parse_int_value(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    match = re.search(r"\d+", str(value))
    if not match:
        return None
    return int(match.group(0))


def parse_bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "verified", "payment verified", "y"}


def pick_first(record: Dict[str, Any], candidates: Iterable[str], default: Any = "") -> Any:
    for key in candidates:
        if key in record and record[key] not in (None, "", "nan", "None"):
            return record[key]
    return default


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)
    return str(value)


def normalize_json_list(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "[]"
    try:
        return json.dumps(list(value), ensure_ascii=False)
    except Exception:
        return "[]"


def derive_job_key(url: str, title: str, keyword: str) -> str:
    if url:
        m = re.search(r"/jobs?/([^/?#]+)", url)
        if m:
            return m.group(1)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]
        return f"url_{slug}"
    raw = f"{title}|{keyword}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:20]


def derive_talent_key(url: str, name: str, keyword: str) -> str:
    if url:
        m = re.search(r"~[A-Za-z0-9]+", url)
        if m:
            return m.group(0)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]
        return f"url_{slug}"
    raw = f"{name}|{keyword}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:20]


def derive_project_key(url: str, title: str, keyword: str) -> str:
    if url:
        m = re.search(r"catalog/(\d+)", url)
        if m:
            return m.group(1)
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]
        return f"url_{slug}"
    raw = f"{title}|{keyword}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:20]


def infer_keyword_from_path(path: Path) -> str:
    stem = path.stem.lower()
    tokens = [t for t in stem.split("_") if t]
    ignore = {"upwork", "scrape", "jobs", "job", "talent", "projects", "project", "run"}
    tokens = [t for t in tokens if t not in ignore]

    cleaned: List[str] = []
    for token in tokens:
        if re.fullmatch(r"\d+", token):
            continue
        if re.fullmatch(r"\d{2}-\d{2}-\d{2}", token):
            continue
        cleaned.append(token)

    if cleaned:
        return " ".join(cleaned[:6])

    parent = path.parent.name
    parent = re.sub(r"_[0-9]{2}-[0-9]{2}-[0-9]{2}$", "", parent)
    parent = re.sub(r"_\d{8,}$", "", parent)
    parent = parent.replace("_", " ").strip()
    return parent or "general"


def detect_dataset_from_filename(path: Path) -> str:
    name = path.name.lower()
    if "jobs" in name:
        return "jobs"
    if "talent" in name:
        return "talent"
    if "project" in name:
        return "projects"
    if "scrape" in name:
        return "mixed"
    return "mixed"


def score_priority(opportunity_score: float) -> str:
    if opportunity_score >= 85:
        return "CRITICAL"
    if opportunity_score >= 70:
        return "HIGH"
    if opportunity_score >= 55:
        return "NORMAL"
    return "LOW"


def compute_fit_score(text: str) -> float:
    normalized = text.lower()
    weights = dict(FIT_TERM_WEIGHTS)

    # Dynamic keyword augmentation from synced Upwork profile
    try:
        from llm.profile_config import get_skills_for_matching, get_ideal_keywords

        for skill in get_skills_for_matching():
            term = str(skill).strip().lower()
            if term and term not in weights:
                weights[term] = 10
        for keyword in get_ideal_keywords():
            term = str(keyword).strip().lower()
            if term and term not in weights:
                weights[term] = 8
    except Exception:
        # Keep static weights as fallback.
        pass

    raw_score = 0.0
    for term, weight in weights.items():
        if term in normalized:
            raw_score += weight
    # Normalize: matching ~7 core skills (7*14=98) should be ~100%.
    # Use fixed cap of 100 so that 5+ matching terms = strong score.
    return round(clamp((raw_score / 100.0) * 100.0), 2)


def compute_freshness_score(proposals_str: str, scraped_at: datetime = None) -> float:
    """0-100 freshness score. Higher = fresher/more worth applying."""
    score = 100.0
    proposals = parse_int_value(proposals_str)

    # Proposals-based staleness (strongest signal)
    if proposals is not None:
        if proposals >= PROPOSALS_DEAD_THRESHOLD:
            score -= 60.0  # Very stale
        elif proposals >= PROPOSALS_STALE_THRESHOLD:
            score -= 35.0
        elif proposals >= PROPOSALS_FRESH_MAX:
            score -= 15.0
        # 0-5 proposals = bonus (very fresh)
        elif proposals <= 5:
            score += 0  # Already at 100

    # Scrape age penalty
    if scraped_at:
        try:
            if isinstance(scraped_at, str):
                scraped_at = datetime.fromisoformat(scraped_at.replace("Z", "+00:00").replace("+00:00", ""))
            age_hours = (datetime.utcnow() - scraped_at).total_seconds() / 3600
            if age_hours > 120:  # > 5 days
                score -= 30.0
            elif age_hours > 72:  # > 3 days
                score -= 15.0
            elif age_hours > 48:
                score -= 5.0
        except Exception:
            pass

    return round(clamp(score), 2)


def compute_safety_score(
    payment_verified: bool,
    client_spend: Optional[float],
    proposals: Optional[int],
    budget_value: Optional[float],
    description: str,
) -> float:
    score = 0.0

    score += 25.0 if payment_verified else 5.0

    spend = client_spend or 0.0
    if spend >= 10000:
        score += 20.0
    elif spend >= 1000:
        score += 15.0
    elif spend >= 100:
        score += 8.0

    if proposals is not None:
        if proposals <= 10:
            score += 15.0
        elif proposals <= 20:
            score += 10.0
        elif proposals <= 50:
            score += 3.0
        else:
            score -= 10.0

    if budget_value is not None:
        if budget_value < 10:
            score -= 20.0
        elif budget_value <= 30:
            score += 4.0
        elif budget_value <= 10000:
            score += 15.0
        else:
            score -= 5.0

    description_len = len((description or "").strip())
    if description_len >= 300:
        score += 15.0
    elif description_len >= 120:
        score += 10.0
    elif description_len >= 50:
        score += 5.0
    else:
        score -= 12.0

    desc_lower = (description or "").lower()
    if any(term in desc_lower for term in SUSPICIOUS_TERMS):
        score -= 40.0

    return round(clamp(score), 2)


class OrchestratorService:
    def __init__(self, data_root: Optional[str] = None):
        root = data_root or os.getenv(
            "UPWORK_DATA_ROOT",
            str(Path.home() / "Downloads" / "upwork_dna"),
        )
        self.data_root = Path(root).expanduser()
        self.data_root.mkdir(parents=True, exist_ok=True)

    def scan_and_ingest(self, db: Session) -> Dict[str, Any]:
        files = [
            p
            for p in self.data_root.rglob("*")
            if p.is_file() and p.suffix.lower() in {".csv", ".json"}
        ]
        scanned = 0
        created = 0
        updated = 0

        for file_path in files:
            scanned += 1
            payload_hash = self._compute_file_hash(file_path)
            rel_path = str(file_path)
            stats = file_path.stat()
            existing = (
                db.query(IngestedFile)
                .filter(IngestedFile.file_path == rel_path)
                .first()
            )

            if existing and existing.file_hash == payload_hash:
                continue

            parsed = self._parse_file(file_path)
            if parsed["jobs"]:
                self._upsert_jobs(db, parsed["jobs"], rel_path)
            if parsed["talent"]:
                self._upsert_talent(db, parsed["talent"], rel_path)
            if parsed["projects"]:
                self._upsert_projects(db, parsed["projects"], rel_path)

            dataset = detect_dataset_from_filename(file_path)
            inferred_keyword = parsed["keyword"] or infer_keyword_from_path(file_path)
            row_count = (
                len(parsed["jobs"]) + len(parsed["talent"]) + len(parsed["projects"])
            )

            if existing:
                existing.file_hash = payload_hash
                existing.file_type = file_path.suffix.lower().lstrip(".")
                existing.dataset = dataset
                existing.keyword = inferred_keyword
                existing.row_count = row_count
                existing.last_modified_at = datetime.utcfromtimestamp(stats.st_mtime)
                existing.ingested_at = datetime.utcnow()
                updated += 1
            else:
                db.add(
                    IngestedFile(
                        file_path=rel_path,
                        file_hash=payload_hash,
                        file_type=file_path.suffix.lower().lstrip("."),
                        dataset=dataset,
                        keyword=inferred_keyword,
                        row_count=row_count,
                        last_modified_at=datetime.utcfromtimestamp(stats.st_mtime),
                    )
                )
                created += 1

            # Keep write locks short; commit each changed file chunk.
            db.flush()
            db.commit()

        refreshed_at = self.refresh_metrics_and_opportunities(db)

        event_payload = {
            "scanned_files": scanned,
            "new_files": created,
            "updated_files": updated,
            "refreshed_at": refreshed_at.isoformat(),
        }
        self._log_event(db, "ingest_scan", event_payload)
        db.commit()

        return {
            "scanned_files": scanned,
            "new_files": created,
            "updated_files": updated,
            "updated_metrics_at": refreshed_at.isoformat(),
        }

    def ingest_run_payload(
        self,
        db: Session,
        run_id: str,
        run_payload: Dict[str, Any],
        refresh_metrics: bool = True,
    ) -> Dict[str, Any]:
        run = run_payload.get("run") if isinstance(run_payload, dict) and "run" in run_payload else run_payload
        run = run if isinstance(run, dict) else {}
        keyword = normalize_text(run.get("keyword", "")).strip() or "general"
        data = run.get("data") if isinstance(run.get("data"), dict) else {}

        jobs_rows: List[Dict[str, Any]] = []
        talent_rows: List[Dict[str, Any]] = []
        project_rows: List[Dict[str, Any]] = []

        for row in data.get("jobs", []) if isinstance(data.get("jobs"), list) else []:
            if not isinstance(row, dict):
                continue
            normalized = {str(k).lower(): v for k, v in row.items()}
            row_keyword = normalize_text(pick_first(normalized, ["keyword", "search_keyword"], keyword)).strip() or keyword
            jobs_rows.append(self._normalize_job_row(normalized, row_keyword))

        for row in data.get("talent", []) if isinstance(data.get("talent"), list) else []:
            if not isinstance(row, dict):
                continue
            normalized = {str(k).lower(): v for k, v in row.items()}
            row_keyword = normalize_text(pick_first(normalized, ["keyword", "search_keyword"], keyword)).strip() or keyword
            talent_rows.append(self._normalize_talent_row(normalized, row_keyword))

        for row in data.get("projects", []) if isinstance(data.get("projects"), list) else []:
            if not isinstance(row, dict):
                continue
            normalized = {str(k).lower(): v for k, v in row.items()}
            row_keyword = normalize_text(pick_first(normalized, ["keyword", "search_keyword"], keyword)).strip() or keyword
            project_rows.append(self._normalize_project_row(normalized, row_keyword))

        source = f"extension_run:{run_id}"
        if jobs_rows:
            self._upsert_jobs(db, jobs_rows, source)
        if talent_rows:
            self._upsert_talent(db, talent_rows, source)
        if project_rows:
            self._upsert_projects(db, project_rows, source)

        db.commit()
        refreshed_at = datetime.utcnow()
        if refresh_metrics:
            refreshed_at = self.refresh_metrics_and_opportunities(db)

        event_payload = {
            "run_id": run_id,
            "keyword": keyword,
            "jobs_ingested": len(jobs_rows),
            "talent_ingested": len(talent_rows),
            "projects_ingested": len(project_rows),
            "refresh_metrics": refresh_metrics,
            "updated_metrics_at": refreshed_at.isoformat(),
        }
        self._log_event(db, "ingest_run_payload", event_payload)
        db.commit()

        return event_payload

    def refresh_metrics_and_opportunities(self, db: Session) -> datetime:
        refreshed_at = datetime.utcnow()
        keywords = {
            row.keyword
            for row in db.query(JobRaw.keyword).filter(JobRaw.keyword.isnot(None)).all()
            if row.keyword
        }
        keywords.update(
            {
                row.keyword
                for row in db.query(TalentRaw.keyword)
                .filter(TalentRaw.keyword.isnot(None))
                .all()
                if row.keyword
            }
        )

        for keyword in keywords:
            self._refresh_keyword_metric(db, keyword, refreshed_at)
        self._refresh_job_opportunities(db, refreshed_at)
        db.commit()
        return refreshed_at

    def _refresh_keyword_metric(self, db: Session, keyword: str, refreshed_at: datetime) -> None:
        jobs = db.query(JobRaw).filter(JobRaw.keyword == keyword).all()
        talent = db.query(TalentRaw).filter(TalentRaw.keyword == keyword).all()

        demand = len(jobs)
        supply = len(talent)
        gap_ratio = float(demand / max(supply, 1))
        budgets = [j.budget_value for j in jobs if j.budget_value is not None]
        budget_avg = float(sum(budgets) / len(budgets)) if budgets else 0.0

        competition_inverse = clamp(100.0 - min(90.0, supply * 4.0))
        now = datetime.utcnow()
        recent_jobs = sum(
            1 for j in jobs if j.scraped_at and j.scraped_at >= now - timedelta(days=7)
        )
        older_jobs = max(0, demand - recent_jobs)
        trend_ratio = (recent_jobs + 1) / (older_jobs + 1)
        trend_score = clamp(trend_ratio * 35.0)

        demand_score = clamp(demand * 5.0)
        gap_score = clamp(gap_ratio * 20.0)
        budget_score = clamp(budget_avg / 20.0)
        opportunity_score = round(
            demand_score * 0.30
            + gap_score * 0.25
            + budget_score * 0.20
            + competition_inverse * 0.15
            + trend_score * 0.10,
            2,
        )

        priority = score_priority(opportunity_score)
        reasons: List[str] = []
        if demand >= 20:
            reasons.append("HIGH_DEMAND")
        if gap_ratio >= 2:
            reasons.append("SUPPLY_GAP")
        if budget_avg >= 500:
            reasons.append("HIGH_BUDGET")
        if competition_inverse >= 70:
            reasons.append("LOW_COMPETITION")
        if trend_score >= 60:
            reasons.append("RISING_TREND")
        if not reasons:
            reasons.append("BASELINE_SIGNAL")

        metric = db.query(KeywordMetric).filter(KeywordMetric.keyword == keyword).first()
        if not metric:
            metric = KeywordMetric(keyword=keyword)
            db.add(metric)
        metric.demand = demand
        metric.supply = supply
        metric.gap_ratio = round(gap_ratio, 4)
        metric.budget_avg = round(budget_avg, 2)
        metric.competition_inverse = round(competition_inverse, 2)
        metric.trend_score = round(trend_score, 2)
        metric.opportunity_score = opportunity_score
        metric.recommended_priority = priority
        metric.last_updated = refreshed_at

        recommendation = (
            db.query(KeywordRecommendation)
            .filter(KeywordRecommendation.keyword == keyword)
            .first()
        )
        if not recommendation:
            recommendation = KeywordRecommendation(keyword=keyword)
            db.add(recommendation)
        recommendation.recommended_priority = priority
        recommendation.opportunity_score = opportunity_score
        recommendation.demand = demand
        recommendation.supply = supply
        recommendation.gap_ratio = round(gap_ratio, 4)
        recommendation.reason_codes = json.dumps(reasons, ensure_ascii=False)
        recommendation.last_updated = refreshed_at

    def _refresh_job_opportunities(self, db: Session, refreshed_at: datetime) -> None:
        keyword_scores = {
            item.keyword: item.opportunity_score
            for item in db.query(KeywordRecommendation).all()
        }

        jobs = db.query(JobRaw).all()
        for job in jobs:
            keyword_score = keyword_scores.get(job.keyword or "", 50.0)
            budget_score = clamp((job.budget_value or 0.0) / 20.0)
            opportunity_score = round(keyword_score * 0.7 + budget_score * 0.3, 2)

            safety_score = compute_safety_score(
                payment_verified=bool(job.payment_verified),
                client_spend=job.client_spend,
                proposals=parse_int_value(job.proposals),
                budget_value=job.budget_value,
                description=job.description or "",
            )

            fit_blob = " ".join(
                [
                    normalize_text(job.title),
                    normalize_text(job.description),
                    normalize_text(job.skills),
                    normalize_text(job.keyword),
                ]
            )
            fit_score = compute_fit_score(fit_blob)

            # ─── Freshness scoring ────────────────────────────
            freshness = compute_freshness_score(
                proposals_str=job.proposals or "0",
                scraped_at=job.scraped_at,
            )

            # ─── Profile-aware apply_now (stricter) ──────────
            proposals_num = parse_int_value(job.proposals)
            is_stale = (proposals_num is not None and proposals_num >= PROPOSALS_STALE_THRESHOLD)
            is_dead = (proposals_num is not None and proposals_num >= PROPOSALS_DEAD_THRESHOLD)

            # Never recommend stale/dead jobs for immediate apply
            apply_now = bool(
                safety_score >= 70
                and fit_score >= 60
                and opportunity_score >= 55
                and freshness >= 50  # must be reasonably fresh
                and not is_dead  # never recommend 50+ proposal jobs
            )
            reasons = self._build_job_reasons(
                opportunity_score=opportunity_score,
                safety_score=safety_score,
                fit_score=fit_score,
                apply_now=apply_now,
            )
            # Add freshness info to reasons
            if is_dead:
                reasons.append("⚠️ 50+ proposals — iş muhtemelen dolmuş")
            elif is_stale:
                reasons.append("⏳ 30+ proposals — rekabet yüksek")

            entry = (
                db.query(JobOpportunity).filter(JobOpportunity.job_key == job.job_key).first()
            )
            # Skip overwriting if LLM already analyzed this job
            if entry and entry.reasons:
                try:
                    existing_reasons = json.loads(entry.reasons)
                    if isinstance(existing_reasons, dict) and existing_reasons.get("llm_action"):
                        # LLM has already analyzed — only update freshness-related fields
                        if is_dead:
                            entry.apply_now = False  # Override: dead jobs can't be APPLY
                        entry.last_updated = refreshed_at
                        continue
                except Exception:
                    pass

            if not entry:
                entry = JobOpportunity(job_key=job.job_key, title=job.title)
                db.add(entry)

            entry.title = job.title or "Untitled job"
            entry.keyword = job.keyword or "general"
            entry.opportunity_score = opportunity_score
            entry.safety_score = safety_score
            entry.fit_score = fit_score
            entry.apply_now = apply_now
            entry.reasons = json.dumps(reasons, ensure_ascii=False)
            entry.last_updated = refreshed_at

            draft = (
                db.query(ProposalDraft).filter(ProposalDraft.job_key == job.job_key).first()
            )
            if not draft:
                draft = ProposalDraft(job_key=job.job_key, cover_letter_draft="")
                db.add(draft)

            generated_draft = self._build_rule_based_draft(job, fit_score, safety_score)
            draft.cover_letter_draft = generated_draft["cover_letter_draft"]
            draft.hook_points = json.dumps(
                generated_draft["hook_points"], ensure_ascii=False
            )
            draft.caution_notes = json.dumps(
                generated_draft["caution_notes"], ensure_ascii=False
            )
            draft.updated_at = refreshed_at

    def get_keyword_recommendations(
        self, db: Session, limit: int = RECOMMENDATION_LIMIT_DEFAULT
    ) -> List[Dict[str, Any]]:
        rows = (
            db.query(KeywordRecommendation)
            .order_by(KeywordRecommendation.opportunity_score.desc())
            .limit(limit)
            .all()
        )
        output = []
        for row in rows:
            try:
                reason_codes = json.loads(row.reason_codes or "[]")
            except json.JSONDecodeError:
                reason_codes = []
            output.append(
                {
                    "keyword": row.keyword,
                    "recommended_priority": row.recommended_priority,
                    "opportunity_score": round(row.opportunity_score or 0.0, 2),
                    "demand": int(row.demand or 0),
                    "supply": int(row.supply or 0),
                    "gap_ratio": round(row.gap_ratio or 0.0, 4),
                    "reason_codes": reason_codes,
                }
            )
        return output

    def get_job_opportunities(
        self,
        db: Session,
        limit: int = RECOMMENDATION_LIMIT_DEFAULT,
        safe_only: bool = False,
    ) -> List[Dict[str, Any]]:
        query = db.query(JobOpportunity)
        if safe_only:
            query = query.filter(JobOpportunity.safety_score >= 70.0)
        rows = query.order_by(JobOpportunity.apply_now.desc(), JobOpportunity.fit_score.desc(), JobOpportunity.opportunity_score.desc()).limit(limit).all()
        output = []
        for row in rows:
            try:
                reasons = json.loads(row.reasons or "[]")
            except json.JSONDecodeError:
                reasons = []
            output.append(
                {
                    "job_key": row.job_key,
                    "title": row.title,
                    "keyword": row.keyword,
                    "opportunity_score": round(row.opportunity_score or 0.0, 2),
                    "safety_score": round(row.safety_score or 0.0, 2),
                    "fit_score": round(row.fit_score or 0.0, 2),
                    "apply_now": bool(row.apply_now),
                    "reasons": reasons,
                }
            )
        return output

    def get_job_draft(self, db: Session, job_key: str) -> Optional[Dict[str, Any]]:
        draft = db.query(ProposalDraft).filter(ProposalDraft.job_key == job_key).first()
        if not draft:
            return None
        try:
            hook_points = json.loads(draft.hook_points or "[]")
        except json.JSONDecodeError:
            hook_points = []
        try:
            caution_notes = json.loads(draft.caution_notes or "[]")
        except json.JSONDecodeError:
            caution_notes = []
        return {
            "job_key": job_key,
            "cover_letter_draft": draft.cover_letter_draft,
            "hook_points": hook_points,
            "caution_notes": caution_notes,
        }

    def update_queue_telemetry(self, db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
        row = db.query(QueueTelemetry).order_by(QueueTelemetry.id.asc()).first()
        if not row:
            row = QueueTelemetry()
            db.add(row)

        row.total = int(payload.get("total", 0))
        row.pending = int(payload.get("pending", 0))
        row.running = int(payload.get("running", 0))
        row.completed = int(payload.get("completed", 0))
        row.error = int(payload.get("error", 0))
        cycle = payload.get("last_cycle_at")
        if isinstance(cycle, str):
            try:
                row.last_cycle_at = datetime.fromisoformat(cycle.replace("Z", "+00:00"))
            except ValueError:
                row.last_cycle_at = datetime.utcnow()
        elif isinstance(cycle, datetime):
            row.last_cycle_at = cycle
        else:
            row.last_cycle_at = datetime.utcnow()
        db.flush()

        self._log_event(db, "queue_telemetry", payload)
        db.commit()
        return self.get_queue_telemetry(db)

    def get_queue_telemetry(self, db: Session) -> Dict[str, Any]:
        row = db.query(QueueTelemetry).order_by(QueueTelemetry.id.asc()).first()
        if row:
            last_cycle = (
                row.last_cycle_at.isoformat() if row.last_cycle_at else None
            )
            return {
                "total": int(row.total or 0),
                "pending": int(row.pending or 0),
                "running": int(row.running or 0),
                "completed": int(row.completed or 0),
                "error": int(row.error or 0),
                "last_cycle_at": last_cycle,
            }

        # Backward-compatible fallback: derive from backend queue table
        total = db.query(QueueItem).count()
        pending = db.query(QueueItem).filter(QueueItem.status == "pending").count()
        running = db.query(QueueItem).filter(QueueItem.status == "running").count()
        completed = db.query(QueueItem).filter(QueueItem.status == "completed").count()
        error = db.query(QueueItem).filter(QueueItem.status == "failed").count()
        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "error": error,
            "last_cycle_at": None,
        }

    def get_summary(self, db: Session) -> Dict[str, Any]:
        latest_ingest = (
            db.query(IngestedFile)
            .order_by(IngestedFile.ingested_at.desc())
            .first()
        )
        latest_pipeline_ingest = (
            db.query(PipelineEvent)
            .filter(PipelineEvent.event_type.in_(["ingest_scan", "ingest_run_payload"]))
            .order_by(PipelineEvent.created_at.desc())
            .first()
        )
        last_ingest_at = latest_ingest.ingested_at if latest_ingest else None
        if latest_pipeline_ingest and (
            not last_ingest_at or latest_pipeline_ingest.created_at > last_ingest_at
        ):
            last_ingest_at = latest_pipeline_ingest.created_at
        return {
            "jobs_raw": db.query(JobRaw).count(),
            "talent_raw": db.query(TalentRaw).count(),
            "projects_raw": db.query(ProjectRaw).count(),
            "keywords": db.query(KeywordRecommendation).count(),
            "opportunities": db.query(JobOpportunity).count(),
            "last_ingest_at": last_ingest_at.isoformat() if last_ingest_at else None,
        }

    def _build_job_reasons(
        self,
        opportunity_score: float,
        safety_score: float,
        fit_score: float,
        apply_now: bool,
    ) -> List[str]:
        reasons = []
        if opportunity_score >= 70:
            reasons.append("HIGH_OPPORTUNITY")
        if safety_score >= 70:
            reasons.append("SAFE_CLIENT")
        elif safety_score < 50:
            reasons.append("AVOID_RISK")
        else:
            reasons.append("REVIEW_REQUIRED")
        if fit_score >= 70:
            reasons.append("STRONG_AI_DATA_FIT")
        elif fit_score >= 55:
            reasons.append("PARTIAL_AI_DATA_FIT")
        if apply_now:
            reasons.append("APPLY_NOW")
        return reasons

    def _build_rule_based_draft(
        self,
        job: JobRaw,
        fit_score: float,
        safety_score: float,
    ) -> Dict[str, Any]:
        text_blob = " ".join(
            [normalize_text(job.title), normalize_text(job.description), normalize_text(job.skills)]
        ).lower()
        hooks = [term for term in FIT_TERM_WEIGHTS if term in text_blob][:5]
        if not hooks:
            hooks = ["data analysis", "python", "dashboarding"]

        caution_notes = []
        if safety_score < 70:
            caution_notes.append("Client requires manual review before applying.")
        if parse_int_value(job.proposals) and parse_int_value(job.proposals) > 50:
            caution_notes.append("High proposal volume; personalize first paragraph.")
        if (job.budget_value or 0) < 30:
            caution_notes.append("Low budget signal; verify scope before submitting.")

        greeting = "Hello,"
        opening = (
            f"I can help deliver this {job.title or 'project'} with measurable outcomes in "
            f"AI/data workflows."
        )
        value_line = (
            f"My strongest overlap with your scope: {', '.join(hooks[:3])}. "
            f"I focus on production-grade Python + analytics delivery."
        )
        close_line = (
            "If useful, I can send a short execution plan with milestones and acceptance criteria."
        )
        fit_note = f"(Fit score: {fit_score:.1f}/100)"
        draft = "\n\n".join([greeting, opening, value_line, close_line, fit_note])

        return {
            "cover_letter_draft": draft,
            "hook_points": hooks,
            "caution_notes": caution_notes,
        }

    def _compute_file_hash(self, file_path: Path) -> str:
        sha = hashlib.sha1()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _parse_file(self, file_path: Path) -> Dict[str, Any]:
        if file_path.suffix.lower() == ".csv":
            return self._parse_csv_file(file_path)
        return self._parse_json_file(file_path)

    def _parse_csv_file(self, file_path: Path) -> Dict[str, Any]:
        dataset = detect_dataset_from_filename(file_path)
        keyword = infer_keyword_from_path(file_path)
        jobs: List[Dict[str, Any]] = []
        talent: List[Dict[str, Any]] = []
        projects: List[Dict[str, Any]] = []

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    normalized = {str(k).strip().lower(): v for k, v in row.items() if k}
                    record_keyword = (
                        normalize_text(
                            pick_first(
                                normalized,
                                ["keyword", "search_keyword", "query", "target_keyword"],
                                keyword,
                            )
                        ).strip()
                        or keyword
                    )
                    if dataset == "jobs":
                        jobs.append(self._normalize_job_row(normalized, record_keyword))
                    elif dataset == "talent":
                        talent.append(self._normalize_talent_row(normalized, record_keyword))
                    elif dataset == "projects":
                        projects.append(
                            self._normalize_project_row(normalized, record_keyword)
                        )
                    else:
                        # mixed CSV fallback
                        if "hourly_rate" in normalized or "jobs_completed" in normalized:
                            talent.append(
                                self._normalize_talent_row(normalized, record_keyword)
                            )
                        elif "sales" in normalized or "category" in normalized:
                            projects.append(
                                self._normalize_project_row(normalized, record_keyword)
                            )
                        else:
                            jobs.append(self._normalize_job_row(normalized, record_keyword))
        except Exception:
            return {"keyword": keyword, "jobs": [], "talent": [], "projects": []}

        return {
            "keyword": keyword,
            "jobs": jobs,
            "talent": talent,
            "projects": projects,
        }

    def _parse_json_file(self, file_path: Path) -> Dict[str, Any]:
        keyword = infer_keyword_from_path(file_path)
        jobs: List[Dict[str, Any]] = []
        talent: List[Dict[str, Any]] = []
        projects: List[Dict[str, Any]] = []

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            return {"keyword": keyword, "jobs": [], "talent": [], "projects": []}

        if isinstance(payload, list):
            dataset = detect_dataset_from_filename(file_path)
            if dataset == "jobs":
                jobs = [
                    self._normalize_job_row(
                        {str(k).lower(): v for k, v in item.items()},
                        keyword,
                    )
                    for item in payload
                    if isinstance(item, dict)
                ]
            elif dataset == "talent":
                talent = [
                    self._normalize_talent_row(
                        {str(k).lower(): v for k, v in item.items()},
                        keyword,
                    )
                    for item in payload
                    if isinstance(item, dict)
                ]
            else:
                projects = [
                    self._normalize_project_row(
                        {str(k).lower(): v for k, v in item.items()},
                        keyword,
                    )
                    for item in payload
                    if isinstance(item, dict)
                ]
            return {"keyword": keyword, "jobs": jobs, "talent": talent, "projects": projects}

        if isinstance(payload, dict):
            source_keyword = normalize_text(
                payload.get("keyword") or payload.get("search_keyword") or keyword
            ).strip() or keyword
            for item in payload.get("jobs", []):
                if isinstance(item, dict):
                    jobs.append(
                        self._normalize_job_row(
                            {str(k).lower(): v for k, v in item.items()},
                            source_keyword,
                        )
                    )
            for item in payload.get("talent", []):
                if isinstance(item, dict):
                    talent.append(
                        self._normalize_talent_row(
                            {str(k).lower(): v for k, v in item.items()},
                            source_keyword,
                        )
                    )
            for item in payload.get("projects", []):
                if isinstance(item, dict):
                    projects.append(
                        self._normalize_project_row(
                            {str(k).lower(): v for k, v in item.items()},
                            source_keyword,
                        )
                    )

        return {"keyword": keyword, "jobs": jobs, "talent": talent, "projects": projects}

    def _normalize_job_row(self, row: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        title = normalize_text(pick_first(row, ["title", "job_title"], "Untitled job")).strip()
        description = normalize_text(
            pick_first(
                row,
                [
                    "description",
                    "snippet",
                    "summary",
                    "detail_summary",
                    "detail_description",
                    "overview",
                ],
                "",
            )
        )
        signal_map = [
            ("job_availability", ["detail_job_availability"]),
            ("posted", ["detail_posted", "posted", "posted_date"]),
            ("activity_last_viewed", ["detail_activity_last_viewed"]),
            ("activity_interviewing", ["detail_activity_interviewing"]),
            ("activity_invites_sent", ["detail_activity_invites_sent"]),
            ("activity_unanswered_invites", ["detail_activity_unanswered_invites"]),
            ("activity_proposals", ["detail_activity_proposals"]),
            ("client_hire_rate", ["detail_client_hire_rate"]),
            ("client_jobs_posted", ["detail_client_jobs_posted"]),
            ("client_open_jobs", ["detail_client_open_jobs"]),
            ("client_member_since", ["detail_client_member_since"]),
        ]
        signal_lines = []
        for label, aliases in signal_map:
            value = normalize_text(pick_first(row, aliases, "")).strip()
            if value:
                signal_lines.append(f"{label}: {value}")
        if signal_lines:
            description = (
                f"{description}\n\n[market_signals]\n" + "\n".join(signal_lines)
            ).strip()
        url = normalize_text(
            pick_first(row, ["url", "job_url", "detail_job_url", "detail_url"], "")
        ).strip()
        budget = normalize_text(
            pick_first(row, ["budget", "hourly_rate", "price", "payment"], "")
        ).strip()
        client_spend = parse_money_value(
            pick_first(row, ["client_spend", "spent", "client_total_spent"], None)
        )
        payment_verified = parse_bool_value(
            pick_first(
                row,
                [
                    "payment_verified",
                    "client_payment_verified",
                    "is_payment_verified",
                ],
                False,
            )
        )
        proposals = pick_first(row, ["proposals", "proposal_count", "bids"], None)
        skills = normalize_text(pick_first(row, ["skills", "skill_tags", "tags"], ""))
        record_keyword = (
            normalize_text(
                pick_first(row, ["keyword", "search_keyword", "query"], keyword)
            ).strip()
            or keyword
        )
        scraped_at = self._parse_datetime(
            pick_first(row, ["scraped_at", "timestamp", "created_at"], None)
        )

        return {
            "job_key": derive_job_key(url, title, record_keyword),
            "keyword": record_keyword,
            "title": title,
            "description": description,
            "url": url,
            "budget": budget,
            "budget_value": parse_money_value(budget),
            "client_spend": client_spend,
            "payment_verified": payment_verified,
            "proposals": normalize_text(proposals) if proposals is not None else None,
            "skills": skills,
            "scraped_at": scraped_at,
        }

    def _normalize_talent_row(self, row: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        name = normalize_text(pick_first(row, ["name", "full_name"], "")).strip()
        title = normalize_text(pick_first(row, ["title", "headline"], "")).strip()
        description = normalize_text(
            pick_first(row, ["description", "overview", "bio", "summary"], "")
        )
        url = normalize_text(
            pick_first(row, ["url", "profile_url", "detail_profile_url"], "")
        ).strip()
        hourly_rate = normalize_text(pick_first(row, ["hourly_rate", "rate", "price"], ""))
        skills = normalize_text(pick_first(row, ["skills", "tags"], ""))
        record_keyword = (
            normalize_text(pick_first(row, ["keyword", "search_keyword"], keyword)).strip()
            or keyword
        )
        scraped_at = self._parse_datetime(
            pick_first(row, ["scraped_at", "timestamp", "created_at"], None)
        )

        return {
            "talent_key": derive_talent_key(url, name or title, record_keyword),
            "keyword": record_keyword,
            "name": name,
            "title": title,
            "description": description,
            "url": url,
            "hourly_rate": hourly_rate,
            "hourly_rate_value": parse_money_value(hourly_rate),
            "skills": skills,
            "country": normalize_text(pick_first(row, ["country", "location"], "")),
            "rating": self._parse_float(pick_first(row, ["rating", "score"], None)),
            "jobs_completed": parse_int_value(pick_first(row, ["jobs_completed", "jobs"], None)),
            "scraped_at": scraped_at,
        }

    def _normalize_project_row(self, row: Dict[str, Any], keyword: str) -> Dict[str, Any]:
        title = normalize_text(pick_first(row, ["title", "project_title"], "Untitled project"))
        description = normalize_text(
            pick_first(row, ["description", "summary", "detail_project_description"], "")
        )
        url = normalize_text(
            pick_first(row, ["url", "project_url", "detail_project_url"], "")
        ).strip()
        price = normalize_text(pick_first(row, ["price", "budget"], ""))
        record_keyword = (
            normalize_text(pick_first(row, ["keyword", "search_keyword"], keyword)).strip()
            or keyword
        )
        scraped_at = self._parse_datetime(
            pick_first(row, ["scraped_at", "timestamp", "created_at"], None)
        )
        return {
            "project_key": derive_project_key(url, title, record_keyword),
            "keyword": record_keyword,
            "title": title,
            "description": description,
            "url": url,
            "category": normalize_text(pick_first(row, ["category", "service_category"], "")),
            "price": price,
            "price_value": parse_money_value(price),
            "rating": self._parse_float(pick_first(row, ["rating", "score"], None)),
            "sales": parse_int_value(pick_first(row, ["sales", "orders"], None)),
            "scraped_at": scraped_at,
        }

    def _upsert_jobs(self, db: Session, records: List[Dict[str, Any]], source_file: str) -> None:
        unique_rows: Dict[str, Dict[str, Any]] = {}
        for row in records:
            key = normalize_text(row.get("job_key")).strip()
            if not key:
                continue
            unique_rows[key] = row
        if not unique_rows:
            return

        keys = list(unique_rows.keys())
        existing = (
            db.query(JobRaw)
            .filter(JobRaw.job_key.in_(keys))
            .all()
        )
        existing_map = {item.job_key: item for item in existing}

        for key, row in unique_rows.items():
            entry = existing_map.get(key)
            if not entry:
                entry = JobRaw(job_key=key, title=row["title"] or "Untitled job")
                db.add(entry)
                existing_map[key] = entry
            changed = False
            changed = self._set_if_changed(entry, "keyword", row["keyword"]) or changed
            changed = self._set_if_changed(entry, "title", row["title"] or "Untitled job") or changed
            changed = self._set_if_changed(entry, "description", row["description"]) or changed
            changed = self._set_if_changed(entry, "url", row["url"]) or changed
            changed = self._set_if_changed(entry, "budget", row["budget"]) or changed
            changed = self._set_if_changed(entry, "budget_value", row["budget_value"]) or changed
            changed = self._set_if_changed(entry, "client_spend", row["client_spend"]) or changed
            changed = self._set_if_changed(entry, "payment_verified", bool(row["payment_verified"])) or changed
            changed = self._set_if_changed(entry, "proposals", row["proposals"]) or changed
            changed = self._set_if_changed(entry, "skills", row["skills"]) or changed
            changed = self._set_if_changed(entry, "source_file", source_file) or changed

            new_scraped_at = row["scraped_at"] or entry.scraped_at or datetime.utcnow()
            if entry.scraped_at is None or (new_scraped_at and new_scraped_at > entry.scraped_at):
                entry.scraped_at = new_scraped_at
                changed = True

            if changed:
                entry.scraped_at = entry.scraped_at or datetime.utcnow()

    def _upsert_talent(self, db: Session, records: List[Dict[str, Any]], source_file: str) -> None:
        unique_rows: Dict[str, Dict[str, Any]] = {}
        for row in records:
            key = normalize_text(row.get("talent_key")).strip()
            if not key:
                continue
            unique_rows[key] = row
        if not unique_rows:
            return

        keys = list(unique_rows.keys())
        existing = (
            db.query(TalentRaw)
            .filter(TalentRaw.talent_key.in_(keys))
            .all()
        )
        existing_map = {item.talent_key: item for item in existing}

        for key, row in unique_rows.items():
            entry = existing_map.get(key)
            if not entry:
                entry = TalentRaw(talent_key=key)
                db.add(entry)
                existing_map[key] = entry
            changed = False
            changed = self._set_if_changed(entry, "keyword", row["keyword"]) or changed
            changed = self._set_if_changed(entry, "name", row["name"]) or changed
            changed = self._set_if_changed(entry, "title", row["title"]) or changed
            changed = self._set_if_changed(entry, "description", row["description"]) or changed
            changed = self._set_if_changed(entry, "url", row["url"]) or changed
            changed = self._set_if_changed(entry, "hourly_rate", row["hourly_rate"]) or changed
            changed = self._set_if_changed(entry, "hourly_rate_value", row["hourly_rate_value"]) or changed
            changed = self._set_if_changed(entry, "skills", row["skills"]) or changed
            changed = self._set_if_changed(entry, "country", row["country"]) or changed
            changed = self._set_if_changed(entry, "rating", row["rating"]) or changed
            changed = self._set_if_changed(entry, "jobs_completed", row["jobs_completed"]) or changed
            changed = self._set_if_changed(entry, "source_file", source_file) or changed

            new_scraped_at = row["scraped_at"] or entry.scraped_at or datetime.utcnow()
            if entry.scraped_at is None or (new_scraped_at and new_scraped_at > entry.scraped_at):
                entry.scraped_at = new_scraped_at
                changed = True

            if changed:
                entry.scraped_at = entry.scraped_at or datetime.utcnow()

    def _upsert_projects(self, db: Session, records: List[Dict[str, Any]], source_file: str) -> None:
        unique_rows: Dict[str, Dict[str, Any]] = {}
        for row in records:
            key = normalize_text(row.get("project_key")).strip()
            if not key:
                continue
            unique_rows[key] = row
        if not unique_rows:
            return

        keys = list(unique_rows.keys())
        existing = (
            db.query(ProjectRaw)
            .filter(ProjectRaw.project_key.in_(keys))
            .all()
        )
        existing_map = {item.project_key: item for item in existing}

        for key, row in unique_rows.items():
            entry = existing_map.get(key)
            if not entry:
                entry = ProjectRaw(project_key=key)
                db.add(entry)
                existing_map[key] = entry
            changed = False
            changed = self._set_if_changed(entry, "keyword", row["keyword"]) or changed
            changed = self._set_if_changed(entry, "title", row["title"]) or changed
            changed = self._set_if_changed(entry, "description", row["description"]) or changed
            changed = self._set_if_changed(entry, "url", row["url"]) or changed
            changed = self._set_if_changed(entry, "category", row["category"]) or changed
            changed = self._set_if_changed(entry, "price", row["price"]) or changed
            changed = self._set_if_changed(entry, "price_value", row["price_value"]) or changed
            changed = self._set_if_changed(entry, "rating", row["rating"]) or changed
            changed = self._set_if_changed(entry, "sales", row["sales"]) or changed
            changed = self._set_if_changed(entry, "source_file", source_file) or changed

            new_scraped_at = row["scraped_at"] or entry.scraped_at or datetime.utcnow()
            if entry.scraped_at is None or (new_scraped_at and new_scraped_at > entry.scraped_at):
                entry.scraped_at = new_scraped_at
                changed = True

            if changed:
                entry.scraped_at = entry.scraped_at or datetime.utcnow()

    @staticmethod
    def _set_if_changed(entry: Any, field: str, value: Any) -> bool:
        if getattr(entry, field) == value:
            return False
        setattr(entry, field, value)
        return True

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        for candidate in (
            text,
            text.replace("Z", "+00:00"),
        ):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
        return None

    def _parse_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        if not match:
            return None
        return float(match.group(0))

    def _log_event(self, db: Session, event_type: str, payload: Dict[str, Any]) -> None:
        db.add(
            PipelineEvent(
                event_type=event_type,
                payload=json.dumps(payload, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
        )
