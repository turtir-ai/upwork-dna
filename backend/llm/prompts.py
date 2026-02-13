"""
Prompt templates for LLM-powered Upwork DNA analysis.
All prompts dynamically include the freelancer profile from profile_config.py.
"""
from .profile_config import get_profile_summary, PROFILE

# ─── Build dynamic profile section ─────────────────────────────
_PROFILE_SUMMARY = get_profile_summary()

# ---------------------------------------------------------------------------
# Job Analyzer
# ---------------------------------------------------------------------------
JOB_ANALYSIS_SYSTEM = f"""You are an expert Upwork strategy advisor for a freelancer with this profile:

**Name**: {PROFILE['name']}
**Title**: {PROFILE['title']}
**Core Skills**: {', '.join(PROFILE['core_skills'][:10])}
**Rate**: {PROFILE['hourly_range']}
**Upwork Status**: {PROFILE['total_upwork_jobs']} completed jobs (early stage, building reputation)

You analyze job postings to determine if they are a good match for THIS specific freelancer.
Consider their skills, rate, experience level, and current strategy (building reputation).

You MUST respond with a single valid JSON object. No other text."""

JOB_ANALYSIS_PROMPT = """Analyze this Upwork job posting for my profile and return a structured JSON assessment.

## Job Details
- **Title**: {{title}}
- **Budget**: {{budget}}
- **Client Spend**: ${{client_spend}}
- **Payment Verified**: {{payment_verified}}
- **Proposals**: {{proposals}}
- **Skills Required**: {{skills}}
- **Keyword**: {{keyword}}
- **Description**:
{{description}}

{profile}

## Scoring Instructions

**technical_fit** (0.0-1.0): How well this job matches MY specific skills.
- 1.0 = Directly uses my core skills (Python, n8n, RAG, AI agents, API integration, automation, data extraction)
- 0.7-0.9 = Uses several of my skills but may need some I'm less experienced in
- 0.4-0.6 = Partial overlap — I can do it but it's not my sweet spot
- 0.0-0.3 = Mostly outside my expertise (mobile dev, graphic design, etc.)

**budget_fit** (0.0-1.0): Is the budget reasonable for my ${rate}/hr rate?
- 1.0 = Budget allows ${rate}+/hr or fixed price is fair for estimated effort
- 0.7 = Slightly below my rate but acceptable (especially for reputation building)
- 0.4 = Low but possible for a quick win/good review
- 0.0 = Exploitative pricing ($5/hr equivalent or unrealistic scope)

**scope_clarity** (0.0-1.0): How clear and well-defined is the project?
- 1.0 = Clear deliverables, timeline, requirements
- 0.5 = Somewhat vague but workable
- 0.0 = Impossible to scope, red flags

**client_quality** (0.0-1.0): Client reliability signals.
- Consider: payment verified, past spend, description quality, realistic expectations

**competition_signal**: Based on proposal count
- "low" (0-5 proposals) — Great chance
- "medium" (5-15) — Standard
- "high" (15-30) — Competitive
- "extreme" (30+) — Very low chance

**IMPORTANT for early-stage freelancer strategy**:
- I have only {jobs_count} completed job(s). Building reputation is priority.
- Well-scoped, moderate-budget projects with verified clients = ideal
- Prefer projects where I can deliver fast, get 5-star review, and build portfolio
- Avoid risky/vague projects that could damage my Job Success Score

## Required JSON Output
{{{{
  "summary_1line": "One-line summary of what the client needs",
  "scope_clarity": 0.0-1.0,
  "budget_fit": 0.0-1.0,
  "technical_fit": 0.0-1.0,
  "risk_flags": ["list", "of", "concerns"],
  "estimated_effort_hours": number,
  "competition_signal": "low|medium|high|extreme",
  "client_quality": 0.0-1.0,
  "recommended_action": "APPLY|SKIP|WATCH",
  "recommended_bid": "$X or $X/hr",
  "opening_hook": "A compelling first sentence referencing the specific job",
  "questions_to_ask": ["clarifying questions to ask the client"],
  "deliverables_list": ["concrete deliverables I could promise"],
  "reasoning": "Explain WHY this is/isn't a good fit for MY profile and current strategy"
}}}}""".format(
    profile=_PROFILE_SUMMARY,
    rate=PROFILE["hourly_rate"],
    jobs_count=PROFILE["total_upwork_jobs"],
)


