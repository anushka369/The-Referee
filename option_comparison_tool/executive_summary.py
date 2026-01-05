"""
ExecutiveSummaryGenerator - Generates executive summaries with recommendations and reasoning.

This module provides recommendation logic with reasoning and tie-breaking explanation
system according to requirements 4.4, 5.2, 5.3.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import Option, Constraint, Priority
from .weighted_scoring import OptionScore, ScoringResult
from .tradeoff_analyzer import TradeoffResult, OptionTradeoff

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of recommendations that can be made."""
    CLEAR_WINNER = "clear_winner"
    CONDITIONAL = "conditional"
    TIED = "tied"
    CONTEXT_DEPENDENT = "context_dependent"


@dataclass
class Recommendation:
    """Represents a recommendation for an option."""
    option_id: str
    option_name: str
    rank: int
    recommendation_type: RecommendationType
    confidence: float  # 0-1 scale
    reasoning: str
    best_for_scenarios: List[str]
    key_advantages: List[str]
    key_disadvantages: List[str]


@dataclass
class TieBreakingExplanation:
    """Explains how ties were broken between similar options."""
    tied_options: List[str]
    tie_breaking_factors: List[str]
    explanation: str
    margin_of_difference: float


@dataclass
class ExecutiveSummary:
    """Complete executive summary with recommendations and explanations."""
    top_recommendation: Recommendation
    all_recommendations: List[Recommendation]
    tie_breaking_explanations: List[TieBreakingExplanation]
    decision_factors: Dict[str, Any]
    summary_text: str
    confidence_level: str


