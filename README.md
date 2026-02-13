# Upwork DNA — Autonomous Upwork Intelligence Stack

I built this project to solve a real freelance problem: **finding high-fit Upwork opportunities fast, with less noise and better decisions**.

Upwork DNA is a full-stack system that combines:
- a Chrome Extension for data collection,
- a FastAPI backend + SQLite pipeline,
- an LLM decision engine for APPLY/WATCH/SKIP,
- a Streamlit operations dashboard,
- and optional Electron + Next.js frontends.

It is designed as an end-to-end flywheel: **collect → score → analyze → prioritize → improve keywords → collect again**.

---

## What This Repository Includes

### 1) Chrome Extension Layer
- `original_repo/` and `original_repo_v2/`: stable and enhanced extension versions
- `extension_analysis/`: advanced extension variant and queue/storage utilities
- Handles keyword queueing, job-page capture, and export logic

### 2) Backend Orchestration Layer (FastAPI)
- `backend/`: API, orchestration, persistence, LLM routes, scoring
- Queue and ingestion workflows
- Opportunity scoring with profile-aware rules + freshness controls
- LLM analysis and proposal drafting endpoints

### 3) LLM Engine
- `backend/llm/`: analyzers, prompts, proposal writing, router, profile config
- Produces structured outputs like:
  - `recommended_action`: APPLY / WATCH / SKIP
  - `composite_score`
  - risk flags, reasoning, and opening hook

### 4) Analytics + Monitoring Layer
- `analist/`: data analysis pipeline and generators
- `analist/dashboard/app.py`: Streamlit dashboard for decisions, trends, and monitoring

### 5) Desktop + Web UI Options
- `electron-app/`: desktop wrapper and launcher scripts
- `web-app/`: modern Next.js interface for queue/results/settings workflows

---

## System Architecture

```text
[Chrome Extension]
   -> collects/searches/schedules
   -> exports raw opportunities

[FastAPI Backend + Orchestrator]
   -> ingests and normalizes data
   -> computes fit/freshness/opportunity signals
   -> stores in SQLite

[LLM Engine]
   -> analyzes top candidates
   -> outputs APPLY/WATCH/SKIP + reasoning
   -> supports proposal draft generation

[Streamlit Dashboard / Web App / Electron]
   -> visualize pipeline state
   -> inspect recommendations
   -> operate the system
```

---

## Core Capabilities

- **Profile-aware ranking**: matches jobs against a skill-weight profile
- **Freshness-aware filtering**: penalizes stale/high-competition opportunities
- **LLM decisioning**: converts raw listings into actionable recommendations
- **Proposal assistance**: draft support for selected opportunities
- **Continuous processing**: orchestrator and watchdog-friendly design
- **Multi-interface usage**: API + Streamlit + Electron + Next.js

---

## Quick Start (Recommended)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Chromium/Chrome
- macOS/Linux shell

### 1) Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2) Streamlit Dashboard
```bash
cd analist/dashboard
streamlit run app.py --server.port 8501
```

### 3) Web App (Optional)
```bash
cd web-app
npm install
npm run dev
```

### 4) Electron App (Optional)
```bash
cd electron-app
npm install
npm run dev
```

### 5) Chrome Extension
- Open `chrome://extensions`
- Enable Developer Mode
- Load unpacked from one of:
  - `original_repo_v2/`
  - `extension_analysis/`

---

## Key API Endpoints

- `GET /health` — backend health
- `GET /v1/opportunities/enriched` — enriched opportunities with fit/freshness context
- `POST /v1/llm/batch-analyze` — batch LLM analysis
- `POST /v1/llm/decide` — decision pass for prioritization

See backend docs at:
- `http://localhost:8000/docs`

---

## Data & Security Notes

This public repository is prepared to avoid sensitive leakage:
- local DB files are ignored
- runtime logs are ignored
- environment files are ignored (`.env`, `.env.*`)
- generated datasets/exports are ignored
- profile config uses sanitized placeholders

Before running in your environment:
1. Create your own `.env`
2. Put your own keys/tokens locally
3. Keep secrets out of commits

---

## Who This Is For

- Freelancers building a data-driven Upwork pipeline
- AI automation engineers shipping agentic workflows
- Teams experimenting with scraping + scoring + LLM decision stacks
- Builders who want both API-first and dashboard-first workflows

---

## Personal Note

I built Upwork DNA as a practical system, not just a demo. The goal is simple:
**spend less time filtering noise, spend more time applying to the right work.**

If this helps your freelance workflow, feel free to fork, adapt, and improve it.

---

## License

MIT (recommended for open collaboration). If you need a different license model, update this section accordingly.
