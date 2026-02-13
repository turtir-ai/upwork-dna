import glob
import os
import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

DATA_DIR = "data"
OUTPUT_PATH = "outputs/profile_blueprint.md"

SEPARATORS = ["|", "/", "-", "–", "—", ":", "•"]

SKILL_SYNONYMS = {
    "power bi": "Power BI",
    "microsoft power bi": "Power BI",
    "power bi developer": "Power BI",
    "google data studio": "Looker Studio",
    "looker studio": "Looker Studio",
    "ms excel": "Microsoft Excel",
    "excel": "Microsoft Excel",
    "microsoft excel": "Microsoft Excel",
    "ms sql server": "SQL Server",
    "sql server": "SQL Server",
    "postgresql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "bigquery": "BigQuery",
    "google bigquery": "BigQuery",
    "data analytics": "Data Analysis",
    "data analysis": "Data Analysis",
    "data visualization": "Data Visualization",
    "etl": "ETL",
    "elt": "ELT",
    "dbt": "dbt",
    "airflow": "Airflow",
    "python": "Python",
    "pandas": "Pandas",
    "sql": "SQL",
    "tableau": "Tableau",
    "looker": "Looker",
    "google analytics": "Google Analytics",
    "ga4": "Google Analytics",
    "dashboards": "Dashboard",
    "dashboard": "Dashboard",
    "reporting": "Reporting",
    "data modeling": "Data Modeling",
}


def extract_numbers(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    text = str(value)
    nums = re.findall(r"[\d,.]+", text)
    out = []
    for n in nums:
        n = n.replace(",", "")
        try:
            out.append(float(n))
        except ValueError:
            continue
    return out


def parse_money(value):
    nums = extract_numbers(value)
    if not nums:
        return 0.0
    return float(np.mean(nums))


def parse_hourly_range(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return (None, None)
    text = str(value).lower()
    if "hour" not in text:
        return (None, None)
    nums = extract_numbers(text)
    if not nums:
        return (None, None)
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))


def parse_rate(value):
    nums = extract_numbers(value)
    return nums[0] if nums else 0.0


def parse_job_success(value):
    nums = extract_numbers(value)
    if not nums:
        return None
    return int(nums[0])


def normalize_skill(skill):
    if not isinstance(skill, str):
        return None
    raw = skill.strip()
    if not raw:
        return None
    key = re.sub(r"\s+", " ", raw.lower().strip())
    if key in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[key]
    if key in {"sql", "etl", "elt", "bi"}:
        return key.upper()
    if raw.isupper():
        return raw
    return raw


def split_skills(series):
    skills = []
    for value in series.dropna().astype(str):
        parts = [p.strip() for p in re.split(r"[;|,]", value) if p.strip()]
        for part in parts:
            norm = normalize_skill(part)
            if norm:
                skills.append(norm)
    return skills


def top_skills(df, cols, top_n=15):
    skills = []
    for col in cols:
        if col in df.columns:
            skills.extend(split_skills(df[col]))
    if not skills:
        return []
    counts = Counter(skills)
    total = sum(counts.values())
    return [(k, v, v / total) for k, v in counts.most_common(top_n)]


def top_ngrams(series, n=2, top_n=15):
    series = series.dropna().astype(str)
    if series.empty:
        return []
    vectorizer = CountVectorizer(stop_words="english", ngram_range=(n, n), min_df=2)
    X = vectorizer.fit_transform(series)
    freqs = X.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    pairs = list(zip(terms, freqs))
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:top_n]


def title_separators(titles):
    counts = Counter()
    for title in titles.dropna().astype(str):
        for sep in SEPARATORS:
            if sep in title:
                counts[sep] += 1
    return counts


def title_components(titles):
    components = []
    for title in titles.dropna().astype(str):
        sep_used = None
        for sep in SEPARATORS:
            if sep in title:
                sep_used = sep
                break
        if not sep_used:
            continue
        parts = [p.strip() for p in title.split(sep_used) if p.strip()]
        if len(parts) <= 1:
            continue
        components.extend(parts[1:])
    comp_skills = []
    for comp in components:
        for part in re.split(r"[;|,]", comp):
            norm = normalize_skill(part.strip())
            if norm:
                comp_skills.append(norm)
    return Counter(comp_skills)


