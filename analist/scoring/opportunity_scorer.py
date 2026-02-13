"""
Keyword Opportunity Scoring Module

Implements composite scoring for keyword opportunities based on:
1. Demand Score (0-100)
2. Supply Gap Score (0-100)
3. Budget Score (0-100)
4. Trend Score (0-100)
5. Competition Score (0-100, lower competition = higher score)
6. Client Quality Score (0-100)

Returns composite opportunity score (0-100) with factor breakdown
and priority classification (HIGH/MEDIUM/LOW).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import statistics


@dataclass
class OpportunityScore:
    """Container for opportunity scoring results."""
    keyword: str
    opportunity_score: float  # Composite 0-100
    factor_breakdown: Dict[str, float]  # Individual factor scores
    recommended_priority: str  # HIGH/MEDIUM/LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "keyword": self.keyword,
            "opportunity_score": round(self.opportunity_score, 2),
            "factor_breakdown": {k: round(v, 2) for k, v in self.factor_breakdown.items()},
            "recommended_priority": self.recommended_priority
        }


class KeywordOpportunityScorer:
    """
    Scores keyword opportunities using composite multi-factor analysis.

    Weights (configurable):
    - Demand: 25% (market demand for the skill)
    - Supply Gap: 20% (freelancer supply vs demand)
    - Budget: 20% (average project budget)
    - Trend: 15% (growth trajectory)
    - Competition: 10% (inverse - less competition is better)
    - Client Quality: 10% (client reliability and ratings)
    """

    # Default weights for composite scoring (sum to 1.0)
    DEFAULT_WEIGHTS = {
        "demand": 0.25,
        "supply_gap": 0.20,
        "budget": 0.20,
        "trend": 0.15,
        "competition": 0.10,  # Inverted: lower competition = higher score
        "client_quality": 0.10
    }

    # Priority thresholds
    PRIORITY_HIGH_THRESHOLD = 70.0
    PRIORITY_MEDIUM_THRESHOLD = 50.0

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with optional custom weights.

        Args:
            weights: Custom factor weights dict. Defaults to DEFAULT_WEIGHTS.
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validate that weights sum to 1.0 and are positive."""
        if not self.weights:
            raise ValueError("Weights cannot be empty")

        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        for name, weight in self.weights.items():
            if weight < 0:
                raise ValueError(f"Weight '{name}' cannot be negative: {weight}")

    def score_keyword_opportunity(
        self,
        keyword: str,
        market_data: Dict[str, Any]
    ) -> OpportunityScore:
        """
        Calculate composite opportunity score for a keyword.

        Args:
            keyword: The keyword/skill to score
            market_data: Dictionary containing market metrics:
                - demand_score: float (0-100) - Market demand level
                - supply_gap_score: float (0-100) - Supply vs demand gap
                - budget_score: float (0-100) - Average budget level
                - trend_score: float (0-100) - Growth trend
                - competition_score: float (0-100) - Competition level (inverted)
                - client_quality_score: float (0-100) - Client reliability

                Alternatively, raw metrics can be provided:
                - job_postings: int - Number of active jobs
                - freelancer_count: int - Number of competing freelancers
                - avg_budget: float - Average project budget
                - budget_currency: str - Currency code (default: USD)
                - trend_growth_rate: float - Percentage growth (e.g., 15.5 for +15.5%)
                - avg_client_rating: float - Average client rating (1-5)
                - client_payment_verified_rate: float - % payment verified (0-100)

        Returns:
            OpportunityScore with composite score, factor breakdown, and priority

        Example:
            >>> scorer = KeywordOpportunityScorer()
            >>> market_data = {
            ...     "demand_score": 85,
            ...     "supply_gap_score": 70,
            ...     "budget_score": 60,
            ...     "trend_score": 75,
            ...     "competition_score": 40,  # Lower is better
            ...     "client_quality_score": 80
            ... }
            >>> result = scorer.score_keyword_opportunity("Python", market_data)
            >>> print(result.opportunity_score)
            72.5
        """
        # Calculate individual factor scores
        factor_scores = self._calculate_factor_scores(market_data)

        # Calculate weighted composite score
        opportunity_score = self._calculate_composite_score(factor_scores)

        # Determine priority classification
        priority = self._classify_priority(opportunity_score)

        return OpportunityScore(
            keyword=keyword,
            opportunity_score=opportunity_score,
            factor_breakdown=factor_scores,
            recommended_priority=priority
        )

    def _calculate_factor_scores(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate individual factor scores from market data.

        Handles both pre-calculated scores (0-100) and raw metrics.
        """
        factor_scores = {}

        # Demand Score
        if "demand_score" in market_data:
            factor_scores["demand"] = self._normalize_score(market_data["demand_score"])
        elif "job_postings" in market_data:
            # Normalize: 1000+ jobs = 100, 0 jobs = 0
            factor_scores["demand"] = min(100, market_data["job_postings"] / 10)
        else:
            factor_scores["demand"] = 50.0  # Default neutral

        # Supply Gap Score
        if "supply_gap_score" in market_data:
            factor_scores["supply_gap"] = self._normalize_score(market_data["supply_gap_score"])
        elif "freelancer_count" in market_data and "job_postings" in market_data:
            # Calculate ratio: fewer freelancers per job = higher gap score
            jobs = market_data["job_postings"]
            freelancers = market_data["freelancer_count"]
            if freelancers > 0:
                ratio = jobs / freelancers
                # Ratio 1.0+ = 100, ratio 0.1 = 10
                factor_scores["supply_gap"] = min(100, ratio * 100)
            else:
                factor_scores["supply_gap"] = 100.0
        else:
            factor_scores["supply_gap"] = 50.0

        # Budget Score
        if "budget_score" in market_data:
            factor_scores["budget"] = self._normalize_score(market_data["budget_score"])
        elif "avg_budget" in market_data:
            # Normalize: $1000+ = 100, $0 = 0
            budget = market_data.get("avg_budget", 0)
            factor_scores["budget"] = min(100, budget / 10)
        else:
            factor_scores["budget"] = 50.0

        # Trend Score
        if "trend_score" in market_data:
            factor_scores["trend"] = self._normalize_score(market_data["trend_score"])
        elif "trend_growth_rate" in market_data:
            # Normalize: +50% growth = 100, -20% = 0
            growth_rate = market_data["trend_growth_rate"]
            factor_scores["trend"] = max(0, min(100, (growth_rate + 20) * 100 / 70))
        else:
            factor_scores["trend"] = 50.0

        # Competition Score (inverse - lower competition = higher score)
        if "competition_score" in market_data:
            # Pre-calculated score should already be inverted
            factor_scores["competition"] = self._normalize_score(market_data["competition_score"])
        elif "freelancer_count" in market_data:
            # Invert: fewer freelancers = higher score
            # 0 freelancers = 100, 10000+ freelancers = 0
            freelancers = market_data["freelancer_count"]
            factor_scores["competition"] = max(0, 100 - (freelancers / 100))
        else:
            factor_scores["competition"] = 50.0

        # Client Quality Score
        if "client_quality_score" in market_data:
            factor_scores["client_quality"] = self._normalize_score(market_data["client_quality_score"])
        elif "avg_client_rating" in market_data:
            # Normalize rating: 5.0 = 100, 1.0 = 0
            rating = market_data.get("avg_client_rating", 3.0)
            factor_scores["client_quality"] = max(0, min(100, (rating - 1) * 25))

            # Apply payment verification bonus
            if "client_payment_verified_rate" in market_data:
                verified_bonus = market_data["client_payment_verified_rate"] * 0.2
                factor_scores["client_quality"] = min(100, factor_scores["client_quality"] + verified_bonus)
        else:
            factor_scores["client_quality"] = 50.0

        return factor_scores

    def _normalize_score(self, score: float) -> float:
        """Ensure score is within 0-100 range."""
        return max(0.0, min(100.0, float(score)))

    def _calculate_composite_score(self, factor_scores: Dict[str, float]) -> float:
        """
        Calculate weighted composite score from individual factors.

        Only includes factors that have defined weights.
        """
        weighted_sum = 0.0
        total_weight = 0.0

        for factor, score in factor_scores.items():
            if factor in self.weights:
                weight = self.weights[factor]
                weighted_sum += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50.0  # Default neutral score

        # Normalize to actual weight total in case of partial data
        return weighted_sum / total_weight

    def _classify_priority(self, score: float) -> str:
        """
        Classify opportunity score into priority level.

        Args:
            score: Composite opportunity score (0-100)

        Returns:
            Priority level: "HIGH", "MEDIUM", or "LOW"
        """
        if score >= self.PRIORITY_HIGH_THRESHOLD:
            return "HIGH"
        elif score >= self.PRIORITY_MEDIUM_THRESHOLD:
            return "MEDIUM"
        else:
            return "LOW"

    def score_batch_keywords(
        self,
        keywords_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, OpportunityScore]:
        """
        Score multiple keywords in batch.

        Args:
            keywords_data: Dict mapping keyword -> market_data

        Returns:
            Dict mapping keyword -> OpportunityScore, sorted by score descending
        """
        results = {}
        for keyword, market_data in keywords_data.items():
            results[keyword] = self.score_keyword_opportunity(keyword, market_data)

        # Sort by opportunity score descending
        return dict(sorted(results.items(), key=lambda x: x[1].opportunity_score, reverse=True))

    def get_top_opportunities(
        self,
        scored_keywords: Dict[str, OpportunityScore],
        top_n: int = 10,
        min_priority: Optional[str] = None
    ) -> list[OpportunityScore]:
        """
        Get top N opportunities from scored keywords.

        Args:
            scored_keywords: Dict of keyword -> OpportunityScore
            top_n: Maximum number of results to return
            min_priority: Minimum priority level (HIGH/MEDIUM/LOW)

        Returns:
            List of top OpportunityScore objects
        """
        priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_order = priority_order.get(min_priority, 0) if min_priority else 0

        filtered = [
            score for score in scored_keywords.values()
            if priority_order.get(score.recommended_priority, 0) >= min_order
        ]

        # Sort by score descending, then by priority
        sorted_results = sorted(
            filtered,
            key=lambda x: (x.opportunity_score, priority_order.get(x.recommended_priority, 0)),
            reverse=True
        )

        return sorted_results[:top_n]

    @staticmethod
    def calculate_supply_gap(job_postings: int, freelancer_count: int) -> float:
        """
        Calculate supply gap ratio.

        Higher ratio = more opportunity (more jobs per freelancer).

        Args:
            job_postings: Number of active job postings
            freelancer_count: Number of competing freelancers

        Returns:
            Supply gap ratio (jobs per freelancer)
        """
        if freelancer_count == 0:
            return float(job_postings) if job_postings > 0 else 0.0
        return round(job_postings / freelancer_count, 4)


# Convenience function for quick scoring
def score_opportunity(
    keyword: str,
    demand_score: float = 50.0,
    supply_gap_score: float = 50.0,
    budget_score: float = 50.0,
    trend_score: float = 50.0,
    competition_score: float = 50.0,
    client_quality_score: float = 50.0,
    weights: Optional[Dict[str, float]] = None
) -> OpportunityScore:
    """
    Quick convenience function to score a single keyword opportunity.

    Args:
        keyword: The keyword/skill to score
        demand_score: Market demand score (0-100)
        supply_gap_score: Supply vs demand gap score (0-100)
        budget_score: Average budget level score (0-100)
        trend_score: Growth trend score (0-100)
        competition_score: Competition level score, inverted (0-100)
        client_quality_score: Client reliability score (0-100)
        weights: Optional custom weights dict

    Returns:
        OpportunityScore object
    """
    scorer = KeywordOpportunityScorer(weights=weights)
    market_data = {
        "demand_score": demand_score,
        "supply_gap_score": supply_gap_score,
        "budget_score": budget_score,
        "trend_score": trend_score,
        "competition_score": competition_score,
        "client_quality_score": client_quality_score
    }
    return scorer.score_keyword_opportunity(keyword, market_data)


if __name__ == "__main__":
    # Example usage and demonstration
    import json

    print("=" * 60)
    print("Keyword Opportunity Scorer - Demonstration")
    print("=" * 60)

    # Example 1: Using pre-calculated scores
    print("\n1. Example with pre-calculated scores:")
    market_data = {
        "demand_score": 85,      # High demand
        "supply_gap_score": 70,  # Good supply gap
        "budget_score": 60,      # Moderate budget
        "trend_score": 75,       # Strong growth
        "competition_score": 40, # Lower competition (good)
        "client_quality_score": 80 # High quality clients
    }

    result = score_opportunity("Python Development", **market_data)
    print(f"\nKeyword: {result.keyword}")
    print(f"Opportunity Score: {result.opportunity_score:.1f}/100")
    print(f"Priority: {result.recommended_priority}")
    print("Factor Breakdown:")
    for factor, score in result.factor_breakdown.items():
        print(f"  - {factor}: {score:.1f}")

    # Example 2: Using raw metrics
    print("\n2. Example with raw market metrics:")
    raw_market_data = {
        "job_postings": 850,
        "freelancer_count": 1200,
        "avg_budget": 750,
        "trend_growth_rate": 25.5,
        "avg_client_rating": 4.2,
        "client_payment_verified_rate": 85
    }

    scorer = KeywordOpportunityScorer()
    result = scorer.score_keyword_opportunity("React Native", raw_market_data)
    print(f"\nKeyword: {result.keyword}")
    print(f"Opportunity Score: {result.opportunity_score:.1f}/100")
    print(f"Priority: {result.recommended_priority}")
    print("\nRaw Metrics:")
    print(f"  - Job Postings: {raw_market_data['job_postings']}")
    print(f"  - Freelancers: {raw_market_data['freelancer_count']}")
    print(f"  - Supply Gap: {scorer.calculate_supply_gap(raw_market_data['job_postings'], raw_market_data['freelancer_count']):.2f} jobs/freelancer")

    # Example 3: Batch scoring
    print("\n3. Batch scoring multiple keywords:")
    batch_data = {
        "Machine Learning": {"demand_score": 95, "supply_gap_score": 60, "budget_score": 85, "trend_score": 90, "competition_score": 30, "client_quality_score": 85},
        "WordPress": {"demand_score": 70, "supply_gap_score": 40, "budget_score": 45, "trend_score": 50, "competition_score": 80, "client_quality_score": 60},
        "Blockchain": {"demand_score": 65, "supply_gap_score": 75, "budget_score": 90, "trend_score": 55, "competition_score": 35, "client_quality_score": 70},
    }

    batch_results = scorer.score_batch_keywords(batch_data)
    print("\nRanked Opportunities:")
    for i, (keyword, score) in enumerate(batch_results.items(), 1):
        print(f"{i}. {keyword}: {score.opportunity_score:.1f}/100 ({score.recommended_priority})")

    # Example 4: Get top HIGH priority opportunities
    print("\n4. Top HIGH priority opportunities:")
    top_high = scorer.get_top_opportunities(batch_results, top_n=5, min_priority="HIGH")
    for i, score in enumerate(top_high, 1):
        print(f"{i}. {score.keyword}: {score.opportunity_score:.1f}/100")

    print("\n" + "=" * 60)
