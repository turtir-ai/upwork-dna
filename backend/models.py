"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Queue Models
class QueueItemCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    job_type: str = Field(default="jobs", pattern="^(jobs|talent|projects|all)$")
    priority: int = Field(default=0, ge=0, le=10)


class QueueItemResponse(BaseModel):
    id: int
    keyword: str
    status: str
    job_type: str
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    items: List[QueueItemResponse]
    total: int


# Scraping Models
class ScrapingRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    job_type: str = Field(default="jobs", pattern="^(jobs|talent|projects|all)$")
    max_pages: int = Field(default=5, ge=1, le=20)


class ScrapingStatusResponse(BaseModel):
    job_id: str
    keyword: str
    status: str
    job_type: str
    total_items: int
    processed_items: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Result Models
class JobResponse(BaseModel):
    id: int
    keyword: str
    title: str
    description: Optional[str] = None
    url: str
    budget: Optional[str] = None
    posted_date: Optional[str] = None
    client_info: Optional[str] = None
    skills: Optional[str] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class TalentResponse(BaseModel):
    id: int
    keyword: str
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    url: str
    hourly_rate: Optional[str] = None
    skills: Optional[str] = None
    country: Optional[str] = None
    rating: Optional[float] = None
    jobs_completed: Optional[int] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    keyword: str
    title: str
    description: Optional[str] = None
    url: str
    category: Optional[str] = None
    price: Optional[str] = None
    rating: Optional[float] = None
    sales: Optional[int] = None
    scraped_at: datetime

    class Config:
        from_attributes = True


class ResultsResponse(BaseModel):
    jobs: List[JobResponse]
    talent: List[TalentResponse]
    projects: List[ProjectResponse]
    totals: dict


# System Status
class SystemStatusResponse(BaseModel):
    status: str
    version: str
    database_connected: bool
    playwright_installed: bool
    queue_size: int
    active_jobs: int
    completed_jobs: int
    uptime: str


# Error Response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Orchestrator v1 models
class KeywordRecommendationResponse(BaseModel):
    keyword: str
    recommended_priority: str
    opportunity_score: float
    demand: int
    supply: int
    gap_ratio: float
    reason_codes: List[str]


class JobOpportunityResponse(BaseModel):
    job_key: str
    title: str
    keyword: str
    opportunity_score: float
    safety_score: float
    fit_score: float
    apply_now: bool
    reasons: List[str]


class JobEnrichedResponse(BaseModel):
    """Enriched job: opportunities + raw data merged for dashboard."""
    job_key: str
    title: str
    keyword: str
    opportunity_score: float
    safety_score: float
    fit_score: float
    apply_now: bool
    reasons: str  # raw JSON string for flexibility
    # From jobs_raw
    description: str = ""
    url: str = ""
    budget: str = ""
    budget_value: Optional[float] = None
    client_spend: Optional[str] = None
    payment_verified: Optional[bool] = None
    proposals: str = ""
    skills: str = ""
    scraped_at: Optional[str] = None
    freshness: float = 100.0  # 0-100, higher = fresher


class ProposalDraftResponse(BaseModel):
    job_key: str
    cover_letter_draft: str
    hook_points: List[str]
    caution_notes: List[str]


class QueueTelemetryResponse(BaseModel):
    total: int
    pending: int
    running: int
    completed: int
    error: int
    last_cycle_at: Optional[str] = None


class QueueTelemetryUpdateRequest(BaseModel):
    total: int = Field(default=0, ge=0)
    pending: int = Field(default=0, ge=0)
    running: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    error: int = Field(default=0, ge=0)
    last_cycle_at: Optional[str] = None


class IngestScanResponse(BaseModel):
    scanned_files: int
    new_files: int
    updated_files: int
    updated_metrics_at: str


class OrchestratorSummaryResponse(BaseModel):
    jobs_raw: int
    talent_raw: int
    projects_raw: int
    keywords: int
    opportunities: int
    last_ingest_at: Optional[str] = None


class RunIngestRequest(BaseModel):
    run_id: str
    run: dict


class RunIngestResponse(BaseModel):
    run_id: str
    keyword: str
    jobs_ingested: int
    talent_ingested: int
    projects_ingested: int
    updated_metrics_at: str