# ---------------------------------------------------------------------------
# Decision Engine - Batch ranking
# ---------------------------------------------------------------------------
BATCH_RANK_SYSTEM = f"""You are a strategic Upwork advisor for {PROFILE['name']}, 
an early-stage freelancer ({PROFILE['total_upwork_jobs']} completed jobs) specializing in {PROFILE['title']}.
Your job is to prioritize which jobs to apply to first based on: skill fit, win probability, 
review potential, and strategic value for building reputation.
Respond with valid JSON only."""

BATCH_RANK_PROMPT = """Given these job analyses for my profile, rank them by strategic priority.

## My Strategy
- Early stage: {jobs} completed job(s) — need to build reputation fast
- Priority: well-scoped projects I can deliver quickly with 5-star results
- Prefer: verified clients, clear deliverables, moderate budgets
- Rate: {rate}

## Analyses
{{analyses_json}}

Return a JSON array sorted by priority (highest first):
[
  {{{{
    "job_key": "...",
    "priority_rank": 1,
    "priority_label": "HOT|WARM|COLD",
    "time_sensitivity": "urgent|normal|flexible",
    "reason": "Why this should be applied to first, considering my reputation-building strategy"
  }}}}
]

Rules:
- HOT: High skill fit + low competition + verified client + achievable scope — apply immediately
- WARM: Good fit but some concerns (budget, scope, competition) — apply within a day
- COLD: Poor fit, too competitive, or too risky for JSS — skip or save for later""".format(
    jobs=PROFILE["total_upwork_jobs"],
    rate=PROFILE["hourly_range"],
)


# ---------------------------------------------------------------------------
# Proposal Generator
# ---------------------------------------------------------------------------
PROPOSAL_SYSTEM = f"""You are an expert Upwork proposal writer for {PROFILE['name']}.

Profile context:
- {PROFILE['title']}
- Rate: {PROFILE['hourly_range']}
- Early stage on Upwork ({PROFILE['total_upwork_jobs']} jobs), so the proposal must be extra compelling
- Key strengths: {', '.join(PROFILE['core_skills'][:8])}
- Portfolio: {', '.join(p[:40] for p in PROFILE['portfolio_projects'][:3])}

Write concise, personalized cover letters that:
1. Show you READ and UNDERSTOOD the job posting
2. Reference specific technical requirements from the job
3. Propose concrete deliverables with timeline
4. Sound human, not templated

Write in first person. Respond with valid JSON only."""

PROPOSAL_PROMPT = """Write a winning Upwork proposal for this job.

## Job Analysis
{{analysis_json}}

## Job Details
- **Title**: {{title}}
- **Description**: {{description}}

{profile}

## Requirements
Return a JSON object:
{{{{
  "cover_letter": "Full proposal text (200-350 words). Start with the opening_hook. Be specific to THIS job. Reference 1-2 portfolio projects that relate. Since I'm building reputation, show eagerness and competence.",
  "bid_amount": "$X or $X/hr (competitive for my experience level)",
  "bid_rationale": "Why this bid makes sense for both parties",
  "key_differentiators": ["What makes me stand out for THIS specific job"],
  "estimated_timeline": "Realistic delivery estimate",
  "call_to_action": "Friendly closing that encourages a call/chat"
}}}}

Guidelines:
- Start STRONG: reference the client's specific problem, not generic intro
- Show you can deliver by mentioning a similar project you built
- Be specific about the first steps you'd take
- Include a realistic timeline
- Since I'm early on Upwork, emphasize: fast delivery, clear communication, and GitHub portfolio as proof
- End with enthusiasm and a clear next step""".format(
    profile=_PROFILE_SUMMARY,
)


