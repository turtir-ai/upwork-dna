#!/usr/bin/env python3
"""
Upwork DNA - NLP Keyword Generator
Analyzes scraped data and generates new high-value keywords
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter
import pandas as pd

# Paths
DATA_DIR = Path("/Users/dev/Documents/upworkextension/analist/data/dataanalist")
RECOMMENDED_OUTPUT = DATA_DIR / "recommended_keywords.json"
QUEUE_FILE = Path.home() / "Downloads" / "upwork_dna" / "recommended_keywords.json"

# High-value skill/technology patterns
TECH_PATTERNS = [
    r'AI\s+\w+', r'machine\s+learning', r'deep\s+learning', r'LLM', r'GPT',
    r'ChatGPT', r'Python', r'JavaScript', r'TypeScript', r'React', r'Node\.js',
    r'API\s+\w+', r'web\s+scraping', r'automation', r'workflow', r'data\s+\w+',
    r'Cloudflare', r'AWS', r'Azure', r'GCP', r'Docker', r'Kubernetes',
    r'SQL', r'NoSQL', r'MongoDB', r'PostgreSQL', r'MySQL',
    r'Flutter', r'Mobile', r'iOS', r'Android', r'Chrome\s+extension'
]

# Job title patterns
JOB_PATTERNS = [
    r'developer', r'engineer', r'specialist', r'expert', r'consultant',
    r'architect', r'analyst', r'researcher', r'manager', r'lead'
]

class NLPKeywordGenerator:
    """Analyze scraped data and generate high-value keywords"""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.keywords_data = []
        self.jobs_df = None
        self.talent_df = None
        self.projects_df = None

    def load_latest_data(self):
        """Load latest CSV files"""
        print("📂 Loading latest data...")

        # Get all CSV files recursively (nested export folders included)
        job_files = list(self.data_dir.rglob("*jobs*.csv"))
        talent_files = list(self.data_dir.rglob("*talent*.csv"))
        project_files = list(self.data_dir.rglob("*project*.csv"))

        # Sort by modification time
        job_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        talent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        project_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Load up to 5 latest files from each category to improve coverage
        if job_files:
            frames = []
            for file in job_files[:5]:
                try:
                    frames.append(pd.read_csv(file, low_memory=False))
                except Exception:
                    pass
            self.jobs_df = pd.concat(frames, ignore_index=True) if frames else None
            print(f"   ✅ Jobs: {len(self.jobs_df) if self.jobs_df is not None else 0} records")

        if talent_files:
            frames = []
            for file in talent_files[:5]:
                try:
                    frames.append(pd.read_csv(file, low_memory=False))
                except Exception:
                    pass
            self.talent_df = pd.concat(frames, ignore_index=True) if frames else None
            print(f"   ✅ Talent: {len(self.talent_df) if self.talent_df is not None else 0} records")

        if project_files:
            frames = []
            for file in project_files[:5]:
                try:
                    frames.append(pd.read_csv(file, low_memory=False))
                except Exception:
                    pass
            self.projects_df = pd.concat(frames, ignore_index=True) if frames else None
            print(f"   ✅ Projects: {len(self.projects_df) if self.projects_df is not None else 0} records")

        return True

    def extract_job_titles(self):
        """Extract unique job titles from jobs data"""
        if self.jobs_df is None or 'title' not in self.jobs_df.columns:
            return []

        titles = self.jobs_df['title'].dropna().unique().tolist()
        return [str(t).lower().strip() for t in titles if t and len(str(t)) > 3]

    def extract_skills_from_text(self, text):
        """Extract skills/technologies from text"""
        if not text or not isinstance(text, str):
            return []

        skills = []
        text_lower = text.lower()

        for pattern in TECH_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.extend([m.lower() for m in matches if len(m) > 2])

        return list(set(skills))

    def extract_all_skills(self):
        """Extract all skills from all data sources"""
        all_skills = []

        def first_existing(row, keys):
            lower_map = {str(col).lower(): col for col in row.index}
            for key in keys:
                actual_key = lower_map.get(str(key).lower(), key)
                if actual_key in row and pd.notna(row.get(actual_key)):
                    return str(row.get(actual_key))
            return ""

        # From jobs titles and multiple description-like columns
        if self.jobs_df is not None:
            for _, row in self.jobs_df.iterrows():
                title = first_existing(row, ['title', 'job_title'])
                snippet = first_existing(
                    row,
                    ['snippet', 'description', 'summary', 'detail_summary', 'detail_description', 'overview']
                )
                all_skills.extend(self.extract_skills_from_text(title))
                all_skills.extend(self.extract_skills_from_text(snippet))

        # From talent titles and overview variants
        if self.talent_df is not None:
            for _, row in self.talent_df.iterrows():
                title = first_existing(row, ['title', 'headline'])
                overview = first_existing(row, ['overview', 'description', 'bio', 'summary'])
                all_skills.extend(self.extract_skills_from_text(title))
                all_skills.extend(self.extract_skills_from_text(overview))

        # From project titles and descriptions
        if self.projects_df is not None:
            for _, row in self.projects_df.iterrows():
                title = first_existing(row, ['title', 'project_title'])
                description = first_existing(
                    row, ['description', 'summary', 'detail_project_description']
                )
                all_skills.extend(self.extract_skills_from_text(title))
                all_skills.extend(self.extract_skills_from_text(description))

        # Count skill frequency
        skill_counter = Counter(all_skills)
        return skill_counter

    def generate_keywords(self, count=15):
        """Generate new high-value keywords based on analysis"""
        print(f"\n🤖 Generating {count} new keywords...")

        self.load_latest_data()
        skill_counter = self.extract_all_skills()

        # Get top skills
        top_skills = skill_counter.most_common(50)

        # Generate keywords with scores
        keywords = []
        used_keywords = set()

        # Get existing keywords to avoid duplicates
        existing = self._get_existing_keywords()
        existing_lower = {k.lower() for k in existing}

        # Generate from trending skills
        for skill, freq in top_skills:
            if len(keywords) >= count:
                break

            skill_clean = skill.strip().lower()
            if len(skill_clean) < 3 or skill_clean in existing_lower:
                continue

            # Calculate opportunity score
            score = min(100, int(freq * 2 + 50))

            # Determine priority
            if score >= 85:
                priority = "CRITICAL"
            elif score >= 75:
                priority = "HIGH"
            elif score >= 60:
                priority = "NORMAL"
            else:
                priority = "LOW"

            keywords.append({
                "keyword": skill_clean,
                "recommended_priority": priority,
                "opportunity_score": score,
                "frequency": freq,
                "demand": int(freq * 1.5),
                "supply": int(freq * 0.5),
                "gap_ratio": round(freq * 3, 2),
                "source": "nlp_analysis"
            })

            existing_lower.add(skill_clean)

        # If we need more keywords, generate from combinations
        if len(keywords) < count:
            base_terms = ['developer', 'engineer', 'specialist', 'expert']
            tech_terms = ['python', 'javascript', 'ai', 'machine learning', 'data', 'api']

            for tech in tech_terms:
                if len(keywords) >= count:
                    break

                for base in base_terms:
                    if len(keywords) >= count:
                        break

                    kw = f"{tech} {base}"
                    if kw.lower() not in existing_lower:
                        keywords.append({
                            "keyword": kw,
                            "recommended_priority": "NORMAL",
                            "opportunity_score": 65,
                            "frequency": 10,
                            "demand": 30,
                            "supply": 15,
                            "gap_ratio": 2.0,
                            "source": "nlp_generated"
                        })
                        existing_lower.add(kw.lower())

        print(f"   ✅ Generated {len(keywords)} keywords")
        return keywords[:count]

    def _get_existing_keywords(self):
        """Get existing keywords to avoid duplicates"""
        existing = set()

        # From auto_keywords in background.js
        existing.update([
            'ai agent', 'machine learning', 'chrome extension', 'data analyst',
            'react developer', 'api integration', 'web scraping', 'workflow automation',
            'business intelligence', 'python automation', 'chatgpt integration',
            'llm development', 'data engineer', 'full stack developer', 'node.js developer',
            'mobile app developer', 'zapier expert', 'make automation', 'data visualization', 'sql expert'
        ])

        return existing

    def save_keywords(self, keywords):
        """Save keywords to output files"""
        output = {
            "generated_at": datetime.now().isoformat(),
            "keywords": keywords
        }

        # Save to data directory
        RECOMMENDED_OUTPUT.write_text(json.dumps(output, indent=2))
        print(f"   ✅ Saved to: {RECOMMENDED_OUTPUT}")

        # Save to Downloads for extension
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_FILE.write_text(json.dumps(output, indent=2))
        print(f"   ✅ Saved to: {QUEUE_FILE}")

        return True

    def analyze_and_generate(self, count=15):
        """Main analysis workflow"""
        print("\n" + "="*60)
        print("🧠 NLP KEYWORD GENERATOR - STARTING ANALYSIS")
        print("="*60)

        keywords = self.generate_keywords(count)
        self.save_keywords(keywords)

        print("\n📊 TOP KEYWORDS:")
        for i, kw in enumerate(keywords[:10], 1):
            print(f"   {i}. {kw['keyword']:30s} | Score: {kw['opportunity_score']:3d} | {kw['recommended_priority']}")

        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE!")
        print("="*60 + "\n")

        return keywords

def main():
    """Run NLP analysis"""
    generator = NLPKeywordGenerator()
    keywords = generator.analyze_and_generate(count=15)
    return keywords

if __name__ == "__main__":
    main()