class ExecutiveSummaryGenerator:
    """
    Generates executive summaries with contextual recommendations and reasoning.
    
    This generator provides recommendation logic with reasoning and tie-breaking
    explanation system according to requirements 4.4, 5.2, 5.3.
    """
    
    def __init__(self):
        """Initialize the executive summary generator."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_summary(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> ExecutiveSummary:
        """
        Generate a comprehensive executive summary with recommendations.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints used in comparison
            
        Returns:
            ExecutiveSummary containing recommendations and explanations
            
        Raises:
            ValueError: If inputs are invalid or summary cannot be generated
        """
        self.logger.info(f"Generating executive summary for {len(scoring_result.option_scores)} options")
        
        # Validate inputs
        self._validate_inputs(scoring_result, tradeoff_result, constraints)
        
        # Generate recommendations for all options
        all_recommendations = self._generate_recommendations(
            scoring_result, tradeoff_result, constraints
        )
        
        # Identify tie-breaking explanations
        tie_breaking_explanations = self._identify_tie_breaking_explanations(
            scoring_result, constraints
        )
        
        # Determine decision factors
        decision_factors = self._analyze_decision_factors(
            scoring_result, tradeoff_result, constraints
        )
        
        # Generate summary text
        summary_text = self._generate_summary_text(
            all_recommendations, tie_breaking_explanations, decision_factors
        )
        
        # Determine overall confidence level
        confidence_level = self._determine_confidence_level(
            all_recommendations, tie_breaking_explanations, decision_factors
        )
        
        summary = ExecutiveSummary(
            top_recommendation=all_recommendations[0],
            all_recommendations=all_recommendations,
            tie_breaking_explanations=tie_breaking_explanations,
            decision_factors=decision_factors,
            summary_text=summary_text,
            confidence_level=confidence_level
        )
        
        self.logger.info(f"Generated executive summary recommending: {summary.top_recommendation.option_name}")
        return summary
    
    def _validate_inputs(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> None:
        """
        Validate inputs for executive summary generation.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Raises:
            ValueError: If validation fails
        """
        if not scoring_result or not scoring_result.option_scores:
            raise ValueError("Scoring result is required and must contain option scores")
        
        if not tradeoff_result:
            raise ValueError("Trade-off result is required")
        
        # Constraints can be empty, but if provided should be valid
        for constraint in constraints:
            if not constraint.name:
                raise ValueError("All constraints must have names")
    
    def _generate_recommendations(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> List[Recommendation]:
        """
        Generate recommendations for all options with reasoning.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            List of Recommendation objects ordered by rank
        """
        recommendations = []
        
        for option_score in scoring_result.option_scores:
            # Find corresponding trade-off analysis
            option_tradeoff = next(
                (ot for ot in tradeoff_result.option_tradeoffs if ot.option_id == option_score.option_id),
                None
            )
            
            # Determine recommendation type
            recommendation_type = self._determine_recommendation_type(
                option_score, scoring_result.option_scores
            )
            
            # Calculate confidence
            confidence = self._calculate_recommendation_confidence(
                option_score, scoring_result.option_scores, constraints
            )
            
            # Generate reasoning
            reasoning = self._generate_recommendation_reasoning(
                option_score, option_tradeoff, constraints, recommendation_type
            )
            
            # Identify best-for scenarios
            best_for_scenarios = self._identify_best_for_scenarios(
                option_score, constraints
            )
            
            # Extract key advantages and disadvantages
            key_advantages = (option_tradeoff.strengths[:3] if option_tradeoff else [])
            key_disadvantages = (option_tradeoff.weaknesses[:3] if option_tradeoff else [])
            
            recommendation = Recommendation(
                option_id=option_score.option_id,
                option_name=option_score.option_name,
                rank=option_score.rank,
                recommendation_type=recommendation_type,
                confidence=confidence,
                reasoning=reasoning,
                best_for_scenarios=best_for_scenarios,
                key_advantages=key_advantages,
                key_disadvantages=key_disadvantages
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _determine_recommendation_type(
        self,
        option_score: OptionScore,
        all_scores: List[OptionScore]
    ) -> RecommendationType:
        """
        Determine the type of recommendation for an option.
        
        Args:
            option_score: Score for the option being evaluated
            all_scores: Scores for all options
            
        Returns:
            RecommendationType indicating the nature of the recommendation
        """
        if option_score.rank == 1:
            # Check if it's a clear winner or tied
            second_best_score = min(
                (score.total_score for score in all_scores if score.rank > 1),
                default=0
            )
            
            score_gap = option_score.total_score - second_best_score
            
            if score_gap > 0.2:  # Significant gap
                return RecommendationType.CLEAR_WINNER
            elif score_gap > 0.05:  # Moderate gap
                return RecommendationType.CONDITIONAL
            else:  # Very close
                return RecommendationType.TIED
        else:
            # Not the top option - context dependent
            return RecommendationType.CONTEXT_DEPENDENT
    
    def _calculate_recommendation_confidence(
        self,
        option_score: OptionScore,
        all_scores: List[OptionScore],
        constraints: List[Constraint]
    ) -> float:
        """
        Calculate confidence level for a recommendation.
        
        Args:
            option_score: Score for the option being evaluated
            all_scores: Scores for all options
            constraints: List of constraints
            
        Returns:
            Confidence level between 0 and 1
        """
        # Base confidence on rank and score gap
        if option_score.rank == 1:
            # Top option - confidence based on gap to second place
            second_best_score = min(
                (score.total_score for score in all_scores if score.rank > 1),
                default=0
            )
            score_gap = option_score.total_score - second_best_score
            base_confidence = min(0.9, 0.5 + score_gap)
        else:
            # Lower ranked options have lower base confidence
            base_confidence = max(0.1, 0.8 - (option_score.rank - 1) * 0.15)
        
        # Adjust based on constraint coverage
        constraint_coverage = len(option_score.normalized_scores) / max(len(constraints), 1)
        coverage_adjustment = constraint_coverage * 0.2
        
        # Adjust based on score consistency (lower variance = higher confidence)
        if option_score.normalized_scores:
            scores = list(option_score.normalized_scores.values())
            mean_score = sum(scores) / len(scores)
            variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            consistency_adjustment = max(-0.2, -variance * 0.5)
        else:
            consistency_adjustment = -0.2
        
        final_confidence = max(0.0, min(1.0, base_confidence + coverage_adjustment + consistency_adjustment))
        return round(final_confidence, 2)
    
    def _generate_recommendation_reasoning(
        self,
        option_score: OptionScore,
        option_tradeoff: Optional[OptionTradeoff],
        constraints: List[Constraint],
        recommendation_type: RecommendationType
    ) -> str:
        """
        Generate detailed reasoning for a recommendation.
        
        Args:
            option_score: Score for the option
            option_tradeoff: Trade-off analysis for the option
            constraints: List of constraints
            recommendation_type: Type of recommendation
            
        Returns:
            Detailed reasoning text
        """
        reasoning_parts = []
        
        # Start with rank and score
        reasoning_parts.append(
            f"{option_score.option_name} ranks #{option_score.rank} "
            f"with a total score of {option_score.total_score:.2f}"
        )
        
        # Add recommendation type context
        if recommendation_type == RecommendationType.CLEAR_WINNER:
            reasoning_parts.append("This option is the clear winner with a significant advantage")
        elif recommendation_type == RecommendationType.CONDITIONAL:
            reasoning_parts.append("This option leads but the margin is moderate")
        elif recommendation_type == RecommendationType.TIED:
            reasoning_parts.append("This option is tied or very close with other top options")
        else:
            reasoning_parts.append("This option may be suitable for specific contexts")
        
        # Add strengths and weaknesses
        if option_tradeoff:
            if option_tradeoff.strengths:
                reasoning_parts.append(
                    f"Key strengths include: {', '.join(option_tradeoff.strengths[:3])}"
                )
            
            if option_tradeoff.weaknesses:
                reasoning_parts.append(
                    f"Areas for consideration: {', '.join(option_tradeoff.weaknesses[:3])}"
                )
            
            # Add trade-off insight
            if option_tradeoff.competing_factors:
                reasoning_parts.append(
                    f"This option involves {len(option_tradeoff.competing_factors)} "
                    f"significant trade-off{'s' if len(option_tradeoff.competing_factors) > 1 else ''}"
                )
        
        # Add constraint-specific insights
        high_scoring_constraints = [
            constraint.name for constraint in constraints
            if option_score.normalized_scores.get(constraint.name, 0) > 0.7
        ]
        
        if high_scoring_constraints:
            reasoning_parts.append(
                f"Particularly strong in: {', '.join(high_scoring_constraints[:2])}"
            )
        
        return ". ".join(reasoning_parts) + "."
    
    def _identify_best_for_scenarios(
        self,
        option_score: OptionScore,
        constraints: List[Constraint]
    ) -> List[str]:
        """
        Identify scenarios where this option would be the best choice.
        
        Args:
            option_score: Score for the option
            constraints: List of constraints
            
        Returns:
            List of scenario descriptions
        """
        scenarios = []
        
        # Find constraints where this option excels
        for constraint in constraints:
            score = option_score.normalized_scores.get(constraint.name, 0)
            
            if score > 0.8:  # Excellent performance
                if constraint.priority == Priority.REQUIRED:
                    scenarios.append(f"When {constraint.name.lower()} is absolutely critical")
                elif constraint.priority == Priority.PREFERRED:
                    scenarios.append(f"When {constraint.name.lower()} is a top priority")
                else:
                    scenarios.append(f"When {constraint.name.lower()} provides significant value")
        
        # Add general scenarios based on rank
        if option_score.rank == 1:
            scenarios.append("General use cases requiring balanced performance")
        elif option_score.rank <= 3:
            scenarios.append("Specific use cases matching its strengths")
        
        # Limit to top 3 scenarios
        return scenarios[:3]
    
    def _identify_tie_breaking_explanations(
        self,
        scoring_result: ScoringResult,
        constraints: List[Constraint]
    ) -> List[TieBreakingExplanation]:
        """
        Identify and explain how ties were broken between similar options.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            constraints: List of constraints
            
        Returns:
            List of TieBreakingExplanation objects
        """
        explanations = []
        tie_threshold = 0.1  # Options within this score range are considered tied
        
        # Group options by similar scores
        score_groups = []
        current_group = []
        
        for i, option_score in enumerate(scoring_result.option_scores):
            if not current_group:
                current_group.append(option_score)
            else:
                score_diff = abs(current_group[0].total_score - option_score.total_score)
                if score_diff <= tie_threshold:
                    current_group.append(option_score)
                else:
                    if len(current_group) > 1:
                        score_groups.append(current_group)
                    current_group = [option_score]
        
        # Don't forget the last group
        if len(current_group) > 1:
            score_groups.append(current_group)
        
        # Generate explanations for each tied group
        for group in score_groups:
            if len(group) > 1:
                explanation = self._generate_tie_breaking_explanation(group, constraints)
                explanations.append(explanation)
        
        return explanations
    
    def _generate_tie_breaking_explanation(
        self,
        tied_options: List[OptionScore],
        constraints: List[Constraint]
    ) -> TieBreakingExplanation:
        """
        Generate explanation for how a specific tie was broken.
        
        Args:
            tied_options: List of options with similar scores
            constraints: List of constraints
            
        Returns:
            TieBreakingExplanation object
        """
        option_names = [opt.option_name for opt in tied_options]
        
        # Find the constraint that best differentiates these options
        best_differentiator = None
        max_variance = 0
        
        for constraint in constraints:
            scores = [opt.normalized_scores.get(constraint.name, 0) for opt in tied_options]
            if len(scores) > 1:
                mean_score = sum(scores) / len(scores)
                variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                
                if variance > max_variance:
                    max_variance = variance
                    best_differentiator = constraint
        
        # Generate tie-breaking factors
        tie_breaking_factors = []
        
        if best_differentiator:
            tie_breaking_factors.append(best_differentiator.name)
            
            # Add secondary factors
            for constraint in constraints:
                if constraint != best_differentiator:
                    scores = [opt.normalized_scores.get(constraint.name, 0) for opt in tied_options]
                    if len(scores) > 1:
                        mean_score = sum(scores) / len(scores)
                        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                        if variance > 0.05:  # Secondary threshold
                            tie_breaking_factors.append(constraint.name)
        
        # Limit to top 3 factors
        tie_breaking_factors = tie_breaking_factors[:3]
        
        # Calculate margin of difference
        scores = [opt.total_score for opt in tied_options]
        margin = max(scores) - min(scores) if scores else 0
        
        # Generate explanation text
        if tie_breaking_factors:
            explanation = (
                f"The tie between {', '.join(option_names)} was broken primarily by "
                f"differences in {', '.join(tie_breaking_factors)}. "
                f"While these options scored similarly overall (margin: {margin:.3f}), "
                f"their performance varied significantly in these key areas."
            )
        else:
            explanation = (
                f"The options {', '.join(option_names)} are very closely matched "
                f"(margin: {margin:.3f}). The ranking reflects minor differences "
                f"across multiple criteria rather than a single decisive factor."
            )
        
        return TieBreakingExplanation(
            tied_options=option_names,
            tie_breaking_factors=tie_breaking_factors,
            explanation=explanation,
            margin_of_difference=round(margin, 3)
        )
    
    def _analyze_decision_factors(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        Analyze key factors that influenced the decision.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            Dictionary containing decision factor analysis
        """
        # Identify most influential constraints
        constraint_influence = {}
        for constraint in constraints:
            # Calculate how much this constraint affected the rankings
            scores = [
                opt.constraint_scores.get(constraint.name, 0)
                for opt in scoring_result.option_scores
            ]
            
            if scores:
                # Influence is based on weight and score variance
                mean_score = sum(scores) / len(scores)
                variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
                influence = constraint.weight * variance
                constraint_influence[constraint.name] = influence
        
        # Sort by influence
        most_influential = sorted(
            constraint_influence.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "most_influential_constraints": [
                {"name": name, "influence_score": round(score, 3)}
                for name, score in most_influential
            ],
            "total_constraints": len(constraints),
            "total_weight": scoring_result.total_weight,
            "has_significant_tradeoffs": len(tradeoff_result.global_tradeoffs) > 0,
            "pareto_efficiency": len(tradeoff_result.pareto_frontier) / len(scoring_result.option_scores),
            "decision_complexity": self._calculate_decision_complexity(
                scoring_result, tradeoff_result, constraints
            )
        }
    
    def _calculate_decision_complexity(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> str:
        """Calculate and categorize the complexity of the decision."""
        complexity_score = 0
        
        # More options = more complex
        complexity_score += len(scoring_result.option_scores) * 0.1
        
        # More constraints = more complex
        complexity_score += len(constraints) * 0.15
        
        # Trade-offs increase complexity
        complexity_score += len(tradeoff_result.global_tradeoffs) * 0.2
        
        # Close scores increase complexity
        scores = [opt.total_score for opt in scoring_result.option_scores]
        if len(scores) > 1:
            score_range = max(scores) - min(scores)
            if score_range < 0.2:
                complexity_score += 0.3
        
        # Categorize complexity
        if complexity_score < 0.5:
            return "Low"
        elif complexity_score < 1.0:
            return "Moderate"
        else:
            return "High"
    
    def _generate_summary_text(
        self,
        recommendations: List[Recommendation],
        tie_breaking_explanations: List[TieBreakingExplanation],
        decision_factors: Dict[str, Any]
    ) -> str:
        """
        Generate the main summary text.
        
        Args:
            recommendations: List of all recommendations
            tie_breaking_explanations: List of tie-breaking explanations
            decision_factors: Analysis of decision factors
            
        Returns:
            Comprehensive summary text
        """
        summary_parts = []
        
        # Top recommendation
        top_rec = recommendations[0]
        summary_parts.append(
            f"Based on the analysis, {top_rec.option_name} is the top recommendation "
            f"(confidence: {top_rec.confidence:.0%})"
        )
        
        # Key reasoning
        if top_rec.key_advantages:
            summary_parts.append(
                f"This option excels in {', '.join(top_rec.key_advantages[:2])}"
            )
        
        # Decision complexity
        complexity = decision_factors.get("decision_complexity", "Moderate")
        summary_parts.append(f"This is a {complexity.lower()} complexity decision")
        
        # Trade-offs mention
        if decision_factors.get("has_significant_tradeoffs"):
            summary_parts.append(
                "The analysis identified significant trade-offs between competing factors"
            )
        
        # Tie-breaking mention
        if tie_breaking_explanations:
            summary_parts.append(
                f"Close competition required tie-breaking analysis for "
                f"{len(tie_breaking_explanations)} group(s) of similar options"
            )
        
        # Alternative options
        if len(recommendations) > 1:
            second_option = recommendations[1]
            summary_parts.append(
                f"{second_option.option_name} is a strong alternative, "
                f"particularly suitable for {second_option.best_for_scenarios[0] if second_option.best_for_scenarios else 'specific contexts'}"
            )
        
        return ". ".join(summary_parts) + "."
    
    def _determine_confidence_level(
        self,
        recommendations: List[Recommendation],
        tie_breaking_explanations: List[TieBreakingExplanation],
        decision_factors: Dict[str, Any]
    ) -> str:
        """
        Determine overall confidence level for the summary.
        
        Args:
            recommendations: List of all recommendations
            tie_breaking_explanations: List of tie-breaking explanations
            decision_factors: Analysis of decision factors
            
        Returns:
            Confidence level description
        """
        if not recommendations:
            return "Low"
        
        top_confidence = recommendations[0].confidence
        complexity = decision_factors.get("decision_complexity", "Moderate")
        
        # Adjust confidence based on various factors
        if top_confidence >= 0.8 and complexity == "Low":
            return "High"
        elif top_confidence >= 0.6 and len(tie_breaking_explanations) == 0:
            return "High"
        elif top_confidence >= 0.5:
            return "Moderate"
        else:
            return "Low"