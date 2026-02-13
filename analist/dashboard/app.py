"""
Upwork DNA v5 – AI Career Intelligence Dashboard
=================================================
Profile-aware job decision system with:
- Smart HOT job ranking with apply/skip actions
- AI-powered profile guidance & keyword strategy
- Full export/download for ChatGPT sharing
- Actionable recommendations at every step
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import plotly.express as px
import streamlit as st

API = os.getenv("UPWORK_ORCHESTRATOR_API", "http://127.0.0.1:8000")

# ═══════════════════════════════════════════════════════════════
# API helpers
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=25)
def get(ep, default=None, timeout=5):
    try:
        with urlopen(Request(f"{API}{ep}", headers={"Accept": "application/json"}), timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return default if default is not None else {}


def get_live(ep, default=None, timeout=5):
    try:
        with urlopen(Request(f"{API}{ep}", headers={"Accept": "application/json"}), timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return default if default is not None else {}

def post(ep, timeout=120):
    import urllib.request
    req = urllib.request.Request(f"{API}{ep}", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def delete(ep):
    import urllib.request
    try:
        with urlopen(urllib.request.Request(f"{API}{ep}", method="DELETE"), timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════════

def reasons(raw) -> dict:
    if isinstance(raw, dict): return raw
    if isinstance(raw, list): return {"tags": raw}
    if isinstance(raw, str):
        try:
            p = json.loads(raw)
            return p if isinstance(p, dict) else {"tags": p} if isinstance(p, list) else {}
        except Exception: pass
    return {}

def trunc(t, n=200): return (t[:n] + "…") if t and len(t) > n else (t or "")

def badge(score, mx=100):
    p = score / mx if mx else 0
    c = "#22c55e" if p >= 0.7 else "#f59e0b" if p >= 0.5 else "#ef4444"
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{score:.0f}</span>'

def build_export_text(profile, enriched, keywords, kw_fit):
    """Build a comprehensive text report for ChatGPT/external AI sharing."""
    lines = []
    lines.append("=" * 60)
    lines.append("UPWORK DNA – FULL ANALYSIS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    # Profile section
    if profile:
        lines.append("\n## FREELANCER PROFILE")
        lines.append(f"Name: {profile.get('name', 'N/A')}")
        lines.append(f"Title: {profile.get('title', 'N/A')}")
        lines.append(f"Rate: {profile.get('hourly_range', 'N/A')}")
        lines.append(f"Completed Jobs: {profile.get('total_upwork_jobs', 0)}")
        lines.append(f"Core Skills: {', '.join(profile.get('core_skills', []))}")
        lines.append(f"Secondary Skills: {', '.join(profile.get('secondary_skills', []))}")
        lines.append(f"Service Lines: {', '.join(profile.get('service_lines', []))}")
        strat = profile.get("strategy", {})
        lines.append(f"Strategy Phase: {strat.get('phase', 'N/A')}")
        lines.append(f"Priority: {strat.get('priority', 'N/A')}")
        lines.append(f"Notes: {strat.get('notes', '')}")
        lines.append(f"Portfolio: {', '.join(profile.get('portfolio_projects', []))}")

    # Keyword fit
    if kw_fit:
        lines.append("\n## KEYWORD-PROFILE FIT ANALYSIS")
        lines.append(f"{'Keyword':<35} {'Fit':>5}  {'Status':<20} Reason")
        lines.append("-" * 90)
        for k in sorted(kw_fit, key=lambda x: x.get("fit_score", 0), reverse=True):
            status = "⭐ IDEAL" if k.get("is_ideal") else ("⛔ AVOID" if k.get("is_avoid") else "")
            lines.append(f"{k['keyword']:<35} {k.get('fit_score', 0):>5.0%}  {status:<20} {k.get('fit_reason', '')}")

    # Top jobs analysis
    if enriched:
        lines.append("\n## TOP JOB OPPORTUNITIES")
        lines.append(f"Total jobs in database: {len(enriched)}")

        analyzed = [j for j in enriched if reasons(j.get("reasons", "")).get("llm_action")]
        apply_jobs = [j for j in analyzed if reasons(j.get("reasons", "")).get("llm_action") == "APPLY"]
        watch_jobs = [j for j in analyzed if reasons(j.get("reasons", "")).get("llm_action") == "WATCH"]
        skip_jobs = [j for j in analyzed if reasons(j.get("reasons", "")).get("llm_action") == "SKIP"]

        lines.append(f"LLM Analyzed: {len(analyzed)} | APPLY: {len(apply_jobs)} | WATCH: {len(watch_jobs)} | SKIP: {len(skip_jobs)}")

        for label, subset in [("✅ APPLY (Best Matches)", apply_jobs), ("👀 WATCH (Potential)", watch_jobs[:10])]:
            if not subset: continue
            lines.append(f"\n### {label}")
            for j in subset:
                r = reasons(j.get("reasons", ""))
                lines.append(f"\n  Title: {j.get('title', 'N/A')}")
                lines.append(f"  URL: {j.get('url', 'N/A')}")
                lines.append(f"  Budget: {j.get('budget', 'N/A')}")
                lines.append(f"  Skills: {j.get('skills', 'N/A')}")
                lines.append(f"  Proposals: {j.get('proposals', 'N/A')}")
                lines.append(f"  Client Verified: {j.get('payment_verified', False)}")
                lines.append(f"  Composite Score: {r.get('composite_score', 0)}")
                lines.append(f"  LLM Summary: {r.get('llm_summary', '')}")
                lines.append(f"  LLM Reasoning: {r.get('llm_reasoning', '')}")
                lines.append(f"  Risk Flags: {', '.join(r.get('risk_flags', []))}")
                lines.append(f"  Opening Hook: {r.get('opening_hook', '')}")
                desc = j.get("description", "")
                if desc:
                    lines.append(f"  Description: {desc[:500]}")

    # Keywords
    if keywords:
        lines.append("\n## KEYWORD MARKET DATA")
        lines.append(f"{'Keyword':<35} {'Demand':>7} {'Supply':>7} {'Gap':>6} {'Score':>6} {'Priority':<10}")
        lines.append("-" * 80)
        for k in sorted(keywords, key=lambda x: x.get("opportunity_score", 0), reverse=True):
            lines.append(
                f"{k.get('keyword', ''):<35} {k.get('demand', 0):>7} {k.get('supply', 0):>7} "
                f"{k.get('gap_ratio', 0):>6.1f} {k.get('opportunity_score', 0):>6.1f} {k.get('recommended_priority', ''):<10}"
            )

    lines.append("\n" + "=" * 60)
    lines.append("END OF REPORT")
    lines.append("You can paste this into ChatGPT and ask:")
    lines.append('- "Which jobs should I apply to first and why?"')
    lines.append('- "Write a proposal for [job title]"')
    lines.append('- "How should I improve my profile for these opportunities?"')
    lines.append('- "What keywords should I add/remove?"')
    lines.append("=" * 60)

    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════

def load():
    summary = get("/v1/telemetry/summary", {})
    enriched = get("/v1/opportunities/enriched?limit=300&max_proposals=50", [])
    keywords = get("/v1/recommendations/keywords?limit=120", [])
    llm = get("/v1/llm/health", {"status": "unavailable"})
    notifs = get("/v1/llm/notifications", {"notifications": []})
    profile = get("/v1/llm/profile", {})
    profile_live = get_live("/v1/llm/profile/competitive-live", {})
    kw_fit = get("/v1/llm/keyword-fit", [])

    return {
        "summary": summary,
        "enriched": enriched,
        "keywords": keywords,
        "llm": llm,
        "notifs": notifs.get("notifications", []) if isinstance(notifs, dict) else [],
        "profile": profile,
        "profile_live": profile_live,
        "kw_fit": kw_fit,
    }

# ═══════════════════════════════════════════════════════════════
# TAB 1: 🎯 Başvuru Kararları (Main Decision Tab)
# ═══════════════════════════════════════════════════════════════

def tab_decisions(data):
    """Main tab: which jobs to apply to, ranked, with actions."""
    profile = data["profile"]
    enriched = data["enriched"]
    notifs = data.get("notifs", [])

    if not enriched:
        st.warning("Henüz iş verisi yok. Extension ile scraping yapın.")
        return

    # Build HOT notification lookup  (job_key → notif)
    hot_lookup = {}
    for n in notifs:
        if isinstance(n, dict) and n.get("priority") == "HOT":
            hot_lookup[n.get("job_key", "")] = n

    df = pd.DataFrame(enriched)
    df["_r"] = df["reasons"].apply(reasons)
    df["action"] = df["_r"].apply(lambda d: d.get("llm_action", ""))
    # Normalize composite to 0-100 consistently
    def _norm_composite(d):
        v = d.get("composite_score", 0)
        if isinstance(v, (int, float)) and v <= 1:
            return round(v * 100);
        return round(v) if isinstance(v, (int, float)) else 0
    df["composite"] = df["_r"].apply(_norm_composite)
    df["summary"] = df["_r"].apply(lambda d: d.get("llm_summary", ""))
    df["reasoning"] = df["_r"].apply(lambda d: d.get("llm_reasoning", ""))
    df["risk_flags"] = df["_r"].apply(lambda d: d.get("risk_flags", []))
    df["hook"] = df["_r"].apply(lambda d: d.get("opening_hook", ""))
    df["is_hot"] = df["job_key"].isin(hot_lookup)
    if "freshness" not in df.columns:
        df["freshness"] = 100.0
        df["freshness"] = 100.0

    # Controls row
    c1, c2, c3, c4, c5 = st.columns([1.2, 0.8, 1, 1, 1])
    with c1:
        if st.button("🤖 AI Analiz Başlat (10 iş)", type="primary", key="d_analyze"):
            with st.spinner("AI analiz ediyor… (30-120 sn)"):
                r1 = post("/v1/llm/batch-analyze?limit=10&unanalyzed_only=true")
                # Fallback: if strict unanalyzed shortlist returns nothing, force a fresh sample.
                if isinstance(r1, dict) and r1.get("analyzed", 0) == 0 and r1.get("total", 0) == 0:
                    r1 = post("/v1/llm/batch-analyze?limit=10&unanalyzed_only=false")
                r2 = post("/v1/llm/decide?limit=20")
            if r1 and not r1.get("error"):
                st.success(f"✅ {r1.get('analyzed', 0)} iş analiz edildi!")
            else:
                st.error(f"Hata: {r1.get('error', 'LLM bağlantısı yok')}")
            if isinstance(r2, dict) and not r2.get("error"):
                st.caption(f"Decision Engine: HOT={r2.get('hot_count', 0)} | WARM={r2.get('warm_count', 0)}")
            elif isinstance(r2, dict):
                st.warning(f"Decision Engine uyarı: {r2.get('error', 'yanıt yok')}")
            st.cache_data.clear()
            st.rerun()
    with c2:
        if st.button("🔄 Yenile", key="d_refresh"):
            st.cache_data.clear()
            st.rerun()
    with c3:
        fresh_filter = st.checkbox("🟢 Sadece Taze İşler", value=True, key="d_fresh")
    with c4:
        sort_by = st.selectbox("Sıralama", ["Taze + Skor", "Profil Uyumu", "En Yeni", "En Yüksek Skor", "Bütçe"], key="d_sort")
    with c5:
        max_prop = st.selectbox("Max Proposals", [15, 30, 50, "Tümü"], key="d_maxp")

    # Apply freshness filter — but NEVER filter out HOT jobs
    if fresh_filter:
        df = df[(df["freshness"] >= 50) | (df["is_hot"])]
    if max_prop != "Tümü":
        def _parse_proposals(p):
            try:
                return int(''.join(c for c in str(p) if c.isdigit()) or "0")
            except Exception:
                return 0
        df = df[(df["proposals"].apply(_parse_proposals) <= int(max_prop)) | (df["is_hot"])]

    # Compute profile skill match count for each row
    _profile_skills = set()
    for s in (profile.get("core_skills", []) + profile.get("secondary_skills", [])):
        for w in s.lower().replace("(", " ").replace(")", " ").split(","):
            _profile_skills.update(w.strip().split())
    def _skill_match(skills_str):
        if not skills_str:
            return 0
        job_words = set(skills_str.lower().replace(";", " ").replace(",", " ").split())
        return len(_profile_skills & job_words)
    df["skill_match"] = df["skills"].fillna("").apply(_skill_match)

    # Sort function
    def _sort_df(frame):
        if sort_by == "En Yeni":
            return frame.sort_values("freshness", ascending=False)
        elif sort_by == "En Yüksek Skor":
            return frame.sort_values("composite", ascending=False)
        elif sort_by == "Bütçe":
            return frame.sort_values("budget_value", ascending=False, na_position="last")
        elif sort_by == "Profil Uyumu":
            return frame.sort_values(["skill_match", "composite"], ascending=[False, False])
        else:  # Taze + Skor (default)
            return frame.sort_values(["freshness", "composite"], ascending=[False, False])

    # Separate analyzed from pending
    analyzed = df[df["action"].isin(["APPLY", "WATCH", "SKIP"])].copy()
    pending_count = len(df[df["action"] == ""])

    # Stats
    apply_df = analyzed[analyzed["action"] == "APPLY"]
    watch_df = analyzed[analyzed["action"] == "WATCH"]
    skip_df = analyzed[analyzed["action"] == "SKIP"]
    hot_count = len(hot_lookup)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("📊 Toplam", len(df))
    m2.metric("🔥 HOT", hot_count)
    m3.metric("✅ BAŞVUR", len(apply_df))
    m4.metric("👀 TAKİP", len(watch_df))
    m5.metric("⏭️ GEÇ", len(skip_df))
    m6.metric("⏳ Bekleyen", pending_count)

    # ── 🔥 HOT JOBS SECTION ──
    if hot_lookup:
        st.markdown(
            f"""<div style="background:linear-gradient(135deg,#dc2626,#f97316);padding:14px 20px;border-radius:10px;color:white;margin:10px 0">
            <strong style="font-size:1.15rem">🔥 {hot_count} HOT Proje — Hemen Başvurmanız Gereken Fırsatlar</strong>
            <p style="margin:4px 0 0;opacity:0.9;font-size:0.9rem">Decision Engine tarafından yüksek öncelikli olarak işaretlendi</p>
            </div>""", unsafe_allow_html=True)
        # Render HOT jobs — prefer enriched card if available
        hot_in_df = df[df["is_hot"]].copy()
        rendered_hot_keys = set()
        if not hot_in_df.empty:
            hot_in_df = _sort_df(hot_in_df)
            for _, row in hot_in_df.iterrows():
                _render_decision_card(row, "hot", profile)
                rendered_hot_keys.add(row.get("job_key", ""))
        # Fallback: render remaining HOT notifications not in filtered df
        for jk, n in hot_lookup.items():
            if jk in rendered_hot_keys:
                continue
            comp_v = n.get("composite_score", 0)
            if isinstance(comp_v, (int, float)) and comp_v <= 1:
                comp_v = int(comp_v * 100)
            ts = n.get("timestamp", "")
            time_label = ""
            if ts:
                try:
                    from datetime import datetime as dt
                    delta = dt.now() - dt.fromisoformat(str(ts).replace("Z","").split("+")[0])
                    h = delta.total_seconds() / 3600
                    time_label = f" | 🕐 {int(h)} saat önce" if h < 24 else f" | 🕐 {int(h/24)} gün önce"
                except Exception:
                    pass
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#991b1b,#dc2626);padding:14px 18px;border-radius:10px;color:white;margin-bottom:8px">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <strong style="font-size:1.05rem">🔥 {n.get('title', 'Unknown')}</strong>
                    <span style="background:rgba(255,255,255,0.2);padding:3px 12px;border-radius:20px;font-size:0.9rem">{comp_v}%</span>
                </div>
                <p style="margin:6px 0 2px;font-size:0.9rem;opacity:0.95">{trunc(n.get('summary', ''), 200)}</p>
                <div style="font-size:0.85rem;opacity:0.8">{trunc(n.get('reason', ''), 200)}{time_label}</div>
                </div>""", unsafe_allow_html=True)
        st.divider()

    if analyzed.empty:
        st.info(f"Henüz AI analizi yapılmamış. {pending_count} iş bekliyor. Yukarıdaki 'AI Analiz' butonuna tıklayın.")
        return

    # Profile context bar
    if profile.get("name"):
        st.markdown(
            f"""<div style="background:#1e40af;color:white;padding:10px 16px;border-radius:8px;margin:8px 0;font-size:0.9rem">
            👤 <strong>{profile['name']}</strong> | {profile.get('title', '')} | 💰 {profile.get('hourly_range', '')} | 
            📋 {profile.get('total_upwork_jobs', 0)} iş | 🎯 {profile.get('strategy', {}).get('phase', 'growth')} fazı
            </div>""", unsafe_allow_html=True)

    # ── APPLY JOBS (most important) ──
    if not apply_df.empty:
        st.markdown(f"### ✅ BAŞVUR — {len(apply_df)} İş (Hemen Başvurmanız Gerekenler)")
        for _, row in _sort_df(apply_df).iterrows():
            _render_decision_card(row, "apply", profile)

    # ── WATCH JOBS ──
    if not watch_df.empty:
        with st.expander(f"👀 TAKİP ET — {len(watch_df)} İş (Potansiyel, yorum gerek)", expanded=len(apply_df) == 0):
            for _, row in _sort_df(watch_df).head(15).iterrows():
                _render_decision_card(row, "watch", profile)

    # ── SKIP JOBS ──
    if not skip_df.empty:
        with st.expander(f"⏭️ GEÇ — {len(skip_df)} İş (AI'ya göre uygun değil)"):
            for _, row in _sort_df(skip_df).head(10).iterrows():
                _render_decision_card(row, "skip", profile)

    # Download button
    st.divider()
    export = build_export_text(profile, enriched, data["keywords"], data["kw_fit"])
    st.download_button(
        "📥 Tüm Analizi İndir (ChatGPT'ye gönder)",
        data=export,
        file_name=f"upwork_dna_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
        type="primary",
    )
    st.caption("İndirdiğiniz dosyayı ChatGPT'ye yapıştırıp 'Hangi işlere başvurmalıyım?' diye sorabilirsiniz.")