def load_all_csvs():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    sql_files = [f for f in files if "sql_data_analyst" in os.path.basename(f).lower()]
    non_sql_files = [f for f in files if f not in sql_files]
    ordered = non_sql_files + sql_files

    jobs, talent, projects = [], [], []
    file_rows = []

    for path in ordered:
        df = pd.read_csv(path)
        base = os.path.basename(path)
        niche = "SQL" if "sql" in base.lower() else "General"
        df["niche"] = niche
        df["source_file"] = base
        file_rows.append((base, df.shape[0], df.shape[1], niche))
        if "jobs_" in base:
            jobs.append(df)
        elif "talent_" in base:
            talent.append(df)
        elif "projects_" in base:
            projects.append(df)

    jobs_df = pd.concat(jobs, ignore_index=True) if jobs else pd.DataFrame()
    talent_df = pd.concat(talent, ignore_index=True) if talent else pd.DataFrame()
    projects_df = pd.concat(projects, ignore_index=True) if projects else pd.DataFrame()
    return file_rows, jobs_df, talent_df, projects_df


def prep_jobs(df):
    if df.empty:
        return df
    if "payment_verified" in df.columns:
        df["payment_verified_bool"] = df["payment_verified"].astype(str).str.lower().eq("true")
    else:
        df["payment_verified_bool"] = False

    hourly_mins = []
    hourly_maxs = []
    for val in df.get("budget", pd.Series(dtype=object)):
        mn, mx = parse_hourly_range(val)
        hourly_mins.append(mn)
        hourly_maxs.append(mx)
    df["hourly_min"] = hourly_mins
    df["hourly_max"] = hourly_maxs

    fixed = []
    for _, row in df.iterrows():
        val = None
        if "fixed_budget" in df.columns and pd.notna(row.get("fixed_budget")):
            val = parse_money(row.get("fixed_budget"))
        else:
            budget = row.get("budget")
            if isinstance(budget, str) and "hour" not in budget.lower():
                val = parse_money(budget)
        fixed.append(val or 0.0)
    df["fixed_budget_num"] = fixed

    df["is_high_value"] = df["payment_verified_bool"] & (
        (df["fixed_budget_num"] >= 500) | (df["hourly_max"] >= 30)
    )
    return df


def prep_talent(df):
    if df.empty:
        return df
    df["rate_num"] = df.get("rate", pd.Series(dtype=object)).apply(parse_rate)
    if "detail_job_success" in df.columns:
        df["job_success_num"] = df["detail_job_success"].apply(parse_job_success)
    else:
        df["job_success_num"] = None
    badges = df.get("detail_badges", pd.Series("", index=df.index)).astype(str)
    df["badge_top"] = badges.str.contains("Top Rated", case=False, na=False) | badges.str.contains(
        "Expert", case=False, na=False
    )
    df["is_elite"] = df["badge_top"] | (df["job_success_num"].fillna(0) >= 95) | (
        df["rate_num"] >= 60
    )
    return df


def prep_projects(df):
    if df.empty:
        return df
    df["price_num"] = df.get("price", pd.Series(dtype=object)).apply(parse_money)
    rating_series = df.get("rating", pd.Series(dtype=object)).fillna(
        df.get("detail_project_rating", pd.Series(dtype=object))
    )
    df["rating_num"] = rating_series.apply(parse_money)
    reviews_series = df.get("reviews", pd.Series(dtype=object)).fillna(
        df.get("detail_project_reviews", pd.Series(dtype=object))
    )
    df["reviews_num"] = reviews_series.apply(parse_money)

    if df["price_num"].notna().any():
        price_decile = np.nanpercentile(df["price_num"], 90)
    else:
        price_decile = 0
    df["is_top_catalog"] = ((df["rating_num"] >= 4.8) & (df["reviews_num"] >= 10)) | (
        df["price_num"] >= price_decile
    )
    return df


