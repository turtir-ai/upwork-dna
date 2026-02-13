# Market Gap Calculator
# Statistical testing for market demand vs supply gaps

from scipy import stats
import numpy as np
from typing import List, Dict, Any


class MarketGapCalculator:
    """
    Statistical market gap calculator with significance testing.

    Calculates demand vs supply gaps with:
    - t-test for statistical significance
    - Cohen's d for effect size
    - Confidence intervals for gap ratios
    """

    def __init__(self, min_sample_size: int = 5, alpha: float = 0.05):
        """
        Initialize the calculator.

        Args:
            min_sample_size: Minimum samples required for valid test
            alpha: Significance threshold (default: 0.05)
        """
        self.min_sample_size = min_sample_size
        self.alpha = alpha

    def calculate_gap(
        self,
        demand_data: List[float],
        supply_data: List[float],
        confidence: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculate market gap with statistical testing.

        Args:
            demand_data: List of demand values (e.g., job counts per skill)
            supply_data: List of supply values (e.g., talent counts per skill)
            confidence: Confidence level for interval (default: 0.95)

        Returns:
            Dictionary containing:
                - gap_ratio: Demand / Supply ratio
                - demand_mean: Mean demand value
                - supply_mean: Mean supply value
                - p_value: Two-tailed t-test p-value
                - confidence_interval: (lower, upper) bounds for gap ratio
                - is_significant: True if p < alpha and sufficient samples
                - effect_size: Cohen's d (standardized effect size)
                - confidence_level: The confidence level used
        """
        demand_arr = np.array(demand_data, dtype=float)
        supply_arr = np.array(supply_data, dtype=float)

        demand_mean = float(np.mean(demand_arr)) if len(demand_arr) > 0 else 0.0
        supply_mean = float(np.mean(supply_arr)) if len(supply_arr) > 0 else 0.0

        # Calculate gap ratio with edge case handling
        if supply_mean > 0:
            gap_ratio = demand_mean / supply_mean
        elif demand_mean > 0:
            gap_ratio = float('inf')  # Infinite gap (demand with no supply)
        else:
            gap_ratio = 1.0  # No demand, no supply

        # Statistical significance testing
        p_value = 1.0
        is_significant = False
        effect_size = 0.0
        confidence_interval = (0.0, float('inf'))

        # Only perform statistical tests with sufficient data
        if len(demand_arr) >= self.min_sample_size and len(supply_arr) >= self.min_sample_size:
            # Two-sample t-test (independent samples, unequal variance)
            t_stat, p_value = stats.ttest_ind(demand_arr, supply_arr, equal_var=False)

            # Calculate Cohen's d (effect size)
            pooled_std = np.sqrt(
                ((len(demand_arr) - 1) * np.var(demand_arr, ddof=1) +
                 (len(supply_arr) - 1) * np.var(supply_arr, ddof=1)) /
                (len(demand_arr) + len(supply_arr) - 2)
            )
            if pooled_std > 0:
                effect_size = abs(demand_mean - supply_mean) / pooled_std

            # Confidence interval for the difference in means
            se_diff = np.sqrt(
                np.var(demand_arr, ddof=1) / len(demand_arr) +
                np.var(supply_arr, ddof=1) / len(supply_arr)
            )
            if se_diff > 0:
                t_critical = stats.t.ppf(
                    (1 + confidence) / 2,
                    df=min(len(demand_arr), len(supply_arr)) - 1
                )
                diff = demand_mean - supply_mean
                ci_lower = diff - t_critical * se_diff
                ci_upper = diff + t_critical * se_diff

                # Convert to gap ratio confidence interval
                if supply_mean > 0:
                    ci_lower_ratio = (demand_mean - t_critical * se_diff) / supply_mean
                    ci_upper_ratio = (demand_mean + t_critical * se_diff) / supply_mean
                    confidence_interval = (max(0, ci_lower_ratio), ci_upper_ratio)

            is_significant = p_value < self.alpha

        return {
            'gap_ratio': gap_ratio,
            'demand_mean': demand_mean,
            'supply_mean': supply_mean,
            'p_value': float(p_value) if not np.isnan(p_value) else 1.0,
            'confidence_interval': confidence_interval,
            'is_significant': is_significant,
            'effect_size': float(effect_size) if not np.isnan(effect_size) else 0.0,
            'confidence_level': confidence,
            'demand_count': len(demand_arr),
            'supply_count': len(supply_arr)
        }

    def calculate_multiple_gaps(
        self,
        skill_data: Dict[str, Dict[str, List[float]]],
        confidence: float = 0.95
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate gaps for multiple skills.

        Args:
            skill_data: Dict mapping skill names to {'demand': [...], 'supply': [...]}
            confidence: Confidence level for intervals

        Returns:
            Dict mapping skill names to gap analysis results
        """
        results = {}

        for skill, data in skill_data.items():
            demand = data.get('demand', [])
            supply = data.get('supply', [])

            result = self.calculate_gap(demand, supply, confidence)
            results[skill] = result

        return results

    def filter_significant_gaps(
        self,
        gap_results: Dict[str, Dict[str, Any]],
        min_effect_size: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Filter gaps by statistical significance and effect size.

        Args:
            gap_results: Results from calculate_multiple_gaps()
            min_effect_size: Minimum Cohen's d (small=0.2, medium=0.5, large=0.8)

        Returns:
            List of significant gaps sorted by gap_ratio descending
        """
        significant = []

        for skill, result in gap_results.items():
            if result.get('is_significant', False) and result.get('effect_size', 0) >= min_effect_size:
                significant.append({
                    'skill': skill,
                    **result
                })

        # Sort by gap ratio (descending)
        significant.sort(key=lambda x: x.get('gap_ratio', 0), reverse=True)

        return significant
