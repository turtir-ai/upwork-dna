"""
Golden Title Generator
======================
Generates high-performance talent titles based on elite pattern analysis.

Upwork title constraints:
- Maximum 70 characters
- Should include: role, primary skills, outcomes
- Pattern: Role | Skill | Skill | Outcome format works best

Author: Upwork Extension Team
Date: 2026-02-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import Counter
import re


class GoldenTitleGenerator:
    """
    Generates optimized Upwork titles based on elite talent pattern analysis.

    Pattern Analysis Features:
    - Extracts common title structures from elite performers
    - Identifies high-value skill combinations
    - Enforces 70-character limit
    - Uses role | skill | outcome format
    """

    # Title patterns based on elite performer analysis
    TITLE_PATTERNS = {
        'role_outcome': '{role} | {primary_skill} | {outcome}',
        'skill_stack': '{primary_skill} | {secondary_skill} | {tertiary_skill}',
        'expert_format': '{role} | {stack} | {specialization}',
        'outcome_focused': '{outcome} | {role} | {primary_skill}',
        'minimalist': '{role} | {primary_skill}',
    }

    # Common role prefixes
    ROLE_PREFIXES = [
        'Data Analyst', 'Business Analyst', 'Data Engineer',
        'Analytics Expert', 'BI Developer', 'Data Scientist',
        'SQL Developer', 'Reporting Specialist', 'Dashboard Expert'
    ]

    # High-value outcomes
    OUTCOME_KEYWORDS = [
        'Actionable Insights', 'Data-Driven Decisions', 'Growth',
        'Revenue Optimization', 'Cost Reduction', 'Efficiency',
        'Executive Dashboards', 'KPI Tracking', 'ROI Analysis'
    ]

    # Skill tier classification
    PREMIUM_SKILLS = [
        'SQL', 'Python', 'Tableau', 'Power BI', 'Looker Studio',
        'Advanced Excel', 'Data Visualization', 'ETL', 'Snowflake',
        'dbt', 'BigQuery', 'Redshift', 'Azure', 'AWS Analytics'
    ]

    # Separator patterns to detect
    SEPARATORS = {
        'pipe': '|',
        'dash': ' - ',
        'slash': ' / ',
        'bullet': ' • '
    }

    # Maximum title length (Upwork constraint)
    MAX_TITLE_LENGTH = 70

    def __init__(self, elite_threshold: float = 50.0):
        """
        Initialize the title generator.

        Args:
            elite_threshold: Hourly rate threshold for elite talent ($/hr)
        """
        self.elite_threshold = elite_threshold
        self.pattern_stats = {}
        self.skill_rankings = {}

    def clean_title(self, title: str) -> str:
        """
        Clean and normalize title text.

        Args:
            title: Raw title string

        Returns:
            Cleaned title string
        """
        if not isinstance(title, str):
            return ""

        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title.strip())

        # Normalize separators to pipe
        for sep_name, sep_char in self.SEPARATORS.items():
            if sep_char != '|':
                title = title.replace(sep_char, ' | ')

        return title

    def parse_title_structure(self, title: str) -> Dict:
        """
        Parse title into components (role, skills, outcomes).

        Args:
            title: Cleaned title string

        Returns:
            Dict with parsed components
        """
        if not title:
            return {'role': '', 'skills': [], 'outcome': '', 'parts': []}

        parts = [p.strip() for p in title.split('|')]
        parts = [p for p in parts if p]

        result = {
            'role': parts[0] if len(parts) > 0 else '',
            'skills': [],
            'outcome': '',
            'parts': parts,
            'separator_count': title.count('|')
        }

        # Try to identify role
        for prefix in self.ROLE_PREFIXES:
            if prefix.lower() in parts[0].lower():
                result['role'] = prefix
                break

        # Extract skills (middle parts)
        if len(parts) > 1:
            for part in parts[1:-1] if len(parts) > 2 else parts[1:]:
                for skill in self.PREMIUM_SKILLS:
                    if skill.lower() in part.lower():
                        result['skills'].append(skill)
                        break

        # Extract outcome (last part)
        if len(parts) > 1:
            last_part = parts[-1].lower()
            for outcome in self.OUTCOME_KEYWORDS:
                if outcome.lower() in last_part:
                    result['outcome'] = outcome
                    break

        return result

    def analyze_elite_titles(self, talent_df: pd.DataFrame) -> Dict:
        """
        Analyze elite talent titles to extract successful patterns.

        Args:
            talent_df: DataFrame with talent data (must have 'title', 'rate' columns)

        Returns:
            Dictionary with pattern analysis results
        """
        results = {
            'total_analyzed': 0,
            'elite_titles': [],
            'pattern_frequency': Counter(),
            'skill_combinations': Counter(),
            'separator_usage': Counter(),
            'length_stats': {
                'min': 0,
                'max': 0,
                'mean': 0,
                'median': 0
            },
            'role_frequency': Counter(),
            'outcome_frequency': Counter(),
            'common_bigrams': Counter()
        }

        if talent_df.empty or 'title' not in talent_df.columns:
            return results

        # Parse rates if available
        if 'rate' in talent_df.columns:
            talent_df['parsed_rate'] = talent_df['rate'].apply(self._extract_rate)
            elite_mask = talent_df['parsed_rate'] >= self.elite_threshold
        else:
            elite_mask = pd.Series([True] * len(talent_df))

        elite_df = talent_df[elite_mask]
        results['total_analyzed'] = len(elite_df)

        if results['total_analyzed'] == 0:
            return results

        lengths = []
        all_skills = []
        all_outcomes = []

        for title in elite_df['title'].dropna():
            cleaned = self.clean_title(str(title))
            if not cleaned:
                continue

            results['elite_titles'].append(cleaned)
            lengths.append(len(cleaned))

            parsed = self.parse_title_structure(cleaned)

            # Count separators
            results['separator_usage'][parsed['separator_count']] += 1

            # Count patterns (by structure)
            pattern_key = f"{len(parsed['parts'])}_parts"
            results['pattern_frequency'][pattern_key] += 1

            # Extract role
            if parsed['role']:
                results['role_frequency'][parsed['role']] += 1

            # Extract outcomes
            if parsed['outcome']:
                results['outcome_frequency'][parsed['outcome']] += 1
                all_outcomes.append(parsed['outcome'])

            # Extract skills
            if parsed['skills']:
                # Individual skills
                for skill in parsed['skills']:
                    all_skills.append(skill)
                    results['skill_combinations'][skill] += 1

                # Skill pairs
                if len(parsed['skills']) >= 2:
                    for i in range(len(parsed['skills']) - 1):
                        pair = f"{parsed['skills'][i]} + {parsed['skills'][i+1]}"
                        results['common_bigrams'][pair] += 1

        # Calculate length statistics
        if lengths:
            results['length_stats'] = {
                'min': int(min(lengths)),
                'max': int(max(lengths)),
                'mean': round(np.mean(lengths), 1),
                'median': round(np.median(lengths), 1)
            }

        # Store skill rankings
        self.skill_rankings = dict(results['skill_combinations'].most_common(20))

        return results

    def _extract_rate(self, rate_val) -> float:
        """
        Extract numeric rate from various formats.

        Handles:
        - String: "$75/hr" -> 75.0
        - String: "75" -> 75.0
        - Numeric: 75.0 -> 75.0
        """
        if isinstance(rate_val, (int, float)):
            return float(rate_val)

        if not isinstance(rate_val, str):
            return 0.0

        # Remove $/hr and extract number
        cleaned = rate_val.replace('$', '').replace('/hr', '').strip()
        match = re.search(r'(\d+\.?\d*)', cleaned)
        return float(match.group(1)) if match else 0.0

    def _truncate_to_limit(self, title: str, limit: int = None) -> str:
        """
        Truncate title to fit within character limit.

        Args:
            title: Title string
            limit: Character limit (defaults to MAX_TITLE_LENGTH)

        Returns:
            Truncated title that fits within limit
        """
        limit = limit or self.MAX_TITLE_LENGTH

        if len(title) <= limit:
            return title

        # Try to truncate at separator
        parts = title.split('|')
        if len(parts) > 1:
            # Remove last part and try again
            truncated = '|'.join(parts[:-1]).strip()
            if len(truncated) <= limit:
                return truncated

        # Last resort: hard truncate
        return title[:limit - 3].strip() + '...'

    def _select_best_pattern(self, profile_data: Dict) -> str:
        """
        Select the best title pattern based on profile data.

        Args:
            profile_data: Dictionary with profile information

        Returns:
            Pattern key from TITLE_PATTERNS
        """
        role = profile_data.get('role', '')
        skills = profile_data.get('skills', [])
        outcome = profile_data.get('outcome', '')

        # Count available components
        has_role = bool(role)
        has_skills = len(skills) >= 2
        has_outcome = bool(outcome)

        if has_role and has_skills and has_outcome:
            return 'expert_format'
        elif has_role and has_outcome:
            return 'role_outcome'
        elif has_skills:
            return 'skill_stack'
        elif has_role and skills:
            return 'minimalist'
        else:
            return 'outcome_focused'

    def generate_titles(
        self,
        profile_data: Dict,
        count: int = 5,
        elite_patterns: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Generate optimized titles based on profile data and elite patterns.

        Args:
            profile_data: Dictionary containing:
                - role: Primary role/title
                - skills: List of skills
                - outcome: Value proposition/outcome
                - specialization: Niche specialization
            count: Number of titles to generate
            elite_patterns: Optional pattern analysis from analyze_elite_titles()

        Returns:
            List of dicts with generated titles and metadata
        """
        titles = []

        role = profile_data.get('role', 'Data Analyst')
        skills = profile_data.get('skills', [])
        outcome = profile_data.get('outcome', '')
        specialization = profile_data.get('specialization', '')

        # Use elite skill rankings if available
        if elite_patterns and 'skill_combinations' in elite_patterns:
            top_skills = [s for s, _ in elite_patterns['skill_combinations'].most_common(5)]
        else:
            top_skills = self.PREMIUM_SKILLS[:5]

        # Prioritize profile skills that match elite patterns
        prioritized_skills = [s for s in skills if s in top_skills]
        if not prioritized_skills:
            prioritized_skills = skills[:3] if skills else top_skills[:3]

        # Generate title variations
        variations = self._generate_title_variations(
            role=role,
            skills=prioritized_skills,
            outcome=outcome,
            specialization=specialization,
            elite_patterns=elite_patterns
        )

        # Validate and truncate
        for title, meta in variations:
            title = self._truncate_to_limit(title)

            titles.append({
                'title': title,
                'length': len(title),
                'pattern': meta.get('pattern', 'custom'),
                'components': meta.get('components', {}),
                'score': self._score_title(title, meta, elite_patterns)
            })

        # Sort by score and return top N
        titles.sort(key=lambda x: x['score'], reverse=True)
        return titles[:count]

    def _generate_title_variations(
        self,
        role: str,
        skills: List[str],
        outcome: str,
        specialization: str,
        elite_patterns: Optional[Dict] = None
    ) -> List[Tuple[str, Dict]]:
        """
        Generate title format variations.

        Returns:
            List of (title, metadata) tuples
        """
        variations = []

        # 1. Classic: Role | Skill | Skill
        if len(skills) >= 2:
            title = f"{role} | {skills[0]} | {skills[1]}"
            variations.append((title, {'pattern': 'classic', 'components': {'role': role, 'skills': skills[:2]}}))

        # 2. Expert: Role | Stack | Outcome
        if outcome and skills:
            stack = ' | '.join(skills[:2])
            title = f"{role} | {stack} | {outcome}"
            variations.append((title, {'pattern': 'expert', 'components': {'role': role, 'skills': skills[:2], 'outcome': outcome}}))

        # 3. Minimal: Role | Primary Skill
        if skills:
            title = f"{role} | {skills[0]}"
            variations.append((title, {'pattern': 'minimal', 'components': {'role': role, 'skills': [skills[0]]}}))

        # 4. Outcome-focused: Outcome | Role | Skill
        if outcome and skills:
            title = f"{outcome} | {role} | {skills[0]}"
            variations.append((title, {'pattern': 'outcome', 'components': {'outcome': outcome, 'role': role, 'skills': [skills[0]]}}))

        # 5. Specialization: Role | Specialization | Skill
        if specialization and skills:
            title = f"{role} | {specialization} | {skills[0]}"
            variations.append((title, {'pattern': 'specialization', 'components': {'role': role, 'specialization': specialization, 'skills': [skills[0]]}}))

        # 6. Triple Skill: Skill1 | Skill2 | Skill3 (no role, for specialists)
        if len(skills) >= 3:
            title = f"{skills[0]} | {skills[1]} | {skills[2]}"
            variations.append((title, {'pattern': 'triple_skill', 'components': {'skills': skills[:3]}}))

        # 7. Pattern-matched (based on elite analysis)
        if elite_patterns and 'role_frequency' in elite_patterns:
            top_roles = elite_patterns['role_frequency'].most_common(1)
            if top_roles and skills:
                top_role = top_roles[0][0]
                title = f"{top_role} | {skills[0]}"
                variations.append((title, {'pattern': 'elite_match', 'components': {'role': top_role, 'skills': [skills[0]]}}))

        return variations

    def _score_title(self, title: str, metadata: Dict, elite_patterns: Optional[Dict] = None) -> float:
        """
        Score a title based on optimization criteria.

        Scoring factors:
        - Length proximity to 60-70 chars (optimal range)
        - Keyword presence (elite skills, outcomes)
        - Pattern match with elite performers
        - Separator count (2-3 separators is optimal)

        Returns:
            Score from 0-100
        """
        score = 0.0

        # 1. Length score (optimal: 55-70 chars)
        length = len(title)
        if 55 <= length <= 70:
            score += 30  # Optimal
        elif 45 <= length < 55:
            score += 20  # Good
        elif 35 <= length < 45:
            score += 10  # Acceptable
        elif length > 70:
            score -= 20  # Too long (will be truncated)
        else:
            score += 5   # Too short

        # 2. Separator score (2-3 separators is optimal)
        separator_count = title.count('|')
        if 2 <= separator_count <= 3:
            score += 20
        elif separator_count == 1:
            score += 10

        # 3. Keyword score (elite skills and outcomes)
        components = metadata.get('components', {})
        has_role = 'role' in components and components['role']
        has_skills = 'skills' in components and components['skills']
        has_outcome = 'outcome' in components and components['outcome']

        if has_role:
            score += 10
        if has_skills:
            score += min(len(components['skills']) * 5, 15)  # Max 15 points
        if has_outcome:
            score += 15

        # 4. Elite pattern match bonus
        if elite_patterns and metadata.get('pattern') == 'elite_match':
            score += 20

        # 5. Premium skill bonus
        title_lower = title.lower()
        premium_matches = sum(1 for skill in self.PREMIUM_SKILLS if skill.lower() in title_lower)
        score += min(premium_matches * 3, 15)

        # 6. Outcome keyword bonus
        outcome_matches = sum(1 for oc in self.OUTCOME_KEYWORDS if oc.lower() in title_lower)
        score += min(outcome_matches * 5, 10)

        return min(max(score, 0), 100)  # Clamp to 0-100

    def get_top_skill_combinations(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get top skill combinations from elite analysis.

        Args:
            limit: Maximum number of combinations to return

        Returns:
            List of (combination, count) tuples
        """
        if not self.skill_rankings:
            return []

        return list(self.skill_rankings.items())[:limit]

    def validate_title(self, title: str) -> Dict:
        """
        Validate a title against Upwork constraints.

        Args:
            title: Title to validate

        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': True,
            'length': len(title),
            'within_limit': len(title) <= self.MAX_TITLE_LENGTH,
            'issues': [],
            'warnings': []
        }

        if not title or not title.strip():
            result['valid'] = False
            result['issues'].append('Title is empty')
            return result

        if not result['within_limit']:
            result['valid'] = False
            result['issues'].append(f'Title exceeds {self.MAX_TITLE_LENGTH} characters')

        # Check for common issues
        if len(title) < 20:
            result['warnings'].append('Title is quite short - consider adding more detail')

        if '|' not in title:
            result['warnings'].append('Consider using pipe separators (|) for better readability')

        return result


# Convenience functions for quick usage
def generate_optimal_title(
    role: str,
    skills: List[str],
    outcome: str = '',
    elite_patterns: Optional[Dict] = None
) -> str:
    """
    Quick function to generate a single optimal title.

    Args:
        role: Primary role/title
        skills: List of skills
        outcome: Value proposition (optional)
        elite_patterns: Optional elite pattern analysis

    Returns:
        Optimized title string
    """
    generator = GoldenTitleGenerator()

    profile_data = {
        'role': role,
        'skills': skills,
        'outcome': outcome
    }

    titles = generator.generate_titles(profile_data, count=1, elite_patterns=elite_patterns)

    return titles[0]['title'] if titles else f"{role} | {skills[0] if skills else 'Expert'}"


def analyze_talent_titles(talent_df: pd.DataFrame, elite_threshold: float = 50.0) -> Dict:
    """
    Quick function to analyze elite talent titles.

    Args:
        talent_df: Talent DataFrame
        elite_threshold: Rate threshold for elite classification

    Returns:
        Pattern analysis results
    """
    generator = GoldenTitleGenerator(elite_threshold=elite_threshold)
    return generator.analyze_elite_titles(talent_df)
