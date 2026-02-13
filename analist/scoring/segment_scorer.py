"""
Multi-Factor Score-First Segmentation for Upwork Market Analysis.

This module implements composite scoring for jobs and talent based on multiple factors.
Each score ranges from 0-100 with detailed factor breakdowns.
"""

import re
import math
from typing import Dict, Any, Optional, List
from collections import Counter

# Try importing numpy, make it optional
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class SegmentScorer:
    """
    Multi-factor scoring engine for Upwork jobs and talent segmentation.

    Job Scoring Factors:
        - Budget (absolute and percentile)
        - Client Quality (rating, spend, verification)
        - Competition (proposal count)
        - Urgency (posting date, interview rate)
        - Skill Match (rare skills, expertise level)

    Talent Scoring Factors:
        - Rate Percentile (relative positioning)
        - Badge Value (Expert, Top Rated, etc.)
        - Job Success Score (JSS)
        - Portfolio (project count, quality)
        - Skill Rarity (uniqueness in market)
    """

    # Scoring weights for different factors
    JOB_WEIGHTS = {
        'budget': 0.25,
        'client_quality': 0.25,
        'competition': 0.20,
        'urgency': 0.15,
        'skill_match': 0.15
    }

    TALENT_WEIGHTS = {
        'rate_percentile': 0.25,
        'badge_value': 0.20,
        'job_success': 0.25,
        'portfolio': 0.15,
        'skill_rarity': 0.15
    }

    def __init__(self, budget_percentiles: Optional[Dict] = None,
                 rate_percentiles: Optional[Dict] = None,
                 skill_frequencies: Optional[Dict] = None):
        """
        Initialize scorer with market benchmarks.

        Args:
            budget_percentiles: Dict mapping niches to budget percentiles (25th, 50th, 75th)
            rate_percentiles: Dict mapping niches to rate percentiles
            skill_frequencies: Dict of skill -> frequency across market
        """
        self.budget_percentiles = budget_percentiles or {}
        self.rate_percentiles = rate_percentiles or {}
        self.skill_frequencies = skill_frequencies or {}

    def _extract_numeric_budget(self, budget_val: Any) -> float:
        """Extract numeric budget value from various formats."""
        if isinstance(budget_val, (int, float)):
            return float(budget_val)

        if isinstance(budget_val, str):
            # Remove currency symbols, extract numbers
            cleaned = budget_val.replace('$', '').replace(',', '').strip()
            # Handle hourly rates (e.g., "50-100/hr")
            if '-' in cleaned:
                parts = cleaned.split('-')
                nums = []
                for part in parts:
                    num_match = re.search(r'[\d.]+', part)
                    if num_match:
                        nums.append(float(num_match.group()))
                return sum(nums) / len(nums) if nums else 0.0
            # Handle single values
            num_match = re.search(r'[\d.]+', cleaned)
            if num_match:
                return float(num_match.group())

        return 0.0

    def _extract_numeric_rate(self, rate_val: Any) -> float:
        """Extract numeric hourly rate from various formats."""
        if isinstance(rate_val, (int, float)):
            return float(rate_val)

        if isinstance(rate_val, str):
            cleaned = rate_val.replace('$', '').replace(',', '').replace('/hr', '').replace('/hour', '').strip()
            num_match = re.search(r'[\d.]+', cleaned)
            if num_match:
                return float(num_match.group())

        return 0.0

    def _extract_client_rating(self, row: Dict) -> float:
        """Extract client rating from row."""
        rating = row.get('client_rating', 0)
        try:
            return float(rating) if rating else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _extract_total_spent(self, row: Dict) -> float:
        """Extract total spent from row."""
        spent = row.get('total_spent', 0)
        if isinstance(spent, str):
            return self._extract_numeric_budget(spent)
        return float(spent) if spent else 0.0

    def _extract_proposal_count(self, row: Dict) -> int:
        """Extract proposal count from row."""
        proposals = row.get('proposals', 0)
        try:
            return int(proposals) if proposals else 0
        except (ValueError, TypeError):
            return 0

    def _is_payment_verified(self, row: Dict) -> bool:
        """Check if client payment is verified."""
        verified = row.get('payment_verified', False)
        if isinstance(verified, str):
            return verified.lower() in ('true', 'yes', 'verified')
        return bool(verified)

    def _extract_badges(self, row: Dict) -> List[str]:
        """Extract badge list from talent row."""
        badges = row.get('detail_badges', '')
        if isinstance(badges, str):
            # Parse badge string (common formats: "badge1,badge2" or "badge1; badge2")
            return [b.strip() for b in re.split(r'[,;]', badges) if b.strip()]
        return []

    def _extract_jss(self, row: Dict) -> float:
        """Extract Job Success Score from talent row."""
        jss = row.get('detail_job_success', 0)
        try:
            return float(jss) if jss else 0.0
        except (ValueError, TypeError):
            return 0.0

    def score_job(self, job_row: Dict, niche: str = 'General') -> Dict[str, Any]:
        """
        Calculate composite job score (0-100) with factor breakdown.

        Args:
            job_row: Dictionary containing job data
            niche: Market niche for percentile comparison

        Returns:
            Dict with:
                - composite_score: Overall score (0-100)
                - factors: Dict of individual factor scores
                - breakdown: Detailed factor analysis
        """
        factors = {}

        # 1. BUDGET SCORE (25%)
        budget = self._extract_numeric_budget(job_row.get('budget', 0))
        factors['budget'] = self._score_budget(budget, niche)

        # 2. CLIENT QUALITY SCORE (25%)
        client_rating = self._extract_client_rating(job_row)
        total_spent = self._extract_total_spent(job_row)
        payment_verified = self._is_payment_verified(job_row)
        factors['client_quality'] = self._score_client_quality(
            client_rating, total_spent, payment_verified
        )

        # 3. COMPETITION SCORE (20%)
        proposals = self._extract_proposal_count(job_row)
        factors['competition'] = self._score_competition(proposals)

        # 4. URGENCY SCORE (15%)
        posted_date = job_row.get('posted', '')
        factors['urgency'] = self._score_urgency(posted_date)

        # 5. SKILL MATCH SCORE (15%)
        skills = job_row.get('skills', '')
        experience_level = job_row.get('experience_level', '')
        factors['skill_match'] = self._score_skill_match(skills, experience_level)

        # Calculate weighted composite score
        composite_score = sum(
            factors[factor]['score'] * self.JOB_WEIGHTS[factor]
            for factor in self.JOB_WEIGHTS
        )

        return {
            'composite_score': round(composite_score, 2),
            'factors': factors,
            'breakdown': self._format_job_breakdown(factors)
        }

    def score_talent(self, talent_row: Dict, niche: str = 'General') -> Dict[str, Any]:
        """
        Calculate composite talent score (0-100) with factor breakdown.

        Args:
            talent_row: Dictionary containing talent data
            niche: Market niche for percentile comparison

        Returns:
            Dict with:
                - composite_score: Overall score (0-100)
                - factors: Dict of individual factor scores
                - breakdown: Detailed factor analysis
        """
        factors = {}

        # 1. RATE PERCENTILE SCORE (25%)
        rate = self._extract_numeric_rate(talent_row.get('rate', 0))
        factors['rate_percentile'] = self._score_rate_percentile(rate, niche)

        # 2. BADGE VALUE SCORE (20%)
        badges = self._extract_badges(talent_row)
        factors['badge_value'] = self._score_badge_value(badges)

        # 3. JOB SUCCESS SCORE (25%)
        jss = self._extract_jss(talent_row)
        factors['job_success'] = self._score_job_success(jss)

        # 4. PORTFOLIO SCORE (15%)
        # Note: Portfolio details might not be in scraped data
        portfolio_count = talent_row.get('portfolio_count', 0)
        factors['portfolio'] = self._score_portfolio(portfolio_count)

        # 5. SKILL RARITY SCORE (15%)
        skills = talent_row.get('skills', '')
        factors['skill_rarity'] = self._score_skill_rarity(skills)

        # Calculate weighted composite score
        composite_score = sum(
            factors[factor]['score'] * self.TALENT_WEIGHTS[factor]
            for factor in self.TALENT_WEIGHTS
        )

        return {
            'composite_score': round(composite_score, 2),
            'factors': factors,
            'breakdown': self._format_talent_breakdown(factors)
        }

    def _score_budget(self, budget: float, niche: str) -> Dict[str, Any]:
        """Score budget based on market percentiles."""
        score = 50  # Default mid score

        # Get niche-specific percentiles
        percentiles = self.budget_percentiles.get(niche, {})
        p25 = percentiles.get('p25', 100)
        p50 = percentiles.get('p50', 500)
        p75 = percentiles.get('p75', 1000)

        if budget >= p75:
            score = 90 + min(10, (budget - p75) / p75 * 10)
        elif budget >= p50:
            score = 70 + (budget - p50) / (p75 - p50) * 20
        elif budget >= p25:
            score = 50 + (budget - p25) / (p50 - p25) * 20
        else:
            score = max(0, 50 * (budget / p25))

        return {
            'score': min(100, max(0, score)),
            'budget': budget,
            'percentile_rank': self._get_percentile_rank(budget, percentiles),
            'vs_market': f"{budget:.2f} vs {p50:.2f} median"
        }

    def _score_client_quality(self, rating: float, spent: float, verified: bool) -> Dict[str, Any]:
        """Score client quality based on rating, spend, and verification."""
        # Rating score (0-40 points)
        rating_score = min(40, rating * 8)

        # Spend score (0-40 points) - logarithmic scale
        if HAS_NUMPY:
            spend_score = min(40, np.log1p(spent) / np.log1p(10000) * 40)
        else:
            spend_score = min(40, math.log1p(spent) / math.log1p(10000) * 40)

        # Verification bonus (0-20 points)
        verified_score = 20 if verified else 0

        total = rating_score + spend_score + verified_score

        return {
            'score': min(100, total),
            'rating': rating,
            'rating_score': rating_score,
            'total_spent': spent,
            'spend_score': spend_score,
            'payment_verified': verified,
            'verified_bonus': verified_score
        }

    def _score_competition(self, proposals: int) -> Dict[str, Any]:
        """Score based on competition level (fewer proposals = higher score)."""
        if proposals <= 5:
            score = 90
        elif proposals <= 10:
            score = 75
        elif proposals <= 20:
            score = 60
        elif proposals <= 50:
            score = 40
        else:
            score = max(10, 40 - (proposals - 50) / 10)

        return {
            'score': min(100, max(0, score)),
            'proposal_count': proposals,
            'competition_level': self._get_competition_level(proposals)
        }

    def _score_urgency(self, posted_date: str) -> Dict[str, Any]:
        """Score based on posting recency."""
        # This is a simplified version - in production, parse actual dates
        score = 50  # Default mid score

        if not posted_date:
            score = 30
        else:
            # Simple heuristic: newer = higher urgency score
            # In production, calculate actual days difference
            posted_lower = posted_date.lower()
            if any(x in posted_lower for x in ['hour', 'minute', 'just posted']):
                score = 90
            elif 'day' in posted_lower:
                days = re.search(r'(\d+)\s*day', posted_lower)
                if days:
                    days_ago = int(days.group(1))
                    score = max(30, 90 - days_ago * 5)
                else:
                    score = 70
            elif 'week' in posted_lower:
                score = 50
            else:
                score = 30

        return {
            'score': min(100, max(0, score)),
            'posted_date': posted_date,
            'urgency_level': self._get_urgency_level(score)
        }

    def _score_skill_match(self, skills: str, experience_level: str) -> Dict[str, Any]:
        """Score based on skill rarity and experience level."""
        score = 50  # Base score

        # Parse skills
        skill_list = self._parse_skills(skills)

        # Calculate rarity score
        rarity_score = 50
        if skill_list and self.skill_frequencies:
            rare_skills = [s for s in skill_list if self.skill_frequencies.get(s, 0) < 0.01]
            rarity_score = 50 + len(rare_skills) * 10

        # Experience level bonus
        exp_bonus = 0
        if experience_level:
            exp_lower = experience_level.lower()
            if 'expert' in exp_lower or 'executive' in exp_lower:
                exp_bonus = 20
            elif 'intermediate' in exp_lower:
                exp_bonus = 10

        score = min(100, rarity_score + exp_bonus)

        return {
            'score': min(100, max(0, score)),
            'skill_count': len(skill_list),
            'rare_skills': len([s for s in skill_list if self.skill_frequencies.get(s, 0) < 0.01]),
            'experience_level': experience_level,
            'exp_bonus': exp_bonus
        }

    def _score_rate_percentile(self, rate: float, niche: str) -> Dict[str, Any]:
        """Score talent based on rate percentile position."""
        score = 50  # Default mid score

        percentiles = self.rate_percentiles.get(niche, {})
        p25 = percentiles.get('p25', 20)
        p50 = percentiles.get('p50', 50)
        p75 = percentiles.get('p75', 100)

        # Higher rate = higher positioning (assuming quality)
        if rate >= p75:
            score = 90 + min(10, (rate - p75) / p75 * 10)
        elif rate >= p50:
            score = 70 + (rate - p50) / (p75 - p50) * 20
        elif rate >= p25:
            score = 50 + (rate - p25) / (p50 - p25) * 20
        else:
            score = max(0, 50 * (rate / p25))

        return {
            'score': min(100, max(0, score)),
            'rate': rate,
            'percentile_rank': self._get_percentile_rank(rate, percentiles),
            'vs_market': f"{rate:.2f} vs {p50:.2f} median"
        }

    def _score_badge_value(self, badges: List[str]) -> Dict[str, Any]:
        """Score based on badge value."""
        badge_values = {
            'expert': 40,
            'top rated': 35,
            'top rated plus': 40,
            'rising talent': 20,
            'verified': 15,
            'pro': 30
        }

        score = 0
        matched_badges = []
        for badge in badges:
            badge_lower = badge.lower().strip()
            for key, value in badge_values.items():
                if key in badge_lower:
                    score += value
                    matched_badges.append(badge)
                    break

        return {
            'score': min(100, score),
            'badge_count': len(badges),
            'matched_badges': matched_badges,
            'total_value': score
        }

    def _score_job_success(self, jss: float) -> Dict[str, Any]:
        """Score based on Job Success Score."""
        if jss >= 95:
            score = 100
        elif jss >= 90:
            score = 85
        elif jss >= 85:
            score = 70
        elif jss >= 80:
            score = 50
        elif jss > 0:
            score = 30
        else:
            score = 0

        return {
            'score': score,
            'jss': jss,
            'tier': self._get_jss_tier(jss)
        }

    def _score_portfolio(self, portfolio_count: int) -> Dict[str, Any]:
        """Score based on portfolio quality/quantity."""
        if portfolio_count >= 20:
            score = 100
        elif portfolio_count >= 10:
            score = 80
        elif portfolio_count >= 5:
            score = 60
        elif portfolio_count >= 2:
            score = 40
        elif portfolio_count >= 1:
            score = 20
        else:
            score = 0

        return {
            'score': score,
            'portfolio_count': portfolio_count,
            'tier': self._get_portfolio_tier(portfolio_count)
        }

    def _score_skill_rarity(self, skills: str) -> Dict[str, Any]:
        """Score based on skill uniqueness in market."""
        skill_list = self._parse_skills(skills)

        if not skill_list or not self.skill_frequencies:
            return {
                'score': 50,
                'skill_count': 0,
                'rare_skill_count': 0,
                'avg_rarity': 0
            }

        # Calculate average rarity (lower frequency = higher rarity)
        frequencies = [self.skill_frequencies.get(s, 0.5) for s in skill_list]
        avg_freq = sum(frequencies) / len(frequencies) if frequencies else 0.5

        # Convert to score (lower frequency = higher score)
        score = 100 - (avg_freq * 100)

        rare_skills = [s for s in skill_list if self.skill_frequencies.get(s, 0) < 0.01]

        return {
            'score': min(100, max(0, score)),
            'skill_count': len(skill_list),
            'rare_skill_count': len(rare_skills),
            'avg_rarity': avg_freq,
            'rare_skills': rare_skills[:5]  # Top 5 rarest
        }

    def _parse_skills(self, skills: Any) -> List[str]:
        """Parse skills from various formats."""
        if isinstance(skills, list):
            return [str(s).strip() for s in skills if s]
        if isinstance(skills, str):
            return [s.strip() for s in re.split(r'[,;|]', skills) if s.strip()]
        return []

    def _get_percentile_rank(self, value: float, percentiles: Dict) -> str:
        """Get percentile rank description."""
        if not percentiles:
            return "Unknown"

        p25 = percentiles.get('p25', 0)
        p50 = percentiles.get('p50', 0)
        p75 = percentiles.get('p75', 0)

        if value >= p75:
            return "Top 25%"
        elif value >= p50:
            return "50-75th percentile"
        elif value >= p25:
            return "25-50th percentile"
        else:
            return "Bottom 25%"

    def _get_competition_level(self, proposals: int) -> str:
        """Get competition level description."""
        if proposals <= 5:
            return "Low"
        elif proposals <= 20:
            return "Medium"
        else:
            return "High"

    def _get_urgency_level(self, score: float) -> str:
        """Get urgency level description."""
        if score >= 80:
            return "Urgent"
        elif score >= 50:
            return "Moderate"
        else:
            return "Low"

    def _get_jss_tier(self, jss: float) -> str:
        """Get JSS tier description."""
        if jss >= 95:
            return "Elite"
        elif jss >= 90:
            return "Excellent"
        elif jss >= 85:
            return "Good"
        elif jss > 0:
            return "Average"
        else:
            return "No Score"

    def _get_portfolio_tier(self, count: int) -> str:
        """Get portfolio tier description."""
        if count >= 20:
            return "Extensive"
        elif count >= 10:
            return "Strong"
        elif count >= 5:
            return "Moderate"
        elif count >= 1:
            return "Basic"
        else:
            return "None"

    def _format_job_breakdown(self, factors: Dict) -> str:
        """Format job score breakdown for display."""
        lines = ["Job Score Breakdown:"]
        for factor_name, factor_data in factors.items():
            lines.append(f"  {factor_name.replace('_', ' ').title()}: {factor_data['score']:.1f}/100")
        return "\n".join(lines)

    def _format_talent_breakdown(self, factors: Dict) -> str:
        """Format talent score breakdown for display."""
        lines = ["Talent Score Breakdown:"]
        for factor_name, factor_data in factors.items():
            lines.append(f"  {factor_name.replace('_', ' ').title()}: {factor_data['score']:.1f}/100")
        return "\n".join(lines)

    def calculate_market_percentiles(self, jobs_df, talent_df, niche_column: str = 'niche') -> Dict:
        """
        Calculate market percentiles from data.

        Args:
            jobs_df: Jobs dataframe
            talent_df: Talent dataframe
            niche_column: Column name for niche categorization

        Returns:
            Dict with budget and rate percentiles by niche
        """
        import pandas as pd

        result = {
            'budget_percentiles': {},
            'rate_percentiles': {},
            'skill_frequencies': {}
        }

        # Budget percentiles by niche
        if niche_column in jobs_df.columns:
            for niche in jobs_df[niche_column].unique():
                niche_jobs = jobs_df[jobs_df[niche_column] == niche]
                if 'budget_num' in niche_jobs.columns:
                    result['budget_percentiles'][niche] = {
                        'p25': niche_jobs['budget_num'].quantile(0.25),
                        'p50': niche_jobs['budget_num'].quantile(0.50),
                        'p75': niche_jobs['budget_num'].quantile(0.75)
                    }

        # Rate percentiles by niche
        if niche_column in talent_df.columns:
            for niche in talent_df[niche_column].unique():
                niche_talent = talent_df[talent_df[niche_column] == niche]
                if 'rate_num' in niche_talent.columns:
                    result['rate_percentiles'][niche] = {
                        'p25': niche_talent['rate_num'].quantile(0.25),
                        'p50': niche_talent['rate_num'].quantile(0.50),
                        'p75': niche_talent['rate_num'].quantile(0.75)
                    }

        # Skill frequencies
        all_skills = []
        for skills in talent_df.get('skills', []):
            all_skills.extend(self._parse_skills(skills))

        if all_skills:
            skill_counts = Counter(all_skills)
            total = sum(skill_counts.values())
            result['skill_frequencies'] = {
                skill: count / total for skill, count in skill_counts.items()
            }

        return result


# Import pandas at module level for use in methods
try:
    import pandas as pd
except ImportError:
    pd = None
