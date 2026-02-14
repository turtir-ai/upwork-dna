from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "profile_dynamic.json"
_DEFAULT_TIMEOUT = 30.0
logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "from", "that", "this", "are", "have",
    "will", "into", "our", "their", "about", "just", "than", "need", "looking", "build",
    "using", "work", "projects", "project", "clients", "client", "experience", "expert",
    "developer", "engineer", "freelancer", "upwork", "profile", "help", "strong", "skills",
}

# ---------- JS extraction script injected into Playwright page ----------
_EXTRACT_JS = r"""
() => {
  const data = {};

  // --- Name & Headline ---
  data.name = document.title.split(' - ')[0].trim();

  const h3s = document.querySelectorAll('main h3');
  for (const h3 of h3s) {
    const t = h3.textContent.trim();
    if (t.includes('|') || t.includes('Engineer') || t.includes('Developer')
        || t.includes('Automation') || t.includes('Freelancer')) {
      data.headline = t;
      break;
    }
  }
  if (!data.headline) data.headline = data.name;

  // --- Location ---
  data.location = '';
  document.querySelectorAll('main *').forEach(el => {
    if (el.children.length === 0 && el.textContent.trim() === 'Turkey') {
      const par = el.parentElement;
      if (par) {
        const siblings = Array.from(par.children).map(c => c.textContent.trim()).filter(Boolean);
        data.location = siblings.join(' ').replace(/\s+/g, ' ');
      }
    }
  });

  // --- Hourly Rate ---
  document.querySelectorAll('main *').forEach(el => {
    const txt = el.textContent.trim();
    if (/^\$\d+(\.\d+)?\/hr$/.test(txt)) data.hourly_rate = txt;
  });

  // --- Overview / Description ---
  const mainText = document.querySelector('main')?.innerText || '';
  // Generic: find the long description block (starts after headline, ends before Work history)
  const ovMatch = mainText.match(/(?:^|\n)([A-Z][^\n]{50,}(?:\n(?!\n\n)[^\n]*){0,40})/m);
  // More targeted: find the about/overview section
  const descBlocks = [];
  document.querySelectorAll('main > div > div > div > div').forEach(el => {
    const t = el.innerText?.trim() || '';
    if (t.length > 200 && !t.includes('Work history') && !t.includes('Portfolio')
        && !t.includes('Skills') && !t.includes('Browse similar')) {
      descBlocks.push(t);
    }
  });
  if (descBlocks.length > 0) {
    // Pick the longest that looks like an overview
    data.overview = descBlocks.reduce((a, b) => a.length > b.length ? a : b).substring(0, 3000);
  } else {
    data.overview = ovMatch ? ovMatch[1].substring(0, 3000) : '';
  }

  // --- Stats ---
  data.total_jobs = null;
  data.hours_per_week = '';
  document.querySelectorAll('main *').forEach(el => {
    const txt = el.textContent.trim();
    if (txt === 'Total jobs') {
      const prev = el.previousElementSibling;
      if (prev) data.total_jobs = parseInt(prev.textContent.trim()) || 0;
    }
    if (txt === 'Hours per week') {
      const next = el.nextElementSibling;
      if (next) data.hours_per_week = next.textContent.trim();
    }
  });
  // Fallback from innerText
  if (data.total_jobs === null) {
    const m = mainText.match(/(\d+)\s*\n?\s*Total jobs/);
    data.total_jobs = m ? parseInt(m[1]) : 0;
  }

  // --- Skills (from Skills heading > ul > li) ---
  data.skills = [];
  document.querySelectorAll('h4').forEach(h4 => {
    if (h4.textContent.trim() === 'Skills') {
      let container = h4.parentElement;
      for (let i = 0; i < 5 && container; i++) {
        const ul = container.querySelector('ul');
        if (ul && ul.querySelectorAll('li').length > 3) {
          ul.querySelectorAll('li').forEach(li => {
            const walker = document.createTreeWalker(li, NodeFilter.SHOW_TEXT);
            const texts = [];
            while (walker.nextNode()) {
              const t = walker.currentNode.textContent.trim();
              if (t && !t.startsWith('Hire ')) texts.push(t);
            }
            const skill = texts[texts.length - 1] || '';
            if (skill && skill.length < 60) data.skills.push(skill);
          });
          break;
        }
        container = container.parentElement;
      }
    }
  });

  // --- Badges (buttons inside skills section) ---
  data.badges = [];
  const badgeNames = ['Clear Communicator', 'Accountable for Outcomes', 'Committed to Quality',
                      'Detail Oriented', 'Solution Oriented', 'Proactive', 'High Performer'];
  document.querySelectorAll('main button').forEach(btn => {
    const t = btn.textContent.trim();
    if (badgeNames.some(b => t.includes(b))) data.badges.push(t);
  });

  // --- Work History ---
  data.work_history = [];
  const tabPanel = document.querySelector('[role="tabpanel"]');
  if (tabPanel) {
    const items = tabPanel.querySelectorAll(':scope > div, :scope > article');
    const processItem = (el) => {
      const inner = el.innerText || '';
      const title = inner.split('\n')[0] || '';
      let rating = '';
      el.querySelectorAll('*').forEach(c => {
        if (c.textContent.includes('Rating is') && c.textContent.includes('out of 5'))
          rating = c.textContent.trim();
      });
      let dateRange = '';
      const dm = inner.match(/((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})\s*-\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})/);
      if (dm) dateRange = dm[1] + ' - ' + dm[2];
      let review = '';
      el.querySelectorAll('*').forEach(c => {
        const t = c.textContent.trim();
        if (t.startsWith('"') && t.endsWith('"') && t.length > 5) review = t;
      });
      return { title: title.substring(0, 200), rating, dateRange, review };
    };

    if (items.length > 0) {
      items.forEach(item => {
        const h = processItem(item);
        if (h.title) data.work_history.push(h);
      });
    } else {
      data.work_history.push(processItem(tabPanel));
    }
  }

  // --- Portfolio ---
  data.portfolio = [];
  document.querySelectorAll('main h3').forEach(h3 => {
    if (h3.textContent.trim() === 'Portfolio') {
      const container = h3.closest('div');
      if (container) {
        container.querySelectorAll('*').forEach(el => {
          const style = window.getComputedStyle(el);
          if (style.cursor === 'pointer' && el.tagName === 'DIV') {
            const t = el.textContent.trim();
            if (t.length > 10 && t.length < 200 && !t.includes('Sign up') && !t.includes('Want to see more'))
              data.portfolio.push(t);
          }
        });
      }
    }
  });
  // Dedup
  data.portfolio = [...new Set(data.portfolio)];

  // --- Online Status ---
  const statusImg = document.querySelector('img[alt*="Status"]');
  data.online_status = statusImg ? statusImg.alt.replace('Status: ', '') : '';

  // --- Contract to hire ---
  data.contract_to_hire = mainText.includes('Open to contract to hire');

  // --- Completed jobs tab count ---
  const tab = document.querySelector('[role="tab"][aria-selected="true"]');
  data.completed_jobs_tab = tab ? tab.textContent.trim() : '';

  return JSON.stringify(data);
}
"""


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_candidate_keywords(text: str) -> tuple[list[str], list[str]]:
    lower = text.lower()

    phrase_candidates = [
        "n8n", "python", "fastapi", "langchain", "langgraph", "rag", "ai agent",
        "agentic", "automation", "api integration", "web scraping", "data extraction",
        "etl", "vector database", "pinecone", "chromadb", "openai", "llm", "chatbot",
        "prompt engineering", "sql", "airtable", "google sheets", "zapier", "make.com",
        "workflow automation", "data pipeline", "retrieval augmented generation",
        "postgresql", "javascript", "ai agent development",
    ]

    extracted = [term for term in phrase_candidates if term in lower]

    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", lower)
    freq = Counter(tok for tok in tokens if tok not in _STOPWORDS)
    top_tokens = [tok for tok, count in freq.most_common(30) if count >= 2][:15]

    merged = list(dict.fromkeys([*extracted, *top_tokens]))
    detected_skills = [k for k in extracted if k not in {"llm", "agentic"}]
    return merged[:30], detected_skills[:20]


