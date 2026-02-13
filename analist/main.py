import json
import pandas as pd
import re
import glob
import os
from collections import Counter
import nltk
from nltk.util import ngrams
from sklearn.feature_extraction.text import TfidfVectorizer

# Import scoring module
from scoring.segment_scorer import SegmentScorer

DATA_DIR = 'data'
OUTPUT_PATH = 'outputs/extreme_market_intelligence_blueprint.md'

def load_all_data():
    """Aggregates all CSV/JSON files, tagging them by niche (SQL vs. General)."""
    files = glob.glob(os.path.join(DATA_DIR, 'upwork_*.csv'))
    
    jobs_dfs, talent_dfs, project_dfs = [], [], []
    
    for f in files:
        niche = 'SQL' if 'sql' in f.lower() else 'General'
        try:
            df = pd.read_csv(f)
            df['niche'] = niche
            if 'jobs' in f: jobs_dfs.append(df)
            elif 'talent' in f: talent_dfs.append(df)
            elif 'projects' in f: project_dfs.append(df)
        except: continue

    jobs = pd.concat(jobs_dfs, ignore_index=True).drop_duplicates() if jobs_dfs else pd.DataFrame()
    talent = pd.concat(talent_dfs, ignore_index=True).drop_duplicates() if talent_dfs else pd.DataFrame()
    projects = pd.concat(project_dfs, ignore_index=True).drop_duplicates() if project_dfs else pd.DataFrame()
    
    return jobs, talent, projects

def clean_salary(val):
    if not isinstance(val, str): return 0
    nums = re.findall(r'[\d,.]+', val.replace('$', '').replace(',', ''))
    if nums:
        vals = [float(n) for n in nums if n.replace('.', '', 1).isdigit()]
        return sum(vals) / len(vals) if vals else 0
    return 0

def extract_features_tfidf(text_series, max_features=20):
    """Uses TF-IDF to find the most 'unique' and 'important' terms in a dataset."""
    if text_series.dropna().empty: return []
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 3), max_features=max_features)
    X = vectorizer.fit_transform(text_series.dropna())
    # Sum TF-IDF scores for each term
    scores = zip(vectorizer.get_feature_names_out(), X.toarray().sum(axis=0))
    return sorted(scores, key=lambda x: x[1], reverse=True)

def analyze_extreme(jobs, talent, projects):
    print("Executing Extreme Comparative Analysis...")
    
    # 1. Niche Benchmarking (SQL vs General)
    talent['rate_num'] = talent['rate'].apply(clean_salary)
    niche_bench = talent.groupby('niche')['rate_num'].mean().to_dict()
    
    # 2. SQL Niche "Micro-Specializations" (TF-IDF on SQL Titles)
    sql_titles = talent[talent['niche'] == 'SQL']['title']
    sql_specializations = extract_features_tfidf(sql_titles, 15)
    
    # 3. High-Value Deliverable Extraction (Projects)
    projects['price_num'] = projects['price'].apply(clean_salary)
    elite_projects = projects[(projects['price_num'] >= 100) & (projects['rating'].apply(lambda x: float(str(x).replace('n/a', '0'))) >= 4.8)]
    # Analyze 'detail_project_description' or 'title'
    project_features = extract_features_tfidf(elite_projects['title'], 15)
    
    # 4. Job Marker Analysis (Budgets by Niche)
    jobs['budget_num'] = jobs['budget'].apply(clean_salary)
    job_niche_bench = jobs.groupby('niche')['budget_num'].mean().to_dict()
    
    # 5. Requirement NLP (What do clients ASK for in SQL jobs?)
    sql_job_raw = jobs[jobs['niche'] == 'SQL']['description']
    if sql_job_raw.empty: sql_job_raw = jobs[jobs['niche'] == 'SQL']['title'] # Fallback
    requirements = extract_features_tfidf(sql_job_raw, 10)

    return {
        'niche_bench': niche_bench,
        'sql_specializations': sql_specializations,
        'project_features': project_features,
        'job_niche_bench': job_niche_bench,
        'requirements': requirements
    }

def generate_extreme_report(results):
    os.makedirs('outputs', exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        f.write("# Extreme Market Intelligence: SQL vs. General Data Analyst\n\n")

        f.write("## 🏗️ 1. Niche Benchmark (Rate Comparison)\n")
        f.write("| Niche | Avg Talent Rate | Avg Job Budget |\n| :--- | :--- | :--- |\n")
        for niche in results['niche_bench'].keys():
            t_rate = results['niche_bench'].get(niche, 0)
            j_budget = results['job_niche_bench'].get(niche, 0)
            f.write(f"| {niche} | ${t_rate:.2f}/hr | ${j_budget:.2f} |\n")

        f.write("\n## 💎 2. SQL 'Micro-Specialization' Opportunities\n")
        f.write("These terms are uniquely powerful in the newest SQL datasets:\n")
        for term, score in results['sql_specializations']:
            f.write(f"- **{term.title()}** (Rel. Importance: {score:.2f})\n")

        f.write("\n## 🛠️ 3. High-Ticket 'Feature Factory'\n")
        f.write("Common features found in $100+ high-rated project catalogs:\n")
        for term, score in results['project_features']:
            f.write(f"- `{term.title()}`\n")

        f.write("\n## 📝 4. Client Requirement Matrix (Proposal Hook Ideas)\n")
        f.write("High-value clients in the SQL niche are actively mentioning these pain points:\n")
        for term, score in results['requirements']:
            f.write(f"- *'I noticed you mentioned **{term}** in the requirements...'* (Term Weight: {score:.2f})\n")

def demonstrate_segment_scoring(jobs, talent):
    """Demonstrate the SegmentScorer functionality."""
    print("\n" + "="*60)
    print("DEMONSTRATING SEGMENT SCORING (P0.2)")
    print("="*60)

    scorer = SegmentScorer()

    # Score a sample job
    if not jobs.empty:
        print("\n--- Sample Job Scoring ---")
        sample_job = jobs.iloc[0].to_dict()
        job_result = scorer.score_job(sample_job, niche='General')
        print(f"Job: {sample_job.get('title', 'N/A')[:60]}...")
        print(f"Composite Score: {job_result['composite_score']}/100")
        for factor, data in job_result['factors'].items():
            print(f"  {factor}: {data['score']:.1f}/100")

    # Score a sample talent
    if not talent.empty:
        print("\n--- Sample Talent Scoring ---")
        sample_talent = talent.iloc[0].to_dict()
        talent_result = scorer.score_talent(sample_talent, niche='General')
        print(f"Talent: {sample_talent.get('name', sample_talent.get('title', 'N/A'))}")
        print(f"Composite Score: {talent_result['composite_score']}/100")
        for factor, data in talent_result['factors'].items():
            print(f"  {factor}: {data['score']:.1f}/100")

def main():
    jobs, talent, projects = load_all_data()
    print(f"Loaded {len(jobs)} jobs, {len(talent)} talent, {len(projects)} projects.")

    results = analyze_extreme(jobs, talent, projects)
    generate_extreme_report(results)
    print(f"Extreme report generated at {OUTPUT_PATH}")

    # Demonstrate SegmentScorer
    if not jobs.empty or not talent.empty:
        demonstrate_segment_scoring(jobs, talent)

if __name__ == "__main__":
    main()
