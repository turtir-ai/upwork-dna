"""
Freelancer Profile Configuration
=================================
Central profile definition used by all LLM prompts for personalized analysis.
Edit this file to tune how the AI evaluates jobs for YOUR specific skills and goals.

This profile is injected into:
- Job analysis (technical_fit, budget_fit scoring)
- Proposal generation (personalized cover letters)
- Keyword discovery (skill-relevant suggestions)
- Decision engine (priority ranking)
"""

PROFILE = {
    # ─── Identity ───────────────────────────────────────────────
    "name": "Your Name",
    "title": "AI Automation Engineer | RAG, AI Agents & n8n Workflows | Python",
    "location": "Remote",
    "timezone": "UTC+3",
    "languages": ["English (Conversational)", "Turkish (Native)"],
    "availability": "30+ hrs/week",
    "upwork_url": "https://www.upwork.com/freelancers/~your-profile-id",

    # ─── Pricing ────────────────────────────────────────────────
    "hourly_rate": 35.0,
    "hourly_range": "$25-50/hr",
    "min_project_budget": 100,       # Skip projects below this ($)
    "preferred_budget_min": 300,     # Sweet spot starts here
    "preferred_project_types": ["hourly", "fixed"],

    # ─── Core Skills (Strong) ──────────────────────────────────
    "core_skills": [
        "Python",
        "n8n",
        "FastAPI",
        "SQL",
        "LangChain",
        "RAG (Retrieval Augmented Generation)",
        "AI Agents",
        "API Integration",
        "Automation",
        "Data Extraction",
        "Web Scraping",
        "ETL",
        "Vector Databases (Pinecone, ChromaDB)",
        "Prompt Engineering",
        "Chatbot Development",
    ],

    # ─── Secondary Skills ──────────────────────────────────────
    "secondary_skills": [
        "OpenAI API",
        "Automated Workflows",
        "Data Pipelines",
        "Excel/Google Sheets Automation",
        "BI Dashboards",
        "Reporting Systems",
        "WordPress REST API",
        "Process Automation",
        "Data Cleaning",
        "PDF/Email Data Extraction",
    ],

    # ─── What I Do (service lines for matching) ────────────────
    "service_lines": [
        "AI agents that execute workflows end-to-end",
        "RAG systems (chat with documents/DB) for internal knowledge retrieval",
        "LLM-based data extraction (PDF/emails/web → validated JSON/SQL/Excel)",
        "n8n + Python automations connecting tools (Slack/HubSpot/Shopify/Sheets)",
        "Data pipelines and reporting systems replacing manual workflows",
        "Process automation saving time and reducing errors",
    ],

    # ─── Experience & Proof Points ─────────────────────────────
    "years_experience": 7,
    "total_upwork_jobs": 1,  # Early stage on Upwork
    "employment_history": [
        "Business Analyst (Data & Automation) — 2019-Present",
        "Freelance Data & Automation Consultant — 2016-Present",
    ],
    "portfolio_projects": [
        "Upwork DNA — Python-based market intelligence engine (scraping + scoring + LLM analysis)",
        "AutoPublisher RAG Console — n8n→WordPress + Citation-First RAG",
        "DriftGuard — Offline Data Reliability Gate (Contract + Drift detection)",
        "LeadIntel Pro — Multi-Source Lead Intelligence Pipeline (Python)",
    ],
    "certifications": [
        "Google Data Analytics — Process Data from Dirty to Clean (Coursera, 2026)",
        "Google Data Analytics — Prepare Data for Exploration (Coursera, 2026)",
    ],
    "education": [
        "Computer Engineering",
        "Economics",
    ],
    "github": "https://github.com/your-username",

    # ─── Job Fit Preferences (for LLM scoring) ────────────────
    "ideal_job_keywords": [
        "python", "n8n", "automation", "api integration", "data extraction",
        "web scraping", "langchain", "rag", "ai agent", "chatbot",
        "fastapi", "etl", "data pipeline", "workflow automation",
        "prompt engineering", "vector database", "sql", "reporting",
        "process automation", "openai",
    ],

    "avoid_keywords": [
        "wordpress theme", "graphic design", "video editing",
        "social media management", "seo writing", "content writing",
        "mobile app (React Native/Flutter)", "unity", "game development",
        "accounting", "bookkeeping",
    ],

    # ─── Competitive Positioning ───────────────────────────────
    "differentiators": [
        "Builder mindset: I ship systems, not just scripts",
        "Proof-of-work portfolio with real automation projects on GitHub",
        "End-to-end delivery: from data source to validated output",
        "Background in both engineering (CS) and business (Economics)",
        "n8n + Python combo for no-code/low-code + custom code hybrid solutions",
    ],

    # ─── Strategy Notes ────────────────────────────────────────
    "strategy": {
        "phase": "growth",  # early | growth | established
        "priority": "build_reputation",  # build_reputation | maximize_income | specialize
        "willing_to_discount": True,  # Accept slightly lower rates for good reviews
        "target_jss": 90,  # Target Job Success Score
        "notes": (
            "Early stage on Upwork (1 job). Priority: get 5+ completed jobs "
            "with 5-star reviews. Accept well-scoped projects even if slightly "
            "below ideal rate. Avoid risky/unclear clients that could damage JSS."
        ),
    },
}


# ─── Helper: Format profile for prompts ───────────────────────

def get_profile_summary() -> str:
    """Compact profile text for injection into LLM prompts."""
    p = PROFILE
    skills_str = ", ".join(p["core_skills"][:12])
    secondary_str = ", ".join(p["secondary_skills"][:8])
    portfolio_str = "\n".join(f"  - {proj}" for proj in p["portfolio_projects"])
    services_str = "\n".join(f"  - {s}" for s in p["service_lines"])
    diffs_str = "\n".join(f"  - {d}" for d in p["differentiators"])

    return f"""## My Profile — {p['name']}
**Title**: {p['title']}
**Rate**: {p['hourly_range']} (base: ${p['hourly_rate']}/hr)
**Availability**: {p['availability']} | {p['location']} ({p['timezone']})
**Upwork Status**: {p['total_upwork_jobs']} completed jobs (building reputation — early stage)
**Languages**: {', '.join(p['languages'])}

**Core Skills**: {skills_str}
**Also proficient in**: {secondary_str}

**What I Deliver**:
{services_str}

**Portfolio (proof-of-work)**:
{portfolio_str}

**Competitive Edge**:
{diffs_str}

**Strategy Note**: {p['strategy']['notes']}"""


def get_skills_for_matching() -> list[str]:
    """All skills flattened for keyword matching."""
    return PROFILE["core_skills"] + PROFILE["secondary_skills"]


def get_ideal_keywords() -> list[str]:
    """Keywords that signal a good job match."""
    return PROFILE["ideal_job_keywords"]


def get_avoid_keywords() -> list[str]:
    """Keywords that signal poor fit."""
    return PROFILE["avoid_keywords"]
