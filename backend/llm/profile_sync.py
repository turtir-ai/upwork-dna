from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup


_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "profile_dynamic.json"
_DEFAULT_TIMEOUT = 20.0

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "from", "that", "this", "are", "have",
    "will", "into", "our", "their", "about", "just", "than", "need", "looking", "build",
    "using", "work", "projects", "project", "clients", "client", "experience", "expert",
    "developer", "engineer", "freelancer", "upwork", "profile", "help", "strong", "skills",
}


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_json_ld_text(soup: BeautifulSoup) -> str:
    chunks: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.get_text(strip=True)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("description", "name", "headline"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    chunks.append(value)
    return _normalize_whitespace(" ".join(chunks))


def _extract_candidate_keywords(text: str) -> tuple[list[str], list[str]]:
    lower = text.lower()

    phrase_candidates = [
        "n8n", "python", "fastapi", "langchain", "langgraph", "rag", "ai agent",
        "agentic", "automation", "api integration", "web scraping", "data extraction",
        "etl", "vector database", "pinecone", "chromadb", "openai", "llm", "chatbot",
        "prompt engineering", "sql", "airtable", "google sheets", "zapier", "make.com",
        "workflow automation", "data pipeline", "retrieval augmented generation",
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
        "overview": normalized[:1000],
        "extracted_keywords": extracted_keywords,
        "detected_skills": detected_skills,
        "source": "manual_profile_text",
    }


def fetch_and_extract_upwork_profile(upwork_url: str) -> dict[str, Any]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    with httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True, headers=headers) as client:
        response = client.get(upwork_url)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "lxml")

    page_title = _normalize_whitespace(soup.title.get_text(" ", strip=True) if soup.title else "")
    meta_desc = _normalize_whitespace((soup.find("meta", attrs={"name": "description"}) or {}).get("content", ""))
    jsonld_text = _extract_json_ld_text(soup)

    visible_text = _normalize_whitespace(soup.get_text(" ", strip=True))
    text_blob = _normalize_whitespace(" ".join([page_title, meta_desc, jsonld_text, visible_text[:5000]]))

    extracted_keywords, detected_skills = _extract_candidate_keywords(text_blob)

    payload = {
        "upwork_url": upwork_url,
        "synced_at": datetime.utcnow().isoformat(),
        "headline": page_title,
        "overview": meta_desc or jsonld_text[:500],
        "extracted_keywords": extracted_keywords,
        "detected_skills": detected_skills,
        "source": "upwork_public_profile",
    }
    return payload


def save_dynamic_profile(payload: dict[str, Any]) -> Path:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _DATA_PATH


def sync_profile_from_upwork(upwork_url: str) -> dict[str, Any]:
    payload = fetch_and_extract_upwork_profile(upwork_url)
    save_dynamic_profile(payload)
    return payload