def demand_supply_gap(job_skills, talent_skills, top_n=15):
    job_counts = Counter(job_skills)
    talent_counts = Counter(talent_skills)
    job_total = sum(job_counts.values()) or 1
    talent_total = sum(talent_counts.values()) or 1

    gaps = []
    for skill, j_count in job_counts.items():
        j_rate = j_count / job_total
        t_rate = talent_counts.get(skill, 0) / talent_total
        gaps.append((skill, j_rate - t_rate, j_rate, t_rate))
    gaps.sort(key=lambda x: x[1], reverse=True)
    return gaps[:top_n]


def summarize_segment(jobs, talent, projects):
    out = {}
    jobs = prep_jobs(jobs.copy()) if not jobs.empty else jobs
    high_value = jobs[jobs["is_high_value"]] if not jobs.empty else jobs

    out["jobs_count"] = len(jobs)
    out["jobs_high_value_count"] = len(high_value)
    out["jobs_top_skills"] = top_skills(high_value if len(high_value) else jobs, ["skills", "detail_mandatory_skills"])
    out["jobs_top_title_bigrams"] = top_ngrams((high_value["title"] if len(high_value) else jobs.get("title", pd.Series(dtype=object))), n=2)
    out["jobs_top_desc_trigrams"] = top_ngrams((high_value["description"] if len(high_value) else jobs.get("description", pd.Series(dtype=object))), n=3)

    talent = prep_talent(talent.copy()) if not talent.empty else talent
    elite = talent[talent["is_elite"]] if not talent.empty else talent

    out["talent_count"] = len(talent)
    out["talent_elite_count"] = len(elite)
    out["talent_top_skills"] = top_skills(elite if len(elite) else talent, ["skills", "detail_skills"])
    out["talent_title_bigrams"] = top_ngrams((elite["title"] if len(elite) else talent.get("title", pd.Series(dtype=object))), n=2)
    out["talent_separators"] = title_separators(elite["title"] if len(elite) else talent.get("title", pd.Series(dtype=object)))
    out["talent_title_components"] = title_components(elite["title"] if len(elite) else talent.get("title", pd.Series(dtype=object)))

    projects = prep_projects(projects.copy()) if not projects.empty else projects
    top_catalog = projects[projects["is_top_catalog"]] if not projects.empty else projects

    out["projects_count"] = len(projects)
    out["projects_top_count"] = len(top_catalog)
    out["projects_top_titles"] = top_ngrams((top_catalog["title"] if len(top_catalog) else projects.get("title", pd.Series(dtype=object))), n=2)
    out["projects_top_desc"] = top_ngrams((top_catalog.get("detail_project_description", pd.Series(dtype=object)) if len(top_catalog) else projects.get("detail_project_description", pd.Series(dtype=object))), n=2)
    out["projects_top_categories"] = Counter(top_catalog.get("detail_project_category", pd.Series(dtype=object)).dropna().astype(str)) if not projects.empty else Counter()
    out["projects_price_stats"] = {
        "median": float(np.nanmedian(top_catalog["price_num"])) if len(top_catalog) else 0,
        "p75": float(np.nanpercentile(top_catalog["price_num"], 75)) if len(top_catalog) else 0,
        "p90": float(np.nanpercentile(top_catalog["price_num"], 90)) if len(top_catalog) else 0,
    }

    job_skills = split_skills((high_value if len(high_value) else jobs).get("skills", pd.Series(dtype=object)))
    talent_skills = split_skills((elite if len(elite) else talent).get("skills", pd.Series(dtype=object)))
    out["gap_skills"] = demand_supply_gap(job_skills, talent_skills, top_n=12)
    return out


def fmt_list(items, n=10):
    lines = []
    for i, item in enumerate(items[:n], 1):
        if len(item) == 3:
            key, value, rate = item
            lines.append(f"{i}. {key} ({value}, {rate*100:.1f}%)")
        elif len(item) == 2:
            key, value = item
            lines.append(f"{i}. {key} ({value})")
        else:
            lines.append(str(item))
    return lines


def fmt_ngrams(items, n=10):
    return [f"{i}. {term} ({count})" for i, (term, count) in enumerate(items[:n], 1)]


