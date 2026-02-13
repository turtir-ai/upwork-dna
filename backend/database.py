"""
Database configuration and models for Upwork DNA
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./upwork_dna.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")
SQLITE_BUSY_TIMEOUT_MS = max(1000, int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000")))

engine_kwargs = {}
if IS_SQLITE:
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000.0,
    }
    # Avoid queue-pool starvation under bursty local requests.
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    **engine_kwargs,
)


if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class QueueItem(Base):
    """Queue items for scraping jobs"""
    __tablename__ = "queue"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    job_type = Column(String, default="jobs")  # jobs, talent, projects, all
    priority = Column(Integer, default=0)


class Job(Base):
    """Scraped job postings"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    url = Column(String, unique=True)
    budget = Column(String)
    posted_date = Column(String)
    client_info = Column(Text)
    skills = Column(Text)  # JSON array as string
    scraped_at = Column(DateTime, default=datetime.utcnow)


class Talent(Base):
    """Scraped talent/freelancer profiles"""
    __tablename__ = "talent"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    name = Column(String)
    title = Column(String)
    description = Column(Text)
    url = Column(String, unique=True)
    hourly_rate = Column(String)
    skills = Column(Text)  # JSON array as string
    country = Column(String)
    rating = Column(Float)
    jobs_completed = Column(Integer)
    scraped_at = Column(DateTime, default=datetime.utcnow)


class Project(Base):
    """Scraped project catalog entries"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    url = Column(String, unique=True)
    category = Column(String)
    price = Column(String)
    rating = Column(Float)
    sales = Column(Integer)
    scraped_at = Column(DateTime, default=datetime.utcnow)


class ScrapingJob(Base):
    """Track scraping job status"""
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    keyword = Column(String)
    status = Column(String, default="pending")  # pending, running, completed, failed
    job_type = Column(String)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestedFile(Base):
    """Track files ingested from Downloads/upwork_dna."""
    __tablename__ = "ingested_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_hash = Column(String, nullable=False, index=True)
    file_type = Column(String, nullable=False)  # csv, json
    dataset = Column(String, nullable=False)  # jobs, talent, projects, mixed
    keyword = Column(String, index=True)
    row_count = Column(Integer, default=0)
    last_modified_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class JobRaw(Base):
    """Normalized jobs ingested from extension exports."""
    __tablename__ = "jobs_raw"

    id = Column(Integer, primary_key=True, index=True)
    job_key = Column(String, unique=True, nullable=False, index=True)
    keyword = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    url = Column(String, index=True)
    budget = Column(String)
    budget_value = Column(Float)
    client_spend = Column(Float)
    payment_verified = Column(Boolean, default=False)
    proposals = Column(String)
    skills = Column(Text)
    source_file = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)


class TalentRaw(Base):
    """Normalized talent profiles ingested from extension exports."""
    __tablename__ = "talent_raw"

    id = Column(Integer, primary_key=True, index=True)
    talent_key = Column(String, unique=True, nullable=False, index=True)
    keyword = Column(String, index=True)
    name = Column(String)
    title = Column(String)
    description = Column(Text)
    url = Column(String, index=True)
    hourly_rate = Column(String)
    hourly_rate_value = Column(Float)
    skills = Column(Text)
    country = Column(String)
    rating = Column(Float)
    jobs_completed = Column(Integer)
    source_file = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)


class ProjectRaw(Base):
    """Normalized project catalog entries ingested from extension exports."""
    __tablename__ = "projects_raw"

    id = Column(Integer, primary_key=True, index=True)
    project_key = Column(String, unique=True, nullable=False, index=True)
    keyword = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    url = Column(String, index=True)
    category = Column(String)
    price = Column(String)
    price_value = Column(Float)
    rating = Column(Float)
    sales = Column(Integer)
    source_file = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)


class KeywordMetric(Base):
    """Aggregated metrics per keyword."""
    __tablename__ = "keyword_metrics"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    demand = Column(Integer, default=0)
    supply = Column(Integer, default=0)
    gap_ratio = Column(Float, default=0.0)
    budget_avg = Column(Float, default=0.0)
    competition_inverse = Column(Float, default=0.0)
    trend_score = Column(Float, default=0.0)
    opportunity_score = Column(Float, default=0.0)
    recommended_priority = Column(String, default="LOW")
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)


class KeywordRecommendation(Base):
    """Recommendation feed consumed by extension/electron/dashboard."""
    __tablename__ = "keyword_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, nullable=False, index=True)
    recommended_priority = Column(String, nullable=False, default="LOW")
    opportunity_score = Column(Float, nullable=False, default=0.0)
    demand = Column(Integer, default=0)
    supply = Column(Integer, default=0)
    gap_ratio = Column(Float, default=0.0)
    reason_codes = Column(Text, default="[]")  # JSON array string
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)


class JobOpportunity(Base):
    """Job-level opportunity and safety scoring output."""
    __tablename__ = "job_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    job_key = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    keyword = Column(String, index=True)
    opportunity_score = Column(Float, default=0.0)
    safety_score = Column(Float, default=0.0)
    fit_score = Column(Float, default=0.0)
    apply_now = Column(Boolean, default=False)
    reasons = Column(Text, default="[]")  # JSON array string
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)


class ProposalDraft(Base):
    """Rule-based proposal drafts per opportunity."""
    __tablename__ = "proposal_drafts"

    id = Column(Integer, primary_key=True, index=True)
    job_key = Column(String, unique=True, nullable=False, index=True)
    cover_letter_draft = Column(Text, nullable=False)
    hook_points = Column(Text, default="[]")  # JSON array string
    caution_notes = Column(Text, default="[]")  # JSON array string
    updated_at = Column(DateTime, default=datetime.utcnow, index=True)


class PipelineEvent(Base):
    """Operational and telemetry events."""
    __tablename__ = "pipeline_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class QueueTelemetry(Base):
    """Latest queue telemetry snapshot pushed by extension."""
    __tablename__ = "queue_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    total = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    running = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    error = Column(Integer, default=0)
    last_cycle_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
