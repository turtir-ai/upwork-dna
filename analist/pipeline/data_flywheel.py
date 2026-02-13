#!/usr/bin/env python3
"""
DATA FLYWHEEL (P2.2)
====================
Analyze current data to score new keywords and prioritize queue.

Features:
- Analyze current data for market insights
- Score new keyword opportunities
- Prioritize keywords by value
- Inject keywords into queue

Author: Upwork Extension Pipeline
Date: 2026-02-07
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import Counter
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataFlywheel')


class DataFlywheel:
    """
    Data Flywheel for continuous keyword optimization.

    Analyzes current data to:
    1. Identify high-value keyword opportunities
    2. Score keywords by market potential
    3. Prioritize queue for next runs
    4. Inject recommendations into queue
    """

    # Priority levels matching extension
    PRIORITY_LEVELS = {
        'CRITICAL': 100,  # Premium opportunity
        'HIGH': 75,       # High value
        'NORMAL': 50,     # Standard
        'LOW': 25         # Exploratory
    }

    def __init__(
        self,
        data_directory: str = str(Path.home() / "Downloads" / "upwork_dna"),
        output_directory: str = str(Path.home() / "Downloads" / "upwork_dna"),
        min_frequency: int = 5,
        max_keywords: int = 20
    ):
        """
        Initialize the data flywheel.

        Args:
            data_directory: Directory containing exported data
            output_directory: Directory for recommended keywords
            min_frequency: Minimum keyword frequency to consider
            max_keywords: Maximum number of keywords to recommend
        """
        self.data_directory = Path(data_directory)
        self.output_directory = Path(output_directory)
        self.min_frequency = min_frequency
        self.max_keywords = max_keywords

        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)

        # Stop words for filtering
        self.stop_words = {
            'and', 'for', 'to', 'the', 'of', 'in', 'a', 'an', 'is', 'with',
            'on', 'at', 'by', 'from', 'or', 'as', 'be', 'was', 'are', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'looking', 'needed', 'expert', 'specialist', 'professional',
            'experienced', 'seeking', 'hiring', 'wanted', 'required'
        }

    def load_data(self) -> Dict[str, pd.DataFrame]:
        """Load all exported data from upwork_dna directory."""
        data = {
            'jobs': pd.DataFrame(),
            'talent': pd.DataFrame(),
            'projects': pd.DataFrame()
        }

        # Scan for CSV files
        for csv_file in self.data_directory.rglob("upwork_jobs_*.csv"):
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                data['jobs'] = pd.concat([data['jobs'], df], ignore_index=True)
                logger.info(f"Loaded jobs from {csv_file.name}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"Failed to load {csv_file}: {e}")

        for csv_file in self.data_directory.rglob("upwork_talent_*.csv"):
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                data['talent'] = pd.concat([data['talent'], df], ignore_index=True)
                logger.info(f"Loaded talent from {csv_file.name}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"Failed to load {csv_file}: {e}")

        for csv_file in self.data_directory.rglob("upwork_projects_*.csv"):
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                data['projects'] = pd.concat([data['projects'], df], ignore_index=True)
                logger.info(f"Loaded projects from {csv_file.name}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"Failed to load {csv_file}: {e}")

        return data

    def analyze_current_data(self, current_keywords: List[str]) -> List[Dict]:
        """
        Analyze current data and score new keyword opportunities.

        Args:
            current_keywords: List of keywords already analyzed

        Returns:
            List of scored keyword recommendations
        """
        logger.info("Starting data flywheel analysis...")

        # Load data
        data = self.load_data()

        if all(df.empty for df in data.values()):
            logger.warning("No data found for analysis")
            return []

        # Extract keywords from various sources
        keyword_candidates = self._extract_keywords(data)

        # Score keywords
        scored_keywords = self._score_keywords(keyword_candidates, data, current_keywords)

        # Sort by score
        scored_keywords.sort(key=lambda x: x['score'], reverse=True)

        # Take top N
        recommendations = scored_keywords[:self.max_keywords]

        logger.info(f"Generated {len(recommendations)} keyword recommendations")

        return recommendations

    def _extract_keywords(self, data: Dict[str, pd.DataFrame]) -> Counter:
        """Extract potential keywords from job titles, skills, etc."""
        all_terms = Counter()

        # From job titles
        if not data['jobs'].empty and 'title' in data['jobs'].columns:
            for title in data['jobs']['title'].dropna():
                terms = self._extract_terms_from_text(str(title))
                all_terms.update(terms)

        # From skills
        if not data['jobs'].empty and 'skills' in data['jobs'].columns:
            for skills in data['jobs']['skills'].dropna():
                terms = self._extract_terms_from_text(str(skills))
                all_terms.update(terms)

        # From talent titles
        if not data['talent'].empty and 'title' in data['talent'].columns:
            for title in data['talent']['title'].dropna():
                terms = self._extract_terms_from_text(str(title))
                all_terms.update(terms)

        return all_terms

    def _extract_terms_from_text(self, text: str) -> List[str]:
        """Extract individual terms and bigrams from text."""
        import re
        from itertools import combinations

        # Clean and tokenize
        text = text.lower()
        text = re.sub(r'[^\w\s\-\|\/]', ' ', text)
        words = [w for w in text.split() if len(w) > 2 and w not in self.stop_words]

        terms = []

        # Individual words
        terms.extend(words)

        # Bigrams (2-word combinations)
        if len(words) >= 2:
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                terms.append(bigram)

        return terms

    def _score_keywords(
        self,
        keyword_candidates: Counter,
        data: Dict[str, pd.DataFrame],
        current_keywords: List[str]
    ) -> List[Dict]:
        """Score keywords by market opportunity."""
        scored = []
        current_set = set(k.lower() for k in current_keywords)

        for keyword, frequency in keyword_candidates.items():
            # Skip if already analyzed
            if keyword.lower() in current_set:
                continue

            # Skip if below minimum frequency
            if frequency < self.min_frequency:
                continue

            # Calculate score
            score = self._calculate_keyword_score(keyword, frequency, data)

            scored.append({
                'keyword': keyword,
                'score': score['total'],
                'frequency': frequency,
                'priority': score['priority'],
                'estimatedValue': score.get('estimated_value', 0),
                'factors': score['factors']
            })

        return scored

    def _calculate_keyword_score(
        self,
        keyword: str,
        frequency: int,
        data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """Calculate comprehensive score for a keyword."""
        factors = {}
        total_score = 0

        # Factor 1: Frequency (0-25 points)
        freq_score = min(25, frequency * 2)
        factors['frequency'] = freq_score
        total_score += freq_score

        # Factor 2: High-value job presence (0-30 points)
        hv_score = self._get_high_value_score(keyword, data)
        factors['high_value_potential'] = hv_score
        total_score += hv_score

        # Factor 3: Competition (inverse) (0-20 points)
        comp_score = self._get_competition_score(keyword, data)
        factors['competition'] = comp_score
        total_score += comp_score

        # Factor 4: Skill specificity (0-15 points)
        spec_score = self._get_specificity_score(keyword)
        factors['specificity'] = spec_score
        total_score += spec_score

        # Factor 5: Trend potential (0-10 points)
        trend_score = self._get_trend_score(keyword)
        factors['trend'] = trend_score
        total_score += trend_score

        # Determine priority level
        if total_score >= 80:
            priority = 'CRITICAL'
        elif total_score >= 60:
            priority = 'HIGH'
        elif total_score >= 40:
            priority = 'NORMAL'
        else:
            priority = 'LOW'

        return {
            'total': total_score,
            'priority': priority,
            'estimated_value': total_score * 10,
            'factors': factors
        }

    def _get_high_value_score(self, keyword: str, data: Dict[str, pd.DataFrame]) -> float:
        """Score based on presence in high-value jobs."""
        if data['jobs'].empty:
            return 0

        score = 0
        jobs = data['jobs']

        # Check if keyword appears in high-value jobs
        # High value = budget >= 500 or hourly >= 30
        if 'budget' in jobs.columns:
            # Parse budget for high-value indicator
            for _, job in jobs.iterrows():
                title = str(job.get('title', '')).lower()
                desc = str(job.get('description', '')).lower()
                budget = str(job.get('budget', ''))

                if keyword.lower() in title or keyword.lower() in desc:
                    # Check if high value
                    if any(x in budget.lower() for x in ['500', '1000', '50/hr', '75/hr']):
                        score += 5
                        if score >= 30:
                            break

        return min(30, score)

    def _get_competition_score(self, keyword: str, data: Dict[str, pd.DataFrame]) -> float:
        """Score based on competition (lower is better)."""
        if data['talent'].empty:
            return 10  # Neutral score if no data

        # Count how many talent profiles mention this keyword
        talent = data['talent']
        mentions = 0

        for _, profile in talent.iterrows():
            title = str(profile.get('title', '')).lower()
            skills = str(profile.get('skills', '')).lower()
            if keyword.lower() in title or keyword.lower() in skills:
                mentions += 1

        # Lower mentions = lower competition = higher score
        if mentions == 0:
            return 20  # No competition found
        elif mentions <= 5:
            return 15
        elif mentions <= 15:
            return 10
        else:
            return 5

    def _get_specificity_score(self, keyword: str) -> float:
        """Score based on keyword specificity."""
        # Longer keywords = more specific = higher score
        words = keyword.split()

        if len(words) >= 3:
            return 15
        elif len(words) == 2:
            return 10
        else:
            return 5

    def _get_trend_score(self, keyword: str) -> float:
        """Score based on trending technology indicators."""
        trend_indicators = [
            'ai', 'machine learning', 'ml', 'deep learning',
            'nlp', 'gpt', 'llm', 'transformer', 'python',
            'automation', 'pipeline', 'etl', 'cloud', 'aws',
            'azure', 'gcp', 'docker', 'kubernetes', 'mlops'
        ]

        keyword_lower = keyword.lower()
        matches = sum(1 for indicator in trend_indicators if indicator in keyword_lower)

        return min(10, matches * 3)

    def inject_keywords_into_queue(self, keywords: List[Dict]) -> bool:
        """
        Inject scored keywords into the queue.

        Args:
            keywords: List of scored keyword recommendations

        Returns:
            True if successful, False otherwise
        """
        output_file = self.output_directory / "recommended_keywords.json"

        # Prepare keywords for queue
        queue_keywords = []
        for kw in keywords:
            queue_keywords.append({
                'keyword': kw['keyword'],
                # Extension/API contract fields
                'recommended_priority': kw['priority'],
                'opportunity_score': kw['score'],
                # Backward-compatible fields
                'priority': kw['priority'],
                'estimatedValue': kw.get('estimatedValue', 0),
                'score': kw['score'],
                'frequency': kw['frequency'],
                'factors': kw['factors']
            })

        # Save to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'generated_at': datetime.now().isoformat(),
                    'keywords': queue_keywords,
                    'metadata': {
                        'total_keywords': len(queue_keywords),
                        'priority_distribution': {
                            level: sum(1 for k in queue_keywords if k['priority'] == level)
                            for level in self.PRIORITY_LEVELS.keys()
                        }
                    }
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"Injected {len(queue_keywords)} keywords into queue")
            logger.info(f"Saved to: {output_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to inject keywords: {e}")
            return False

    def execute_flywheel(self, current_keywords: List[str]) -> List[Dict]:
        """
        Execute the complete flywheel cycle.

        Args:
            current_keywords: List of keywords already analyzed

        Returns:
            List of new keyword recommendations
        """
        logger.info("="*60)
        logger.info("🔄 EXECUTING DATA FLYWHEEL")
        logger.info("="*60)

        # Analyze current data
        recommendations = self.analyze_current_data(current_keywords)

        if not recommendations:
            logger.warning("No recommendations generated")
            return []

        # Inject into queue
        success = self.inject_keywords_into_queue(recommendations)

        if success:
            logger.info("✅ Flywheel cycle complete")
            self._print_summary(recommendations)
        else:
            logger.error("❌ Flywheel cycle failed")

        return recommendations

    def _print_summary(self, recommendations: List[Dict]):
        """Print summary of recommendations."""
        print("\n" + "="*60)
        print("📊 KEYWORD RECOMMENDATIONS")
        print("="*60)

        for i, rec in enumerate(recommendations[:10], 1):
            print(f"\n{i}. {rec['keyword'].title()}")
            print(f"   Priority: {rec['priority']}")
            print(f"   Score: {rec['score']:.1f}")
            print(f"   Frequency: {rec['frequency']}")


def default_flywheel_callback(keywords: List[Dict]):
    """Default callback for flywheel completion."""
    print("\n" + "="*60)
    print("🚀 FLYWHEEL RECOMMENDATIONS READY")
    print("="*60)
    print(f"Generated {len(keywords)} new keyword opportunities")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Example usage
    flywheel = DataFlywheel(
        data_directory=str(Path.home() / "Downloads" / "upwork_dna"),
        output_directory=str(Path.home() / "Downloads" / "upwork_dna")
    )

    # Execute flywheel
    recommendations = flywheel.execute_flywheel(
        current_keywords=['sql data analyst', 'python developer']
    )

    if recommendations:
        default_flywheel_callback(recommendations)