def write_segment(handle, title, seg):
    handle.write(f"## {title}\n")
    handle.write(f"- Jobs: {seg['jobs_count']} (High-value: {seg['jobs_high_value_count']})\n")
    handle.write(f"- Talent: {seg['talent_count']} (Elite: {seg['talent_elite_count']})\n")
    handle.write(f"- Projects: {seg['projects_count']} (Top catalog: {seg['projects_top_count']})\n\n")

    handle.write("### Jobs: Top Skills (high-value)\n")
    for line in fmt_list(seg["jobs_top_skills"], 12):
        handle.write(f"- {line}\n")
    handle.write("\n### Jobs: Top Title Bigrams\n")
    for line in fmt_ngrams(seg["jobs_top_title_bigrams"], 10):
        handle.write(f"- {line}\n")
    handle.write("\n### Jobs: Top Description Trigrams\n")
    for line in fmt_ngrams(seg["jobs_top_desc_trigrams"], 10):
        handle.write(f"- {line}\n")

    handle.write("\n### Talent (Elite): Top Skills\n")
    for line in fmt_list(seg["talent_top_skills"], 12):
        handle.write(f"- {line}\n")
    handle.write("\n### Talent (Elite): Title Bigrams\n")
    for line in fmt_ngrams(seg["talent_title_bigrams"], 10):
        handle.write(f"- {line}\n")

    sep_counts = seg["talent_separators"]
    if sep_counts:
        handle.write("\n### Talent Title Separators\n")
        for sep, count in sep_counts.most_common():
            handle.write(f"- '{sep}': {count}\n")

    comp_counts = seg["talent_title_components"]
    if comp_counts:
        handle.write("\n### Talent Title Components (after separator)\n")
        for skill, count in comp_counts.most_common(10):
            handle.write(f"- {skill}: {count}\n")

    handle.write("\n### Projects: Top Title Bigrams\n")
    for line in fmt_ngrams(seg["projects_top_titles"], 10):
        handle.write(f"- {line}\n")
    handle.write("\n### Projects: Top Description Bigrams\n")
    for line in fmt_ngrams(seg["projects_top_desc"], 10):
        handle.write(f"- {line}\n")

    if seg["projects_top_categories"]:
        handle.write("\n### Projects: Top Categories\n")
        for cat, count in seg["projects_top_categories"].most_common(10):
            handle.write(f"- {cat}: {count}\n")

    handle.write("\n### Market Gap (Demand > Supply)\n")
    for skill, gap, j_rate, t_rate in seg["gap_skills"]:
        handle.write(
            f"- {skill}: +{gap*100:.1f}pp (demand {j_rate*100:.1f}%, supply {t_rate*100:.1f}%)\n"
        )

    handle.write("\n### Project Price Stats (Top Catalog)\n")
    stats = seg["projects_price_stats"]
    handle.write(f"- Median: ${stats['median']:.0f}\n- P75: ${stats['p75']:.0f}\n- P90: ${stats['p90']:.0f}\n\n")


def main():
    file_rows, jobs_df, talent_df, projects_df = load_all_csvs()

    overall = summarize_segment(jobs_df, talent_df, projects_df)
    general = summarize_segment(
        jobs_df[jobs_df["niche"] != "SQL"],
        talent_df[talent_df["niche"] != "SQL"],
        projects_df[projects_df["niche"] != "SQL"],
    )
    sql = summarize_segment(
        jobs_df[jobs_df["niche"] == "SQL"],
        talent_df[talent_df["niche"] == "SQL"],
        projects_df[projects_df["niche"] == "SQL"],
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as handle:
        handle.write("# Profile Optimization Blueprint (Data-Driven)\n\n")
        handle.write("## Data Coverage (read all CSVs; SQL Data Analyst files processed last)\n")
        for base, rows, cols, niche in file_rows:
            handle.write(f"- {base} — {rows} rows, {cols} cols ({niche})\n")
        handle.write("\n# General + Data Visualization (Combined)\n")
        write_segment(handle, "Combined (Non-SQL)", general)
        handle.write("# SQL Data Analyst (Processed Last)\n")
        write_segment(handle, "SQL Data Analyst", sql)

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