def build_profile_payload_from_text(profile_text: str, upwork_url: str = "", headline: str = "") -> dict[str, Any]:
    normalized = _normalize_whitespace(profile_text)
    extracted_keywords, detected_skills = _extract_candidate_keywords(normalized)

    return {
        "upwork_url": upwork_url,
        "synced_at": datetime.utcnow().isoformat(),
        "headline": _normalize_whitespace(headline),
        "overview": normalized[:2000],
        "extracted_keywords": extracted_keywords,
        "detected_skills": detected_skills,
        "source": "manual_profile_text",
    }


def _fetch_with_playwright(upwork_url: str) -> dict[str, Any]:
    """Use Playwright headless browser to bypass Cloudflare and extract DOM data."""
    from playwright.sync_api import sync_playwright  # lazy import

    with sync_playwright() as p:
        # Try system Chrome first (less detectable), fall back to bundled Chromium
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            logger.info("[ProfileSync] Using system Chrome channel")
        except Exception:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            logger.info("[ProfileSync] Using bundled Chromium")

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1440, "height": 900},
            java_script_enabled=True,
        )
        # Hide webdriver detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        page = context.new_page()

        try:
            page.goto(upwork_url, wait_until="domcontentloaded", timeout=45000)

            # Wait for Cloudflare challenge to resolve — poll for main content
            for attempt in range(30):
                title = page.title()
                if "lütfen" in title.lower() or "moment" in title.lower() \
                   or "checking" in title.lower() or "just a" in title.lower():
                    logger.info(f"[ProfileSync] Cloudflare challenge active (attempt {attempt+1}/30)")
                    page.wait_for_timeout(2000)
                else:
                    break

            # Wait for profile content to load (longer timeout for CF delays)
            page.wait_for_selector("main h3, main h4", timeout=30000)
            page.wait_for_timeout(3000)  # let dynamic content settle

            raw_json = page.evaluate(_EXTRACT_JS)
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

        finally:
            browser.close()

    return data


