import json
import os
from typing import List, Dict, Any

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "visuals")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "analysis_report.json")


def load_report(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "figure.dpi": 120,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })


def plot_jobs_top_skills(report: Dict[str, Any]) -> None:
    skills = report.get("jobs_analysis", {}).get("top_skills", [])[:15]
    if not skills:
        return
    df = pd.DataFrame(skills, columns=["skill", "count"]).sort_values("count")
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="count", y="skill", palette="Blues_r")
    plt.title("En Çok Aranan 15 Skill (İş İlanları)")
    plt.xlabel("İlan Sayısı")
    plt.ylabel("Skill")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "jobs_top_skills.png"))
    plt.close()


def plot_jobs_title_bigrams(report: Dict[str, Any]) -> None:
    ngrams = report.get("jobs_analysis", {}).get("title_ngrams", [])[:15]
    if not ngrams:
        return
    df = pd.DataFrame(ngrams)
    df = df.sort_values("Frequency")
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="Frequency", y="Phrase", palette="Greens_r")
    plt.title("Başlıklarda En Sık Geçen Bigrams")
    plt.xlabel("Frekans")
    plt.ylabel("Bigram")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "jobs_title_bigrams.png"))
    plt.close()


def plot_talent_top_skills(report: Dict[str, Any]) -> None:
    skills = report.get("talent_analysis", {}).get("top_skills", [])[:15]
    if not skills:
        return
    df = pd.DataFrame(skills, columns=["skill", "count"]).sort_values("count")
    plt.figure(figsize=(8, 5))
    sns.barplot(data=df, x="count", y="skill", palette="Purples_r")
    plt.title("Elite Freelancer'larda En Yaygın 15 Skill")
    plt.xlabel("Freelancer Sayısı")
    plt.ylabel("Skill")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "talent_top_skills.png"))
    plt.close()


def plot_talent_rate_summary(report: Dict[str, Any]) -> None:
    rate_stats = report.get("talent_analysis", {}).get("rate_distribution", {})
    if not rate_stats:
        return
    df = pd.DataFrame([
        {"metric": "Min", "value": rate_stats.get("min", 0)},
        {"metric": "Median", "value": rate_stats.get("median", 0)},
        {"metric": "Mean", "value": rate_stats.get("mean", 0)},
        {"metric": "Max", "value": rate_stats.get("max", 0)},
    ])
    plt.figure(figsize=(6, 4))
    sns.barplot(data=df, x="metric", y="value", palette="Oranges")
    plt.title("Freelancer Saatlik Ücret Özeti")
    plt.xlabel("Metri̇k")
    plt.ylabel("$/hr")
    for idx, row in df.iterrows():
        plt.text(idx, row["value"] + (row["value"] * 0.01), f"{row['value']:.1f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "talent_rate_summary.png"))
    plt.close()


def plot_projects_delivery(report: Dict[str, Any]) -> None:
    deliveries = report.get("projects_analysis", {}).get("delivery_patterns", {})
    if not deliveries:
        return
    df = pd.DataFrame(list(deliveries.items()), columns=["delivery", "count"]).sort_values("count")
    plt.figure(figsize=(7, 5))
    sns.barplot(data=df, x="count", y="delivery", palette="coolwarm")
    plt.title("Project Catalog Teslimat Süreleri")
    plt.xlabel("Proje Sayısı")
    plt.ylabel("Süre")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "projects_delivery.png"))
    plt.close()


def plot_market_gaps(report: Dict[str, Any]) -> None:
    gaps: List[Dict[str, Any]] = report.get("market_gaps", [])[:20]
    if not gaps:
        return
    df = pd.DataFrame(gaps)
    df = df.sort_values("gap_ratio", ascending=False)
    plt.figure(figsize=(8, 6))
    sns.barplot(data=df, x="gap_ratio", y="skill", palette="rocket")
    plt.title("Market Gap (Talep/Arz Oranı) — İlk 20")
    plt.xlabel("Gap Ratio (Talep / Arz)")
    plt.ylabel("Skill")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "market_gaps.png"))
    plt.close()


def plot_jobs_budget_mix(report: Dict[str, Any]) -> None:
    budget = report.get("jobs_analysis", {}).get("budget_stats", {})
    if not budget:
        return
    df = pd.DataFrame([
        {"type": "Fixed", "count": budget.get("fixed_count", 0)},
        {"type": "Hourly", "count": budget.get("hourly_count", 0)},
    ])
    plt.figure(figsize=(5, 4))
    sns.barplot(data=df, x="type", y="count", palette="pastel")
    plt.title("İş Modeli Dağılımı")
    plt.xlabel("Tür")
    plt.ylabel("İş Sayısı")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "jobs_budget_mix.png"))
    plt.close()


def main() -> None:
    style()
    ensure_output_dir()
    report = load_report(REPORT_PATH)

    plot_jobs_top_skills(report)
    plot_jobs_title_bigrams(report)
    plot_jobs_budget_mix(report)
    plot_talent_top_skills(report)
    plot_talent_rate_summary(report)
    plot_projects_delivery(report)
    plot_market_gaps(report)

    print(f"Görseller kaydedildi: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