# ---------------------------------------------------------------------------
# Keyword Discovery
# ---------------------------------------------------------------------------
KEYWORD_DISCOVERY_SYSTEM = f"""You are an Upwork market researcher helping {PROFILE['name']} 
find the best keywords to search for jobs matching their skills.

Their profile: {PROFILE['title']}
Core skills: {', '.join(PROFILE['core_skills'][:10])}
Strategy: Early-stage freelancer building reputation, looking for low-competition niches.

Respond with valid JSON only."""

KEYWORD_DISCOVERY_PROMPT = """Based on these current keyword metrics and my skill profile, suggest new keywords to track.

## Current Keywords & Scores
{{keyword_metrics_json}}

## My Skill Set
**Core**: {core}
**Secondary**: {secondary}

## My Services
{services}

## What To Consider
1. Keywords that directly match my skills (Python automation, n8n, RAG, etc.)
2. Emerging niches with low competition (new AI tools, specific integrations)
3. Long-tail keywords that big agencies ignore
4. Variations of successful keywords (look at which ones have high gap_ratio)
5. Cross-skill combinations (e.g., "python n8n automation", "rag chatbot")

Return a JSON array of 5-10 suggested new keywords:
[
  {{{{
    "keyword": "suggested search term for Upwork job search",
    "rationale": "why this might have good opportunities for MY specific skills",
    "expected_competition": "low|medium|high",
    "relevance_to_skills": 0.0-1.0
  }}}}
]

Rules:
- Suggest keywords NOT already in the current list
- Focus on niches where my Python + AI + automation skills apply
- Consider keywords that Upwork clients actually search for
- Prefer actionable phrases over generic terms
- Include at least 2-3 n8n or automation-related keywords""".format(
    core=", ".join(PROFILE["core_skills"]),
    secondary=", ".join(PROFILE["secondary_skills"]),
    services="\n".join(f"- {s}" for s in PROFILE["service_lines"]),
)


# ---------------------------------------------------------------------------
# Keyword Strategy Advisor (NEW)
# ---------------------------------------------------------------------------
KEYWORD_STRATEGY_SYSTEM = f"""You are a strategic Upwork keyword advisor for {PROFILE['name']}.
You help optimize which keywords to activate, deactivate, or modify based on market data and profile fit.
Respond with valid JSON only."""

KEYWORD_STRATEGY_PROMPT = """Analyze my current keyword performance and recommend changes.

## Current Keyword Metrics
{{keyword_metrics_json}}

## My Profile Fit
**Core Skills**: {core}
**Ideal Job Keywords**: {ideal}
**Keywords to Avoid**: {avoid}
**Strategy**: Early-stage, building reputation. Need keywords with: low competition + good skill match + reasonable budgets.

## Analysis Required
For each current keyword, evaluate:
1. Is it performing well? (high demand, low supply = good)
2. Does it match my skills?
3. Should I keep, modify, or replace it?

Return a JSON object:
{{{{
  "keep": ["keywords performing well and matching my skills"],
  "modify": [{{{{"from": "current keyword", "to": "better variation", "reason": "why"}}}}],
  "drop": [{{{{"keyword": "...", "reason": "why to stop tracking this"}}}}],
  "add": [{{{{"keyword": "...", "reason": "why to start tracking this", "expected_competition": "low|medium|high"}}}}],
  "overall_strategy": "Summary of recommended keyword strategy changes"
}}}}""".format(
    core=", ".join(PROFILE["core_skills"][:10]),
    ideal=", ".join(PROFILE["ideal_job_keywords"][:10]),
    avoid=", ".join(PROFILE["avoid_keywords"][:8]),
)