def fetch_and_extract_upwork_profile(upwork_url: str) -> dict[str, Any]:
    """Fetch public Upwork profile — tries Playwright (Cloudflare-safe) first."""
    logger.info(f"[ProfileSync] Fetching {upwork_url} via Playwright")

    raw = _fetch_with_playwright(upwork_url)

    name = raw.get("name", "")
    headline = raw.get("headline", "")
    overview = raw.get("overview", "")
    skills = raw.get("skills", [])
    badges = raw.get("badges", [])
    hourly_rate = raw.get("hourly_rate", "")
    total_jobs = raw.get("total_jobs", 0)
    hours_per_week = raw.get("hours_per_week", "")
    location = raw.get("location", "")
    work_history = raw.get("work_history", [])
    portfolio = raw.get("portfolio", [])
    online_status = raw.get("online_status", "")
    contract_to_hire = raw.get("contract_to_hire", False)

    # Build keyword list from skills + overview text
    text_blob = " ".join([headline, overview, " ".join(skills), " ".join(badges)])
    extracted_keywords, detected_skills = _extract_candidate_keywords(text_blob)

    # Merge scraped skills into detected_skills
    merged_skills = list(dict.fromkeys([s.lower() for s in skills] + detected_skills))

    payload = {
        "upwork_url": upwork_url,
        "synced_at": datetime.utcnow().isoformat(),
        "name": name,
        "headline": headline,
        "overview": overview[:2000],
        "hourly_rate": hourly_rate,
        "total_jobs": total_jobs,
        "hours_per_week": hours_per_week,
        "location": location,
        "skills": skills,
        "badges": badges,
        "work_history": work_history,
        "portfolio": portfolio,
        "online_status": online_status,
        "contract_to_hire": contract_to_hire,
        "extracted_keywords": extracted_keywords,
        "detected_skills": merged_skills,
        "source": "playwright_public_profile",
    }

    logger.info(
        f"[ProfileSync] Extracted: {len(skills)} skills, "
        f"{len(work_history)} jobs, {total_jobs} total, rate={hourly_rate}"
    )
    return payload


def save_dynamic_profile(payload: dict[str, Any]) -> Path:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _DATA_PATH


def load_cached_profile() -> dict[str, Any] | None:
    """Load previously saved profile from disk (for fallback when scraping fails)."""
    if _DATA_PATH.exists():
        try:
            data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("synced_at"):
                return data
        except Exception:
            pass
    return None


def save_rich_profile_from_extension(rich: dict[str, Any], upwork_url: str = "") -> dict[str, Any]:
    """Save rich profile data sent by the Chrome extension — no scraping needed."""
    skills = rich.get("skills", [])
    overview = rich.get("overview", "")
    headline = rich.get("headline", "")
    badges = rich.get("badges", [])

    # Build keyword list from skills + overview text
    text_blob = " ".join([headline, overview, " ".join(skills), " ".join(badges)])
    extracted_keywords, detected_skills = _extract_candidate_keywords(text_blob)

    # Merge scraped skills into detected_skills
    merged_skills = list(dict.fromkeys([s.lower() for s in skills] + detected_skills))

    payload = {
        "upwork_url": upwork_url or rich.get("upwork_url", ""),
        "synced_at": datetime.utcnow().isoformat(),
        "name": rich.get("name", ""),
        "headline": headline,
        "overview": overview[:2000],
        "hourly_rate": rich.get("hourly_rate", ""),
        "total_jobs": rich.get("total_jobs", 0),
        "hours_per_week": rich.get("hours_per_week", ""),
        "location": rich.get("location", ""),
        "skills": skills,
        "badges": badges,
        "work_history": rich.get("work_history", []),
        "portfolio": rich.get("portfolio", []),
        "online_status": rich.get("online_status", ""),
        "contract_to_hire": rich.get("contract_to_hire", False),
        "extracted_keywords": extracted_keywords,
        "detected_skills": merged_skills,
        "source": "extension_rich_profile",
    }

    save_dynamic_profile(payload)
    logger.info(
        f"[ProfileSync] Extension rich profile saved: {len(skills)} skills, "
        f"{len(rich.get('work_history', []))} jobs, rate={rich.get('hourly_rate', '')}"
    )
    return payload


def sync_profile_from_upwork(upwork_url: str) -> dict[str, Any]:
    payload = fetch_and_extract_upwork_profile(upwork_url)
    save_dynamic_profile(payload)
    return payload