def _render_decision_card(row, ctype, profile=None):
    """Render a single job decision card."""
    url = row.get("url", "")
    title = row.get("title", "Untitled")
    budget = row.get("budget", "")
    proposals = row.get("proposals", "")
    skills = row.get("skills", "")
    desc = row.get("description", "")
    verified = row.get("payment_verified", False)
    comp = row.get("composite", 0)
    summary = row.get("summary", "")
    reasoning = row.get("reasoning", "")
    hook = row.get("hook", "")
    flags = row.get("risk_flags", [])
    freshness = row.get("freshness", 100)
    scraped_at = row.get("scraped_at", "")

    # Skill match badge
    skill_match_html = ""
    if profile and skills:
        p_skills = set()
        for s in profile.get("core_skills", []) + profile.get("secondary_skills", []):
            p_skills.update(s.lower().replace("-", " ").split())
        p_skills.discard("")
        job_words = set(skills.lower().replace(";", " ").replace(",", " ").split())
        matched = p_skills & job_words
        match_count = len(matched)
        if match_count >= 3:
            match_color = "#22c55e"
            match_label = "Harika Uyum"
        elif match_count >= 1:
            match_color = "#eab308"
            match_label = "Kısmi Uyum"
        else:
            match_color = "#ef4444"
            match_label = "Düşük Uyum"
        skill_match_html = f'<span style="background:{match_color};padding:3px 8px;border-radius:20px;font-size:0.8rem;margin-left:6px">🎯 {match_count} {match_label}</span>'

    if isinstance(comp, (int, float)) and comp <= 1:
        comp = int(comp * 100)
    else:
        comp = int(comp) if isinstance(comp, (int, float)) else 0

    # Freshness badge
    if freshness >= 80:
        fresh_icon = "🟢"
        fresh_label = "Taze"
    elif freshness >= 50:
        fresh_icon = "🟡"
        fresh_label = "Orta"
    else:
        fresh_icon = "🔴"
        fresh_label = "Eski"

    # Parse proposals count for warning
    try:
        p_num = int(''.join(c for c in str(proposals) if c.isdigit()) or "0")
    except Exception:
        p_num = 0
    proposals_warn = ""
    if p_num >= 50:
        proposals_warn = ' <span style="background:#ef4444;padding:1px 6px;border-radius:3px;font-size:0.75rem">⚠️ ÇOK FAZLA</span>'
    elif p_num >= 30:
        proposals_warn = ' <span style="background:#f59e0b;padding:1px 6px;border-radius:3px;font-size:0.75rem">⚠️ YOĞUN</span>'

    # Scraped time ago
    time_ago = ""
    if scraped_at:
        try:
            from datetime import datetime as dt
            scraped = dt.fromisoformat(str(scraped_at).replace("Z", "").split("+")[0])
            delta = dt.now() - scraped
            hours = delta.total_seconds() / 3600
            if hours < 24:
                time_ago = f"{int(hours)} saat önce"
            else:
                time_ago = f"{int(hours / 24)} gün önce"
        except Exception:
            time_ago = ""

    # Colors per type
    colors = {
        "apply": ("linear-gradient(135deg,#065f46,#10b981)", "🟢"),
        "hot": ("linear-gradient(135deg,#991b1b,#f97316)", "🔥"),
        "watch": ("linear-gradient(135deg,#92400e,#f59e0b)", "🟡"),
        "skip": ("linear-gradient(135deg,#991b1b,#ef4444)", "🔴"),
    }
    bg, icon = colors.get(ctype, ("linear-gradient(135deg,#6b7280,#9ca3af)", "⚪"))

    verified_badge = "✅ Verified" if verified else "❌ Unverified"
    link_html = f'<a href="{url}" target="_blank" style="color:#fef08a;text-decoration:underline;font-size:0.85rem">🔗 Upwork\'da Aç</a>' if url else ""

    flag_html = ""
    if flags:
        pos = [f for f in flags if "BOOST" in f or "STRATEGY" in f]
        neg = [f for f in flags if f not in pos]
        if pos:
            flag_html += f'<div style="color:#86efac;font-size:0.8rem;margin-top:4px">✨ {" | ".join(pos)}</div>'
        if neg:
            flag_html += f'<div style="color:#fca5a5;font-size:0.8rem;margin-top:4px">⚠️ {" | ".join(neg)}</div>'

    hook_html = f'<div style="background:rgba(255,255,255,0.1);padding:8px;border-radius:6px;margin-top:8px;font-style:italic;font-size:0.9rem">💬 "{trunc(hook, 200)}"</div>' if hook else ""

    reasoning_html = f'<div style="font-size:0.85rem;margin-top:6px;opacity:0.9">📝 {trunc(reasoning, 300)}</div>' if reasoning else ""

    st.markdown(
        f"""<div style="background:{bg};padding:16px 20px;border-radius:10px;color:white;margin-bottom:10px">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <strong style="font-size:1.1rem">{icon} {title}</strong>
            <div>
                <span style="background:rgba(255,255,255,0.2);padding:3px 12px;border-radius:20px;font-weight:bold;margin-right:6px">
                    Skor: {comp}%
                </span>
                <span style="background:rgba(255,255,255,0.15);padding:3px 8px;border-radius:20px;font-size:0.8rem">
                    {fresh_icon} {fresh_label}
                </span>
                {skill_match_html}
            </div>
        </div>
        <p style="margin:6px 0;font-size:0.9rem;opacity:0.95">{trunc(summary, 200)}</p>
        <div style="display:flex;gap:16px;font-size:0.85rem;opacity:0.8;flex-wrap:wrap">
            {'<span>💰 ' + str(budget) + '</span>' if budget else ''}
            <span>📨 {proposals} proposals{proposals_warn}</span>
            <span>💳 {verified_badge}</span>
            {'<span>🕐 ' + time_ago + '</span>' if time_ago else ''}
        </div>
        {'<div style="font-size:0.8rem;opacity:0.7;margin-top:2px">🛠️ ' + trunc(skills, 120) + '</div>' if skills else ''}
        {flag_html}
        {reasoning_html}
        {hook_html}
        <div style="margin-top:8px;display:flex;gap:12px">
            {link_html}
        </div>
        </div>""",
        unsafe_allow_html=True,
    )



