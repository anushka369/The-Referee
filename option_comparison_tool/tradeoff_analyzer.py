"""
TradeoffAnalyzer - Implements trade-off analysis for option comparison.

This module identifies and explains trade-offs between competing factors,
providing quantification methods and explanations for decision-making.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
import math
from itertools import combinations

from .models import Option, Constraint, ConstraintType, Priority
from .weighted_scoring import WeightedScoringAnalyzer, OptionScore

logger = logging.getLogger(__name__)


@dataclass
class TradeoffAnalysis:
    """Represents a trade-off between two constraints."""
    constraint_a: str
    constraint_b: str
    correlation: float  # -1 to 1, negative indicates trade-off
    description: str
    affected_options: List[str]
    quantification: Optional[Dict[str, float]] = None


@dataclass
class OptionTradeoff:
    """Represents trade-offs for a specific option."""
    option_id: str
    option_name: str
    strengths: List[str]
    weaknesses: List[str]
    tradeoff_summary: str
    competing_factors: List[TradeoffAnalysis]


@dataclass
class TradeoffResult:
    """Complete results from trade-off analysis."""
    option_tradeoffs: List[OptionTradeoff]
    global_tradeoffs: List[TradeoffAnalysis]
    pareto_frontier: List[str]  # Option IDs on Pareto frontier
    analysis_metadata: Dict[str, Any]


class TradeoffAnalyzer:
    """
    Implements trade-off analysis for multi-criteria decision making.
    
    This analyzer identifies competing factors, explains trade-offs,
    and provides quantification methods for understanding compromises.
    """
    
    def __init__(self):
        """Initialize the trade-off analyzer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scoring_analyzer = WeightedScoringAnalyzer()
    
    def analyze_tradeoffs(
        self, 
        options: List[Option], 
        constraints: List[Constraint]
    ) -> TradeoffResult:
        """
        Perform comprehensive trade-off analysis on options against constraints.
        
        Args:
            options: List of options to analyze
            constraints: List of constraints to evaluate against
            
        Returns:
            TradeoffResult containing trade-off analysis
            
        Raises:
            ValueError: If inputs are invalid or analysis cannot be performed
        """
        self.logger.info(f"Starting trade-off analysis for {len(options)} options and {len(constraints)} constraints")
        
        # Validate inputs
        self._validate_inputs(options, constraints)
        
        # If insufficient data for trade-off analysis, return minimal result
        if len(options) < 2 or len(constraints) < 2:
            return self._create_minimal_tradeoff_result(options, constraints)
        
        # Get scoring results for analysis
        scoring_result = self.scoring_analyzer.analyze(options, constraints)
        
        # Identify global trade-offs between constraints
        global_tradeoffs = self._identify_global_tradeoffs(options, constraints, scoring_result)
        
        # Analyze trade-offs for each option
        option_tradeoffs = self._analyze_option_tradeoffs(options, constraints, scoring_result, global_tradeoffs)
        
        # Find Pareto frontier
        pareto_frontier = self._find_pareto_frontier(options, constraints, scoring_result)
        
        # Create analysis metadata
        metadata = self._create_analysis_metadata(options, constraints, global_tradeoffs, pareto_frontier)
        
        result = TradeoffResult(
            option_tradeoffs=option_tradeoffs,
            global_tradeoffs=global_tradeoffs,
            pareto_frontier=pareto_frontier,
            analysis_metadata=metadata
        )
        
        self.logger.info(f"Completed trade-off analysis. Found {len(global_tradeoffs)} global trade-offs")
        return result
    
    def _validate_inputs(self, options: List[Option], constraints: List[Constraint]) -> None:
        """
        Validate inputs for trade-off analysis.
        
        Args:
            options: List of options to validate
            constraints: List of constraints to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not options:
            raise ValueError("At least one option is required for trade-off analysis")
        
        # Validate that all options have unique names
        option_names = [opt.name for opt in options]
        if len(option_names) != len(set(option_names)):
            raise ValueError("All options must have unique names")
        
        # Validate constraints have valid weights
        for constraint in constraints:
            if not (0.0 <= constraint.weight <= 1.0):
                raise ValueError(f"Constraint '{constraint.name}' has invalid weight: {constraint.weight}")
    
    def _create_minimal_tradeoff_result(self, options: List[Option], constraints: List[Constraint]) -> TradeoffResult:
        """
        Create a minimal trade-off result when insufficient data for full analysis.
        
        Args:
            options: List of options
            constraints: List of constraints
            
        Returns:
            TradeoffResult with minimal analysis
        """
        option_tradeoffs = []
        for option in options:
            tradeoff = OptionTradeoff(
                option_id=option.id,
                option_name=option.name,
                strengths=[],
                weaknesses=[],
                tradeoff_summary="Insufficient data for trade-off analysis",
                competing_factors=[]
            )
            option_tradeoffs.append(tradeoff)
        
        metadata = {
            "analysis_type": "tradeoff_analysis",
            "option_count": len(options),
            "constraint_count": len(constraints),
            "global_tradeoff_count": 0,
            "pareto_frontier_size": len(options),
            "pareto_efficiency": 1.0,  # All options on frontier when no trade-offs
            "trade_off_intensity": 0.0,
            "most_significant_tradeoffs": [],
            "notes": "Insufficient data for comprehensive trade-off analysis"
        }
        
        return TradeoffResult(
            option_tradeoffs=option_tradeoffs,
            global_tradeoffs=[],
            pareto_frontier=[opt.id for opt in options],  # All options on frontier when no trade-offs
            analysis_metadata=metadata
        )
    
    def _identify_global_tradeoffs(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        scoring_result
    ) -> List[TradeoffAnalysis]:
        """
        Identify trade-offs between constraints across all options.
        
        Args:
            options: List of options
            constraints: List of constraints
            scoring_result: Results from weighted scoring analysis
            
        Returns:
            List of TradeoffAnalysis objects representing global trade-offs
        """
        global_tradeoffs = []
        
        # Calculate correlation matrix between constraints
        constraint_correlations = self._calculate_constraint_correlations(options, constraints, scoring_result)
        
        # Identify trade-offs (negative correlations)
        for (constraint_a, constraint_b), correlation in constraint_correlations.items():
            if correlation < -0.3:  # Threshold for significant negative correlation
                # Find options most affected by this trade-off
                affected_options = self._find_options_affected_by_tradeoff(
                    options, constraint_a, constraint_b, scoring_result
                )
                
                # Generate description
                description = self._generate_tradeoff_description(constraint_a, constraint_b, correlation)
                
                # Calculate quantification metrics
                quantification = self._quantify_tradeoff(constraint_a, constraint_b, correlation, affected_options)
                
                tradeoff = TradeoffAnalysis(
                    constraint_a=constraint_a,
                    constraint_b=constraint_b,
                    correlation=correlation,
                    description=description,
                    affected_options=affected_options,
                    quantification=quantification
                )
                global_tradeoffs.append(tradeoff)
        
        return global_tradeoffs
    
    def _calculate_constraint_correlations(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        scoring_result
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate correlations between constraint scores across options.
        
        Args:
            options: List of options
            constraints: List of constraints
            scoring_result: Results from weighted scoring analysis
            
        Returns:
            Dictionary mapping constraint pairs to correlation coefficients
        """
        correlations = {}
        
        # Get normalized scores for all options and constraints
        constraint_scores = {}
        for constraint in constraints:
            scores = []
            for option_score in scoring_result.option_scores:
                score = option_score.normalized_scores.get(constraint.name, 0.0)
                scores.append(score)
            constraint_scores[constraint.name] = scores
        
        # Calculate correlations between all constraint pairs
        for constraint_a, constraint_b in combinations(constraints, 2):
            scores_a = constraint_scores[constraint_a.name]
            scores_b = constraint_scores[constraint_b.name]
            
            correlation = self._calculate_correlation(scores_a, scores_b)
            correlations[(constraint_a.name, constraint_b.name)] = correlation
        
        return correlations
    
    def _calculate_correlation(self, scores_a: List[float], scores_b: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient between two score lists.
        
        Args:
            scores_a: First set of scores
            scores_b: Second set of scores
            
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(scores_a) != len(scores_b) or len(scores_a) < 2:
            return 0.0
        
        # Calculate means
        mean_a = sum(scores_a) / len(scores_a)
        mean_b = sum(scores_b) / len(scores_b)
        
        # Calculate correlation components
        numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(scores_a, scores_b))
        
        sum_sq_a = sum((a - mean_a) ** 2 for a in scores_a)
        sum_sq_b = sum((b - mean_b) ** 2 for b in scores_b)
        
        denominator = math.sqrt(sum_sq_a * sum_sq_b)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _find_options_affected_by_tradeoff(
        self, 
        options: List[Option], 
        constraint_a: str, 
        constraint_b: str, 
        scoring_result
    ) -> List[str]:
        """
        Find options most affected by a specific trade-off.
        
        Args:
            options: List of options
            constraint_a: First constraint in trade-off
            constraint_b: Second constraint in trade-off
            scoring_result: Results from weighted scoring analysis
            
        Returns:
            List of option names affected by this trade-off
        """
        affected_options = []
        
        for option_score in scoring_result.option_scores:
            score_a = option_score.normalized_scores.get(constraint_a, 0.0)
            score_b = option_score.normalized_scores.get(constraint_b, 0.0)
            
            # Option is affected if it has significantly different scores on the two constraints
            score_diff = abs(score_a - score_b)
            if score_diff > 0.3:  # Threshold for significant difference
                affected_options.append(option_score.option_name)
        
        return affected_options
    
    def _generate_tradeoff_description(self, constraint_a: str, constraint_b: str, correlation: float) -> str:
        """
        Generate a human-readable description of a trade-off.
        
        Args:
            constraint_a: First constraint in trade-off
            constraint_b: Second constraint in trade-off
            correlation: Correlation coefficient
            
        Returns:
            Human-readable description of the trade-off
        """
        strength = "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.5 else "weak"
        
        return (f"There is a {strength} trade-off between {constraint_a} and {constraint_b}. "
                f"Options that excel in {constraint_a} tend to perform worse in {constraint_b}, "
                f"and vice versa (correlation: {correlation:.2f}).")
    
    def _quantify_tradeoff(
        self, 
        constraint_a: str, 
        constraint_b: str, 
        correlation: float, 
        affected_options: List[str]
    ) -> Dict[str, float]:
        """
        Quantify the trade-off with numeric measures.
        
        Args:
            constraint_a: First constraint in trade-off
            constraint_b: Second constraint in trade-off
            correlation: Correlation coefficient
            affected_options: Options affected by this trade-off
            
        Returns:
            Dictionary with quantification metrics
        """
        return {
            "correlation_strength": abs(correlation),
            "affected_option_count": len(affected_options),
            "trade_off_intensity": abs(correlation) * len(affected_options),
            "significance_score": min(abs(correlation) * 2, 1.0)  # 0-1 scale
        }
    
    def _analyze_option_tradeoffs(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        scoring_result, 
        global_tradeoffs: List[TradeoffAnalysis]
    ) -> List[OptionTradeoff]:
        """
        Analyze trade-offs for each individual option.
        
        Args:
            options: List of options
            constraints: List of constraints
            scoring_result: Results from weighted scoring analysis
            global_tradeoffs: Global trade-offs identified
            
        Returns:
            List of OptionTradeoff objects
        """
        option_tradeoffs = []
        
        for option_score in scoring_result.option_scores:
            # Identify strengths and weaknesses
            strengths, weaknesses = self._identify_option_strengths_weaknesses(
                option_score, constraints
            )
            
            # Find relevant global trade-offs for this option
            relevant_tradeoffs = [
                tradeoff for tradeoff in global_tradeoffs
                if option_score.option_name in tradeoff.affected_options
            ]
            
            # Generate trade-off summary
            summary = self._generate_option_tradeoff_summary(
                option_score, strengths, weaknesses, relevant_tradeoffs
            )
            
            option_tradeoff = OptionTradeoff(
                option_id=option_score.option_id,
                option_name=option_score.option_name,
                strengths=strengths,
                weaknesses=weaknesses,
                tradeoff_summary=summary,
                competing_factors=relevant_tradeoffs
            )
            option_tradeoffs.append(option_tradeoff)
        
        return option_tradeoffs
    
    def _identify_option_strengths_weaknesses(
        self, 
        option_score: OptionScore, 
        constraints: List[Constraint]
    ) -> Tuple[List[str], List[str]]:
        """
        Identify strengths and weaknesses for a specific option.
        
        Args:
            option_score: Scoring results for the option
            constraints: List of constraints
            
        Returns:
            Tuple of (strengths, weaknesses) as lists of constraint names
        """
        strengths = []
        weaknesses = []
        
        # Calculate thresholds based on score distribution
        scores = list(option_score.normalized_scores.values())
        if not scores:
            return strengths, weaknesses
        
        avg_score = sum(scores) / len(scores)
        
        # Identify strengths (above average) and weaknesses (below average)
        for constraint in constraints:
            score = option_score.normalized_scores.get(constraint.name, 0.0)
            
            if score > avg_score + 0.2:  # Significantly above average
                strengths.append(constraint.name)
            elif score < avg_score - 0.2:  # Significantly below average
                weaknesses.append(constraint.name)
        
        return strengths, weaknesses
    
    def _generate_option_tradeoff_summary(
        self, 
        option_score: OptionScore, 
        strengths: List[str], 
        weaknesses: List[str], 
        relevant_tradeoffs: List[TradeoffAnalysis]
    ) -> str:
        """
        Generate a summary of trade-offs for a specific option.
        
        Args:
            option_score: Scoring results for the option
            strengths: List of strength areas
            weaknesses: List of weakness areas
            relevant_tradeoffs: Relevant global trade-offs
            
        Returns:
            Human-readable summary of option trade-offs
        """
        if not strengths and not weaknesses:
            return f"{option_score.option_name} shows balanced performance across all criteria."
        
        summary_parts = []
        
        if strengths:
            summary_parts.append(f"{option_score.option_name} excels in {', '.join(strengths)}")
        
        if weaknesses:
            summary_parts.append(f"but sacrifices performance in {', '.join(weaknesses)}")
        
        if relevant_tradeoffs:
            tradeoff_count = len(relevant_tradeoffs)
            summary_parts.append(f"This option is affected by {tradeoff_count} significant trade-off{'s' if tradeoff_count > 1 else ''}")
        
        return ". ".join(summary_parts) + "."
    
    def _find_pareto_frontier(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        scoring_result
    ) -> List[str]:
        """
        Find options on the Pareto frontier (non-dominated solutions).
        
        Args:
            options: List of options
            constraints: List of constraints
            scoring_result: Results from weighted scoring analysis
            
        Returns:
            List of option IDs on the Pareto frontier
        """
        if len(constraints) < 2:
            # With fewer than 2 constraints, all options are on the frontier
            return [opt.id for opt in options]
        
        pareto_options = []
        
        for option_score in scoring_result.option_scores:
            is_dominated = False
            
            # Check if this option is dominated by any other option
            for other_score in scoring_result.option_scores:
                if other_score.option_id == option_score.option_id:
                    continue
                
                if self._dominates(other_score, option_score, constraints):
                    is_dominated = True
                    break
            
            if not is_dominated:
                pareto_options.append(option_score.option_id)
        
        return pareto_options
    
    def _dominates(self, option_a: OptionScore, option_b: OptionScore, constraints: List[Constraint]) -> bool:
        """
        Check if option A dominates option B (Pareto dominance).
        
        Args:
            option_a: First option score
            option_b: Second option score
            constraints: List of constraints
            
        Returns:
            True if option A dominates option B
        """
        # A dominates B if A is at least as good as B in all criteria
        # and strictly better in at least one criterion
        
        at_least_as_good_in_all = True
        strictly_better_in_one = False
        
        for constraint in constraints:
            score_a = option_a.normalized_scores.get(constraint.name, 0.0)
            score_b = option_b.normalized_scores.get(constraint.name, 0.0)
            
            if score_a < score_b:
                at_least_as_good_in_all = False
                break
            elif score_a > score_b:
                strictly_better_in_one = True
        
        return at_least_as_good_in_all and strictly_better_in_one
    
    def _create_analysis_metadata(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        global_tradeoffs: List[TradeoffAnalysis], 
        pareto_frontier: List[str]
    ) -> Dict[str, Any]:
        """Create metadata about the trade-off analysis."""
        return {
            "analysis_type": "tradeoff_analysis",
            "option_count": len(options),
            "constraint_count": len(constraints),
            "global_tradeoff_count": len(global_tradeoffs),
            "pareto_frontier_size": len(pareto_frontier),
            "pareto_efficiency": len(pareto_frontier) / len(options) if options else 0,
            "trade_off_intensity": sum(t.quantification.get("trade_off_intensity", 0) for t in global_tradeoffs),
            "most_significant_tradeoffs": [
                {"constraints": (t.constraint_a, t.constraint_b), "correlation": t.correlation}
                for t in sorted(global_tradeoffs, key=lambda x: abs(x.correlation), reverse=True)[:3]
            ]
        }