# ═══════════════════════════════════════════════════════════════
# TAB 2: 📋 Tüm İşler Browser
# ═══════════════════════════════════════════════════════════════

def tab_jobs(data):
    enriched = data["enriched"]
    if not enriched:
        st.info("Henüz veri yok.")
        return

    df = pd.DataFrame(enriched)
    df["_r"] = df["reasons"].apply(reasons)
    df["action"] = df["_r"].apply(lambda d: d.get("llm_action", ""))
    df["composite"] = df["_r"].apply(lambda d: d.get("composite_score", 0))

    # Filters
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kws = sorted(df["keyword"].dropna().unique().tolist())
        kw = st.selectbox("Keyword", ["Tümü"] + kws, key="jb_kw")
    with c2:
        act = st.selectbox("AI Karar", ["Tümü", "APPLY", "WATCH", "SKIP", "Bekleyen"], key="jb_act")
    with c3:
        sort = st.selectbox("Sırala", ["Fit Score", "Composite", "Budget", "Freshness"], key="jb_sort")
    with c4:
        verified_only = st.checkbox("Sadece Verified", key="jb_ver")
    with c5:
        fresh_only_jb = st.checkbox("🟢 Taze", value=True, key="jb_fresh")

    if "freshness" not in df.columns:
        df["freshness"] = 100.0

    f = df.copy()
    if kw != "Tümü": f = f[f["keyword"] == kw]
    if act == "Bekleyen": f = f[f["action"] == ""]
    elif act != "Tümü": f = f[f["action"] == act]
    if verified_only: f = f[f["payment_verified"] == True]
    if fresh_only_jb: f = f[f["freshness"] >= 50]

    scol = {"Fit Score": "fit_score", "Composite": "composite", "Budget": "budget_value", "Freshness": "freshness"}.get(sort, "fit_score")
    f = f.sort_values(scol, ascending=False, na_position="last")

    st.caption(f"{min(50, len(f))} / {len(f)} iş gösteriliyor (toplam: {len(df)})")

    for _, row in f.head(50).iterrows():
        a = row.get("action", "")
        url = row.get("url", "")
        freshness = row.get("freshness", 100)
        fresh_dot = "🟢" if freshness >= 80 else ("🟡" if freshness >= 50 else "🔴")
        ab = {"APPLY": ("✅", "#22c55e"), "WATCH": ("👀", "#f59e0b"), "SKIP": ("⏭️", "#ef4444")}.get(a, ("⏳", "#6b7280"))
        tl = f'<a href="{url}" target="_blank" style="color:#1a7a3a;text-decoration:none;font-weight:bold">{row["title"]}</a>' if url else f'<b>{row["title"]}</b>'

        st.markdown(
            f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;margin-bottom:6px;background:white">
            <div style="display:flex;justify-content:space-between;align-items:center">
                {tl}
                <span style="background:{ab[1]};color:white;padding:2px 10px;border-radius:12px;font-size:0.8rem">{ab[0]} {a or 'Pending'} {fresh_dot}</span>
            </div>
            <div style="margin-top:4px;font-size:0.85rem;color:#6b7280">
                🔑 {row['keyword']}
                {'  |  💰 ' + str(row.get('budget', '')) if row.get('budget') else ''}
                {'  |  📨 ' + str(row.get('proposals', '')) if row.get('proposals') else ''}
                {'  |  ✅ Verified' if row.get('payment_verified') else '  |  ❌ Unverified'}
            </div>
            <p style="margin:4px 0;font-size:0.88rem;color:#374151">{trunc(row.get('description', ''), 200)}</p>
            <div style="display:flex;gap:10px;font-size:0.8rem">
                <span>Fit: {badge(row['fit_score'])}</span>
                <span>Safety: {badge(row['safety_score'])}</span>
                <span>Opp: {badge(row['opportunity_score'])}</span>
                <span>Fresh: {badge(freshness)}</span>
            </div>
            </div>""",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════
# TAB 3: 📝 Proposal Üretici
# ═══════════════════════════════════════════════════════════════

def tab_proposal(data):
    enriched = data["enriched"]
    if not enriched:
        st.info("Önce job analizi yapın.")
        return

    df = pd.DataFrame(enriched)
    df["_r"] = df["reasons"].apply(reasons)
    df["action"] = df["_r"].apply(lambda d: d.get("llm_action", ""))

    # Prioritize APPLY jobs
    candidates = df[df["action"] == "APPLY"].to_dict("records")
    if not candidates:
        candidates = df[df["apply_now"] == True].head(20).to_dict("records")
    if not candidates:
        candidates = df.sort_values("fit_score", ascending=False).head(20).to_dict("records")

    opts = {}
    for j in candidates:
        b = f" | {j.get('budget', '')}" if j.get("budget") else ""
        opts[f"{j['title'][:55]}{b}"] = j["job_key"]

    sel = st.selectbox("📌 Proposal yazılacak işi seç:", list(opts.keys()), key="p_sel")
    key = opts.get(sel, "")
    job = next((j for j in candidates if j["job_key"] == key), {})

    if job:
        with st.expander("📄 İş Detayı", expanded=True):
            url = job.get("url", "")
            if url: st.markdown(f"🔗 [Upwork'da Aç]({url})")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**💰 Budget:** {job.get('budget', 'N/A')}")
            c2.markdown(f"**📨 Proposals:** {job.get('proposals', 'N/A')}")
            c3.markdown(f"**💳 Verified:** {'✅' if job.get('payment_verified') else '❌'}")
            st.markdown(f"**🛠️ Skills:** {job.get('skills', 'N/A')}")
            d = job.get("description", "")
            if d: st.markdown(f"**📝 Açıklama:** {d[:800]}")

    if st.button("✍️ AI Proposal Yaz", type="primary", key="p_gen"):
        with st.spinner("AI proposal yazıyor… (15-45 sn)"):
            r = post(f"/v1/llm/generate-proposal/{key}")

        if r and not r.get("error") and not r.get("llm_error"):
            st.success("✅ Proposal hazır!")
            cover = r.get("cover_letter", "")

            st.markdown("### 💌 Cover Letter")
            st.markdown(f"""<div style="background:#f0f9ff;padding:16px;border-radius:8px;border-left:4px solid #2563eb;white-space:pre-wrap;line-height:1.7">{cover}</div>""", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            c1.markdown(f"**💰 Teklif:** {r.get('bid_amount', 'N/A')}")
            c1.markdown(f"**📅 Süre:** {r.get('estimated_timeline', 'N/A')}")
            c2.markdown(f"**💡 Gerekçe:** {r.get('bid_rationale', '')}")

            diffs = r.get("key_differentiators", [])
            if diffs:
                st.markdown("**🎯 Öne Çıkan Yönler:**")
                for d in diffs: st.markdown(f"- {d}")

            cta = r.get("call_to_action", "")
            if cta: st.markdown(f"**📞 Kapanış:** _{cta}_")

            # Download proposal
            proposal_text = f"Job: {job.get('title', '')}\nURL: {job.get('url', '')}\n\n{cover}\n\nBid: {r.get('bid_amount', '')}\nTimeline: {r.get('estimated_timeline', '')}"
            st.download_button("📥 Proposal İndir", data=proposal_text, file_name=f"proposal_{key[:20]}.txt", mime="text/plain")

            st.text_area("📋 Kopyala:", value=cover, height=200, key="p_copy")

        elif r and r.get("llm_error"):
            st.error(f"LLM Hatası: {r['llm_error']}")
        else:
            st.error(f"Hata: {r.get('error', 'Bağlantı sorunu') if r else 'API yanıt vermedi'}")


# ═══════════════════════════════════════════════════════════════
# TAB 4: 👤 Profil & Strateji
# ═══════════════════════════════════════════════════════════════

def tab_profile(data):
    profile = data.get("profile", {})
    profile_live = data.get("profile_live", {})
    kw_fit = data.get("kw_fit", [])

    if not profile.get("name"):
        st.warning("Profil yüklenemedi.")
        return

    # Profile card
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#1e40af,#3b82f6);padding:20px;border-radius:12px;color:white;margin-bottom:16px">
        <h2 style="margin:0">👤 {profile['name']}</h2>
        <p style="margin:6px 0 0;opacity:0.9;font-size:1.1rem">{profile.get('title', '')}</p>
        <div style="display:flex;gap:24px;margin-top:12px;font-size:0.95rem">
            <span>💰 {profile.get('hourly_range', '')}</span>
            <span>📋 {profile.get('total_upwork_jobs', 0)} tamamlanmış iş</span>
            <span>🎯 Faz: {profile.get('strategy', {}).get('phase', 'growth').upper()}</span>
        </div>
        </div>""", unsafe_allow_html=True)

    # Skills
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔧 Core Skills")
        for s in profile.get("core_skills", []): st.markdown(f"- ✅ {s}")
    with c2:
        st.markdown("### 📦 Secondary Skills")
        for s in profile.get("secondary_skills", []): st.markdown(f"- {s}")

    # Services
    st.markdown("### 💼 Hizmet Alanları")
    cols = st.columns(3)
    for i, s in enumerate(profile.get("service_lines", [])): cols[i % 3].markdown(f"🔹 {s}")

    # Portfolio
    st.markdown("### 🏆 Portfolio")
    for p in profile.get("portfolio_projects", []): st.markdown(f"- 📂 {p}")

    # Strategy
    st.divider()
    strat = profile.get("strategy", {})
    st.markdown(
        f"""<div style="background:#fef3c7;padding:14px;border-radius:8px;border-left:4px solid #f59e0b">
        <strong>🎯 Strateji:</strong> {strat.get('phase', 'growth').upper()} | 
        <strong>Öncelik:</strong> {strat.get('priority', '')} <br/>
        <strong>Notlar:</strong> {strat.get('notes', '')}
        </div>""", unsafe_allow_html=True)

    # Keyword fit
    st.divider()
    st.markdown("### 🔑 Keyword–Profil Uyumu")
    if kw_fit:
        df_fit = pd.DataFrame(kw_fit)
        fig = px.bar(
            df_fit.sort_values("fit_score", ascending=True),
            x="fit_score", y="keyword", orientation="h",
            color="fit_score", color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            range_color=[0, 1], title="Keyword → Profil Uyum Skoru",
            labels={"fit_score": "Uyum", "keyword": ""},
        )
        fig.update_layout(height=max(300, len(df_fit) * 28), margin=dict(l=0, r=0, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        for k in kw_fit:
            icon = "🟢" if k["fit_score"] >= 0.7 else ("🟡" if k["fit_score"] >= 0.4 else "🔴")
            ex = " ⭐" if k.get("is_ideal") else (" ⛔" if k.get("is_avoid") else "")
            st.markdown(f"{icon} **{k['keyword']}** — {k['fit_score']:.0%}{ex} | _{k.get('fit_reason', '')}_")

    # Live sync + competitive benchmark
    st.divider()
    st.markdown("### ⚡ Canlı Senkron & Rekabet Analizi")
    if profile_live and isinstance(profile_live, dict):
        synced_at = profile_live.get("synced_at") or "-"
        market = profile_live.get("market_snapshot", {}) or {}
        bench = profile_live.get("benchmark", {}) or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔄 Son Sync", str(synced_at)[:19] if synced_at else "-")
        c2.metric("🏁 HOT APPLY", int(market.get("hot_apply_jobs", 0)))
        c3.metric("👥 Talent Havuzu", int(market.get("talent_scanned", 0)))
        c4.metric("📈 Readiness", f"{bench.get('readiness_score', 0):.1f}")

        b1, b2, b3 = st.columns(3)
        b1.metric("💰 Pazar Median Rate", f"${market.get('median_hourly_rate', 0)}/hr")
        b2.metric("⭐ Pazar Median Rating", f"{market.get('median_rating', 0)}")
        b3.metric("📋 Deneyim Açığı", bench.get("experience_gap", 0))

        actions = profile_live.get("priority_actions", []) or []
        if actions:
            st.markdown("**Öncelikli Aksiyonlar**")
            for action in actions:
                st.markdown(f"- {action}")

        top_comp = profile_live.get("top_competitors", []) or []
        if top_comp:
            comp_df = pd.DataFrame(top_comp)
            show_cols = [
                c for c in [
                    "name", "title", "hourly_rate", "rating", "jobs_completed",
                    "skill_overlap", "competitive_score"
                ] if c in comp_df.columns
            ]
            st.markdown("**En Güçlü Rakipler (Canlı Havuz)**")
            st.dataframe(comp_df[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Canlı profil benchmark verisi henüz hazır değil. Extension profil sync sonrası otomatik düşer.")

    # Ideal/Avoid keywords
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✅ İdeal Keywords")
        for k in profile.get("ideal_job_keywords", []): st.markdown(f"🟢 {k}")
    with c2:
        st.markdown("### ⛔ Kaçınılacak")
        for k in profile.get("avoid_keywords", []): st.markdown(f"🔴 {k}")

    # Download profile
    st.divider()
    profile_text = build_export_text(profile, [], [], kw_fit)
    st.download_button(
        "📥 Profil Raporunu İndir",
        data=profile_text,
        file_name=f"upwork_profile_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )


# ═══════════════════════════════════════════════════════════════
# TAB 5: 🧠 Keyword Strateji (LLM)
# ═══════════════════════════════════════════════════════════════

def tab_keyword_strategy(data):
    st.markdown(
        """<div style="background:linear-gradient(135deg,#7c3aed,#a855f7);padding:16px;border-radius:12px;color:white;margin-bottom:16px">
        <h3 style="margin:0">🧠 AI Keyword Strateji Danışmanı</h3>
        <p style="margin:6px 0 0;opacity:0.85">LLM, keyword performansını profilinize göre analiz edip değişiklik önerir.</p>
        </div>""", unsafe_allow_html=True)

    # Current keyword fit quick view
    kw_fit = data.get("kw_fit", [])
    if kw_fit:
        top = sorted(kw_fit, key=lambda x: x["fit_score"], reverse=True)[:5]
        low = sorted(kw_fit, key=lambda x: x["fit_score"])[:5]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("🟢 **En Uyumlu:**")
            for k in top: st.markdown(f"  - {k['keyword']} ({k['fit_score']:.0%})")
        with c2:
            st.markdown("🔴 **En Az Uyumlu:**")
            for k in low: st.markdown(f"  - {k['keyword']} ({k['fit_score']:.0%})")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧠 AI Strateji Analizi", type="primary", key="ks_analyze"):
            with st.spinner("LLM keyword analizi… (15-45 sn)"):
                r = post("/v1/llm/keyword-strategy")

            if r and not r.get("error") and not r.get("llm_error"):
                st.success("✅ Analiz tamamlandı!")
                st.session_state["kw_strategy_result"] = r
            elif r and r.get("llm_error"):
                st.error(f"LLM Hatası: {r['llm_error']}")
            else:
                st.error(f"Hata: {r.get('error', 'Bağlantı sorunu') if r else 'API cevap vermedi'}")

    with c2:
        if st.button("🔍 Yeni Keyword Bul", key="ks_discover"):
            with st.spinner("AI keyword keşfi… (10-30 sn)"):
                r = post("/v1/llm/discover-keywords")
            if r and isinstance(r, list) and len(r) > 0:
                st.success(f"✅ {len(r)} öneri!")
                st.session_state["kw_discover_result"] = r
            else:
                st.error("Öneri üretilemedi.")

    # Show strategy result
    sr = st.session_state.get("kw_strategy_result")
    if sr:
        st.divider()
        if sr.get("overall_strategy"):
            st.markdown(f"""<div style="background:#f0f9ff;padding:14px;border-radius:8px;border-left:4px solid #2563eb;margin:8px 0">
            <strong>📋 Genel Strateji:</strong><br/>{sr['overall_strategy']}</div>""", unsafe_allow_html=True)

        for label, key, icon, desc in [
            ("Koru", "keep", "🟢", "performans iyi"),
            ("Değiştir", "modify", "🔄", None),
            ("Kaldır", "drop", "❌", None),
            ("Ekle", "add", "➕", None),
        ]:
            items = sr.get(key, [])
            if not items: continue
            st.markdown(f"### {icon} {label} ({len(items)})")
            for item in items:
                if isinstance(item, str):
                    st.markdown(f"{icon} **{item}** — {desc}")
                elif isinstance(item, dict):
                    if "from" in item:
                        st.markdown(f"🔄 **{item['from']}** → **{item['to']}** — _{item.get('reason', '')}_")
                    elif "keyword" in item:
                        comp = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(item.get("expected_competition", ""), "⚪")
                        st.markdown(f"{comp} **{item['keyword']}** — _{item.get('reason', '')}_")

        # Download strategy
        strat_text = json.dumps(sr, indent=2, ensure_ascii=False)
        st.download_button("📥 Strateji Raporu İndir", data=strat_text, file_name="keyword_strategy.json", mime="application/json")

    # Show discover result
    dr = st.session_state.get("kw_discover_result")
    if dr:
        st.divider()
        st.markdown("### 🔍 Keşfedilen Yeni Keywords")
        for k in dr:
            rel = k.get("relevance_to_skills", 0)
            if isinstance(rel, float) and rel <= 1: rel = int(rel * 100)
            st.markdown(f"🔹 **{k['keyword']}** — Rekabet: {k.get('expected_competition', '?')} | Uyum: {rel}% | {k.get('rationale', '')}")


# ═══════════════════════════════════════════════════════════════
# TAB 6: 📊 Pazar Verileri
# ═══════════════════════════════════════════════════════════════

def tab_market(data):
    keywords = data["keywords"]
    if not keywords:
        st.info("Keyword verisi yok.")
        return

    df = pd.DataFrame(keywords)

    # Gap chart
    top = df.sort_values("gap_ratio", ascending=False).head(15)
    fig = px.bar(top, x="keyword", y="gap_ratio", color="opportunity_score",
                 color_continuous_scale="Greens", title="🎯 Düşük Rekabet Fırsatları (Gap Ratio)",
                 labels={"gap_ratio": "Gap", "opportunity_score": "Fırsat"})
    fig.update_layout(height=350, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Scatter
    fig2 = px.scatter(df, x="supply", y="demand", size="opportunity_score",
                      color="recommended_priority",
                      color_discrete_map={"CRITICAL": "#dc2626", "HIGH": "#f59e0b", "NORMAL": "#3b82f6", "LOW": "#9ca3af"},
                      hover_name="keyword", title="📈 Demand vs Supply")
    fig2.update_layout(height=350, margin=dict(t=40, b=20))
    st.plotly_chart(fig2, use_container_width=True)

    # Table
    st.dataframe(
        df[["keyword", "recommended_priority", "opportunity_score", "demand", "supply", "gap_ratio"]].rename(
            columns={"recommended_priority": "Öncelik", "opportunity_score": "Skor", "gap_ratio": "Gap"}
        ), use_container_width=True, hide_index=True)

    # Download
    csv = df.to_csv(index=False)
    st.download_button("📥 Keyword Verisi İndir (CSV)", data=csv, file_name="keyword_market_data.csv", mime="text/csv")


# ═══════════════════════════════════════════════════════════════
# TAB 7: 📥 Export Center
# ═══════════════════════════════════════════════════════════════

def tab_export(data):
    st.markdown(
        """<div style="background:linear-gradient(135deg,#0f766e,#14b8a6);padding:16px;border-radius:12px;color:white;margin-bottom:16px">
        <h3 style="margin:0">📥 Export & Paylaşım Merkezi</h3>
        <p style="margin:6px 0 0;opacity:0.85">Tüm analizleri indir, ChatGPT/Claude'a gönder, profil rehberi al.</p>
        </div>""", unsafe_allow_html=True)

    profile = data.get("profile", {})
    enriched = data.get("enriched", [])
    keywords = data.get("keywords", [])
    kw_fit = data.get("kw_fit", [])

    # 1. Full Report
    st.markdown("### 📋 Tam Analiz Raporu")
    st.caption("Profil + tüm iş analizleri + keyword verileri – ChatGPT'ye yapıştırılmaya hazır")
    full_report = build_export_text(profile, enriched, keywords, kw_fit)
    st.download_button(
        "📥 Tam Rapor İndir (.txt)",
        data=full_report,
        file_name=f"upwork_dna_full_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
        mime="text/plain",
        type="primary",
        key="exp_full",
    )
    st.markdown("""
    **ChatGPT'ye yapıştırdıktan sonra sorabilecekleriniz:**
    - "Bu profil için hangi işlere başvurmalıyım? Neden?"
    - "Profilimi nasıl geliştirebilirim?"
    - "Bu iş için bir proposal yaz"
    - "Hangi keyword'leri ekleyip çıkarmalıyım?"
    - "Rate'imi yükseltmek için ne yapmalıyım?"
    """)

    st.divider()

    # 2. Jobs only (CSV)
    st.markdown("### 💼 İş Verileri")
    if enriched:
        jobs_df = pd.DataFrame(enriched)
        # Parse reasons for export
        jobs_df["_r"] = jobs_df["reasons"].apply(reasons)
        jobs_df["ai_action"] = jobs_df["_r"].apply(lambda d: d.get("llm_action", ""))
        jobs_df["ai_summary"] = jobs_df["_r"].apply(lambda d: d.get("llm_summary", ""))
        jobs_df["ai_reasoning"] = jobs_df["_r"].apply(lambda d: d.get("llm_reasoning", ""))
        jobs_df["composite_score"] = jobs_df["_r"].apply(lambda d: d.get("composite_score", 0))
        export_cols = ["title", "url", "keyword", "budget", "proposals", "payment_verified",
                       "skills", "fit_score", "safety_score", "opportunity_score",
                       "ai_action", "ai_summary", "ai_reasoning", "composite_score", "description"]
        export_df = jobs_df[[c for c in export_cols if c in jobs_df.columns]]
        csv = export_df.to_csv(index=False)
        st.download_button("📥 İş Verileri İndir (CSV)", data=csv, file_name="upwork_jobs.csv", mime="text/csv", key="exp_jobs")
        st.caption(f"{len(enriched)} iş kaydı")

    st.divider()

    # 3. Profile summary
    st.markdown("### 👤 Profil Özeti")
    if profile.get("name"):
        profile_text = json.dumps(profile, indent=2, ensure_ascii=False)
        st.download_button("📥 Profil JSON İndir", data=profile_text, file_name="upwork_profile.json", mime="application/json", key="exp_profile")

    st.divider()

    # 4. Keyword fit
    st.markdown("### 🔑 Keyword Uyum Raporu")
    if kw_fit:
        kw_text = json.dumps(kw_fit, indent=2, ensure_ascii=False)
        st.download_button("📥 Keyword Fit İndir (JSON)", data=kw_text, file_name="keyword_fit.json", mime="application/json", key="exp_kwfit")

    st.divider()

    # 5. ChatGPT prompt helper
    st.markdown("### 🤖 ChatGPT Hazır Promptlar")
    prompts = [
        ("Profil İyileştirme", "Aşağıda Upwork profilim ve pazar analiz verileri var. Bu verilere göre:\n1. Profilimi nasıl güçlendirebilirim?\n2. Title ve overview'umu nasıl değiştirmeliyim?\n3. Hangi skills'i öne çıkarmalıyım?\n4. Rate stratejim ne olmalı?\n\n[RAPORU BURAYA YAPIŞTIR]"),
        ("İş Seçme Danışmanlığı", "Aşağıda Upwork iş analizleri var. Profilime en uygun 5 işi seç ve her biri için:\n1. Neden bu işe başvurmalıyım?\n2. Proposal'da ne vurgulamalıyım?\n3. Teklif fiyatım ne olmalı?\n\n[RAPORU BURAYA YAPIŞTIR]"),
        ("Keyword Stratejisi", "Aşağıda keyword performans verileri ve profil uyum skorları var. Bana:\n1. Hangi keyword'leri bırakmalıyım?\n2. Hangi yeni keyword'ler eklemeliyim?\n3. Niche stratejim ne olmalı?\n\n[RAPORU BURAYA YAPIŞTIR]"),
        ("Proposal Yazımı", "Aşağıda bir Upwork iş ilanı ve profilim var. Bu iş için:\n1. Dikkat çekici bir opening yaz\n2. Teknik yetkinliğimi göster\n3. Portfolio'mdan ilgili projeleri referans ver\n4. Teklif gerekçesi ve timeline ver\n\n[RAPORU BURAYA YAPIŞTIR]"),
    ]
    for title, prompt in prompts:
        with st.expander(f"💡 {title}"):
            st.code(prompt, language=None)
            st.download_button(f"📥 {title} Prompt İndir", data=prompt, file_name=f"chatgpt_{title.lower().replace(' ', '_')}.txt", mime="text/plain", key=f"exp_prompt_{title}")


# ═══════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════

def sidebar(data):
    profile = data.get("profile", {})
    llm = data["llm"]
    summary = data["summary"]

    # Profile badge
    if profile.get("name"):
        st.sidebar.markdown(
            f"""<div style="background:#1e40af;color:white;padding:10px 12px;border-radius:8px;margin-bottom:8px;font-size:0.85rem">
            👤 <strong>{profile['name']}</strong><br/>
            💰 {profile.get('hourly_range', '')} | 📋 {profile.get('total_upwork_jobs', 0)} iş
            </div>""", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("🧬 **Upwork DNA**")

    # LLM Status
    st.sidebar.markdown("---")
    ok = llm.get("status") in ("healthy", "degraded")
    if ok:
        st.sidebar.success(f"🤖 LLM: {llm.get('model', '?')[:30]}")
    else:
        st.sidebar.error(f"🤖 LLM Offline: {llm.get('error', '')[:40]}")

    st.sidebar.caption(f"API: {API}")
    st.sidebar.caption(f"Son ingest: {summary.get('last_ingest_at', 'n/a')}")

    # Quick actions
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 Hızlı İşlemler")

    if st.sidebar.button("📥 Ingest & Tara", key="s_ingest"):
        with st.spinner("Taranıyor…"):
            post("/v1/ingest/scan")
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("🤖 LLM Analiz (10)", key="s_llm"):
        with st.spinner("AI analiz…"):
            r = post("/v1/llm/batch-analyze?limit=10&unanalyzed_only=true")
            if isinstance(r, dict) and r.get("analyzed", 0) == 0 and r.get("total", 0) == 0:
                r = post("/v1/llm/batch-analyze?limit=10&unanalyzed_only=false")
            if r and not r.get("error"):
                st.sidebar.success(f"✅ {r.get('analyzed', 0)} analiz")
            else:
                st.sidebar.error(f"❌ {r.get('error', 'analiz yapılamadı') if isinstance(r, dict) else 'analiz yapılamadı'}")
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("🎯 Decision Engine", key="s_dec"):
        with st.spinner("Karar motoru…"):
            r = post("/v1/llm/decide?limit=20")
            if r and not r.get("error"):
                st.sidebar.success(f"🔥 {r.get('hot_count', 0)} HOT")
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("🔄 Yenile", key="s_ref"):
        st.cache_data.clear()
        st.rerun()

    # Export shortcut
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Quick Export")
    export = build_export_text(
        data.get("profile", {}), data.get("enriched", []),
        data.get("keywords", []), data.get("kw_fit", [])
    )
    st.sidebar.download_button(
        "📥 Full Report İndir",
        data=export,
        file_name=f"upwork_report_{datetime.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
        key="s_export",
    )

    # Auto refresh
    st.sidebar.markdown("---")
    auto = st.sidebar.checkbox("⏰ Oto Yenile", key="s_auto")
    if auto:
        iv = st.sidebar.slider("Aralık (sn)", 30, 600, 120, key="s_iv")
        from streamlit.components.v1 import html
        html(f"<script>setTimeout(()=>window.parent.location.reload(),{iv*1000})</script>", height=0)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="Upwork DNA v5", page_icon="🧬", layout="wide", initial_sidebar_state="expanded")

    st.markdown("""<style>
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 14px; border-radius: 8px 8px 0 0; font-weight: 600; }
    div[data-testid="stMetric"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
    </style>""", unsafe_allow_html=True)

    # Header
    st.markdown(
        """<div style="background:linear-gradient(135deg,#1a7a3a,#0d4020);padding:18px;border-radius:12px;color:white;margin-bottom:12px">
        <h1 style="margin:0;font-size:1.7rem">🧬 Upwork DNA v5 – AI Career Intelligence</h1>
        <p style="margin:4px 0 0;opacity:0.85">Scrape → Analiz → Karar → Proposal → Başvur (Profil odaklı)</p>
        </div>""", unsafe_allow_html=True)

    data = load()
    sidebar(data)

    # Top metrics
    s = data["summary"]
    llm = data["llm"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Jobs", f"{int(s.get('jobs_raw', 0)):,}")
    c2.metric("💼 Opportunities", f"{int(s.get('opportunities', 0)):,}")
    c3.metric("🔑 Keywords", int(s.get("keywords", 0)))
    c4.metric("🤖 LLM", "Online" if llm.get("status") in ("healthy", "degraded") else "Offline")
    notifs = data["notifs"]
    c5.metric("🔥 HOT", sum(1 for n in notifs if n.get("priority") == "HOT"))

    st.divider()

    tabs = st.tabs([
        "🎯 Başvuru Kararları",
        "📋 Tüm İşler",
        "📝 Proposal",
        "👤 Profil",
        "🧠 Keyword Strateji",
        "📊 Pazar Verileri",
        "📥 Export",
    ])

    with tabs[0]: tab_decisions(data)
    with tabs[1]: tab_jobs(data)
    with tabs[2]: tab_proposal(data)
    with tabs[3]: tab_profile(data)
    with tabs[4]: tab_keyword_strategy(data)
    with tabs[5]: tab_market(data)
    with tabs[6]: tab_export(data)


if __name__ == "__main__":
    main()

