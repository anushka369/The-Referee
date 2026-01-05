"""
DynamicAnalyzer - Implements dynamic analysis features for option comparison.

This module provides constraint weight adjustment, impact analysis, and what-if
analysis capabilities for interactive exploration of comparison scenarios.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy

from .models import Option, Constraint, ComparisonSession
from .weighted_scoring import WeightedScoringAnalyzer, ScoringResult, OptionScore

logger = logging.getLogger(__name__)


@dataclass
class WeightAdjustment:
    """Represents a constraint weight adjustment."""
    constraint_name: str
    old_weight: float
    new_weight: float


@dataclass
class ImpactAnalysis:
    """Results of impact analysis for constraint modifications."""
    weight_adjustments: List[WeightAdjustment]
    ranking_changes: Dict[str, Tuple[int, int]]  # option_name -> (old_rank, new_rank)
    score_changes: Dict[str, Tuple[float, float]]  # option_name -> (old_score, new_score)
    most_affected_options: List[str]  # option names ordered by impact magnitude
    summary: str


@dataclass
class WhatIfScenario:
    """Represents a what-if analysis scenario."""
    scenario_name: str
    original_constraints: List[Constraint]
    modified_constraints: List[Constraint]
    original_result: ScoringResult
    modified_result: ScoringResult
    impact_analysis: ImpactAnalysis


class DynamicAnalyzer:
    """
    Implements dynamic analysis features for interactive comparison exploration.
    
    Provides constraint weight adjustment, impact analysis, and what-if scenarios
    to help users understand how changes affect their comparison results.
    """
    
    def __init__(self):
        """Initialize the dynamic analyzer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.scoring_analyzer = WeightedScoringAnalyzer()
    
    def adjust_constraint_weights(
        self, 
        session: ComparisonSession, 
        weight_adjustments: Dict[str, float]
    ) -> Tuple[ComparisonSession, ImpactAnalysis]:
        """
        Adjust constraint weights and recalculate analysis with impact analysis.
        
        Args:
            session: The comparison session to modify
            weight_adjustments: Dictionary mapping constraint names to new weights
            
        Returns:
            Tuple of (updated_session, impact_analysis)
            
        Raises:
            ValueError: If weight adjustments are invalid
        """
        self.logger.info(f"Adjusting weights for {len(weight_adjustments)} constraints")
        
        # Validate weight adjustments
        self._validate_weight_adjustments(session, weight_adjustments)
        
        # Store original state for impact analysis
        original_constraints = deepcopy(session.constraints)
        original_result = None
        if session.analysis_results:
            # Re-run original analysis to ensure consistency
            original_result = self.scoring_analyzer.analyze(session.options, original_constraints)
        
        # Apply weight adjustments
        adjustments = []
        for constraint in session.constraints:
            if constraint.name in weight_adjustments:
                old_weight = constraint.weight
                new_weight = weight_adjustments[constraint.name]
                constraint.weight = new_weight
                adjustments.append(WeightAdjustment(constraint.name, old_weight, new_weight))
        
        # Recalculate analysis
        new_result = self.scoring_analyzer.analyze(session.options, session.constraints)
        session.analysis_results = {
            'weighted_scoring': new_result.__dict__
        }
        session.update_timestamp()
        
        # Perform impact analysis
        impact_analysis = self._analyze_impact(
            adjustments, original_result, new_result, original_constraints, session.constraints
        )
        
        self.logger.info(f"Weight adjustment complete. {len(impact_analysis.most_affected_options)} options affected")
        return session, impact_analysis
    
    def create_what_if_scenario(
        self, 
        session: ComparisonSession, 
        scenario_name: str,
        weight_adjustments: Dict[str, float]
    ) -> WhatIfScenario:
        """
        Create a what-if scenario without modifying the original session.
        
        Args:
            session: The original comparison session
            scenario_name: Name for this scenario
            weight_adjustments: Dictionary mapping constraint names to new weights
            
        Returns:
            WhatIfScenario with original and modified results
            
        Raises:
            ValueError: If weight adjustments are invalid
        """
        self.logger.info(f"Creating what-if scenario '{scenario_name}' with {len(weight_adjustments)} weight changes")
        
        # Validate weight adjustments
        self._validate_weight_adjustments(session, weight_adjustments)
        
        # Get original analysis results
        original_result = self.scoring_analyzer.analyze(session.options, session.constraints)
        
        # Create modified constraints
        modified_constraints = deepcopy(session.constraints)
        adjustments = []
        
        for constraint in modified_constraints:
            if constraint.name in weight_adjustments:
                old_weight = constraint.weight
                new_weight = weight_adjustments[constraint.name]
                constraint.weight = new_weight
                adjustments.append(WeightAdjustment(constraint.name, old_weight, new_weight))
        
        # Run analysis with modified constraints
        modified_result = self.scoring_analyzer.analyze(session.options, modified_constraints)
        
        # Perform impact analysis
        impact_analysis = self._analyze_impact(
            adjustments, original_result, modified_result, session.constraints, modified_constraints
        )
        
        scenario = WhatIfScenario(
            scenario_name=scenario_name,
            original_constraints=deepcopy(session.constraints),
            modified_constraints=modified_constraints,
            original_result=original_result,
            modified_result=modified_result,
            impact_analysis=impact_analysis
        )
        
        self.logger.info(f"What-if scenario '{scenario_name}' created successfully")
        return scenario
    
    def analyze_constraint_sensitivity(
        self, 
        session: ComparisonSession, 
        constraint_name: str,
        weight_range: Tuple[float, float] = (0.0, 1.0),
        steps: int = 10
    ) -> Dict[float, ScoringResult]:
        """
        Analyze how sensitive rankings are to changes in a specific constraint weight.
        
        Args:
            session: The comparison session
            constraint_name: Name of constraint to analyze
            weight_range: Tuple of (min_weight, max_weight) to test
            steps: Number of weight values to test
            
        Returns:
            Dictionary mapping weight values to scoring results
            
        Raises:
            ValueError: If constraint not found or parameters invalid
        """
        self.logger.info(f"Analyzing sensitivity for constraint '{constraint_name}' over {steps} steps")
        
        # Find the constraint
        target_constraint = None
        for constraint in session.constraints:
            if constraint.name == constraint_name:
                target_constraint = constraint
                break
        
        if not target_constraint:
            raise ValueError(f"Constraint '{constraint_name}' not found in session")
        
        if weight_range[0] < 0.0 or weight_range[1] > 1.0 or weight_range[0] >= weight_range[1]:
            raise ValueError("Invalid weight range. Must be 0.0 <= min < max <= 1.0")
        
        if steps < 2:
            raise ValueError("Steps must be at least 2")
        
        # Store original weight
        original_weight = target_constraint.weight
        
        # Generate weight values to test
        min_weight, max_weight = weight_range
        weight_step = (max_weight - min_weight) / (steps - 1)
        weight_values = [min_weight + i * weight_step for i in range(steps)]
        
        # Test each weight value
        sensitivity_results = {}
        
        try:
            for weight in weight_values:
                # Temporarily adjust weight
                target_constraint.weight = weight
                
                # Run analysis
                result = self.scoring_analyzer.analyze(session.options, session.constraints)
                sensitivity_results[weight] = result
        
        finally:
            # Restore original weight
            target_constraint.weight = original_weight
        
        self.logger.info(f"Sensitivity analysis complete for constraint '{constraint_name}'")
        return sensitivity_results
    
    def identify_critical_constraints(
        self, 
        session: ComparisonSession,
        sensitivity_threshold: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Identify constraints that have the most impact on rankings.
        
        Args:
            session: The comparison session
            sensitivity_threshold: Minimum weight change to test (default 0.1)
            
        Returns:
            List of (constraint_name, impact_score) tuples, sorted by impact
        """
        self.logger.info(f"Identifying critical constraints with threshold {sensitivity_threshold}")
        
        if not session.constraints:
            return []
        
        # Get baseline results
        baseline_result = self.scoring_analyzer.analyze(session.options, session.constraints)
        baseline_rankings = {score.option_name: score.rank for score in baseline_result.option_scores}
        
        constraint_impacts = []
        
        for constraint in session.constraints:
            # Test increasing weight
            original_weight = constraint.weight
            test_weight = min(1.0, original_weight + sensitivity_threshold)
            
            if test_weight != original_weight:
                # Temporarily adjust weight
                constraint.weight = test_weight
                
                try:
                    # Run analysis with adjusted weight
                    test_result = self.scoring_analyzer.analyze(session.options, session.constraints)
                    test_rankings = {score.option_name: score.rank for score in test_result.option_scores}
                    
                    # Calculate ranking changes
                    ranking_changes = 0
                    for option_name in baseline_rankings:
                        old_rank = baseline_rankings[option_name]
                        new_rank = test_rankings.get(option_name, old_rank)
                        ranking_changes += abs(old_rank - new_rank)
                    
                    # Impact score is total ranking changes
                    impact_score = ranking_changes
                    constraint_impacts.append((constraint.name, impact_score))
                
                finally:
                    # Restore original weight
                    constraint.weight = original_weight
        
        # Sort by impact (highest first)
        constraint_impacts.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Identified {len(constraint_impacts)} constraints with impact analysis")
        return constraint_impacts
    
    def _validate_weight_adjustments(
        self, 
        session: ComparisonSession, 
        weight_adjustments: Dict[str, float]
    ) -> None:
        """
        Validate weight adjustments.
        
        Args:
            session: The comparison session
            weight_adjustments: Dictionary of constraint name to new weight
            
        Raises:
            ValueError: If validation fails
        """
        if not weight_adjustments:
            raise ValueError("No weight adjustments provided")
        
        # Check that all constraint names exist
        constraint_names = {c.name for c in session.constraints}
        for constraint_name in weight_adjustments:
            if constraint_name not in constraint_names:
                raise ValueError(f"Constraint '{constraint_name}' not found in session")
        
        # Check that all weights are valid
        for constraint_name, weight in weight_adjustments.items():
            if not isinstance(weight, (int, float)):
                raise ValueError(f"Weight for '{constraint_name}' must be a number")
            if not (0.0 <= weight <= 1.0):
                raise ValueError(f"Weight for '{constraint_name}' must be between 0.0 and 1.0, got {weight}")
    
    def _analyze_impact(
        self,
        adjustments: List[WeightAdjustment],
        original_result: Optional[ScoringResult],
        new_result: ScoringResult,
        original_constraints: List[Constraint],
        new_constraints: List[Constraint]
    ) -> ImpactAnalysis:
        """
        Analyze the impact of weight adjustments on rankings and scores.
        
        Args:
            adjustments: List of weight adjustments made
            original_result: Original scoring results (None if no previous analysis)
            new_result: New scoring results after adjustments
            original_constraints: Original constraints
            new_constraints: New constraints after adjustments
            
        Returns:
            ImpactAnalysis with detailed impact information
        """
        ranking_changes = {}
        score_changes = {}
        
        if original_result:
            # Create lookup dictionaries for original results
            original_rankings = {score.option_name: score.rank for score in original_result.option_scores}
            original_scores = {score.option_name: score.total_score for score in original_result.option_scores}
            
            # Calculate changes
            for new_score in new_result.option_scores:
                option_name = new_score.option_name
                
                old_rank = original_rankings.get(option_name, 0)
                new_rank = new_score.rank
                ranking_changes[option_name] = (old_rank, new_rank)
                
                old_score = original_scores.get(option_name, 0.0)
                new_score_val = new_score.total_score
                score_changes[option_name] = (old_score, new_score_val)
        else:
            # No original results - all changes are from baseline of 0
            for new_score in new_result.option_scores:
                option_name = new_score.option_name
                ranking_changes[option_name] = (0, new_score.rank)
                score_changes[option_name] = (0.0, new_score.total_score)
        
        # Identify most affected options (by ranking change magnitude)
        ranking_impacts = []
        for option_name, (old_rank, new_rank) in ranking_changes.items():
            impact_magnitude = abs(old_rank - new_rank)
            ranking_impacts.append((option_name, impact_magnitude))
        
        # Sort by impact magnitude (highest first)
        ranking_impacts.sort(key=lambda x: x[1], reverse=True)
        most_affected_options = [option_name for option_name, _ in ranking_impacts]
        
        # Generate summary
        summary = self._generate_impact_summary(adjustments, ranking_changes, most_affected_options)
        
        return ImpactAnalysis(
            weight_adjustments=adjustments,
            ranking_changes=ranking_changes,
            score_changes=score_changes,
            most_affected_options=most_affected_options,
            summary=summary
        )
    
    def _generate_impact_summary(
        self,
        adjustments: List[WeightAdjustment],
        ranking_changes: Dict[str, Tuple[int, int]],
        most_affected_options: List[str]
    ) -> str:
        """Generate a human-readable summary of the impact analysis."""
        if not adjustments:
            return "No weight adjustments were made."
        
        # Count significant ranking changes
        significant_changes = sum(
            1 for old_rank, new_rank in ranking_changes.values() 
            if abs(old_rank - new_rank) > 0
        )
        
        # Build summary
        summary_parts = []
        
        # Adjustments made
        if len(adjustments) == 1:
            adj = adjustments[0]
            summary_parts.append(
                f"Adjusted weight for '{adj.constraint_name}' from {adj.old_weight:.2f} to {adj.new_weight:.2f}."
            )
        else:
            summary_parts.append(f"Adjusted weights for {len(adjustments)} constraints.")
        
        # Impact on rankings
        if significant_changes == 0:
            summary_parts.append("No ranking changes occurred.")
        elif significant_changes == 1:
            summary_parts.append("1 option changed ranking.")
        else:
            summary_parts.append(f"{significant_changes} options changed rankings.")
        
        # Most affected option
        if most_affected_options and ranking_changes:
            top_option = most_affected_options[0]
            old_rank, new_rank = ranking_changes[top_option]
            if abs(old_rank - new_rank) > 0:
                if new_rank < old_rank:
                    summary_parts.append(f"'{top_option}' improved from rank {old_rank} to {new_rank}.")
                else:
                    summary_parts.append(f"'{top_option}' dropped from rank {old_rank} to {new_rank}.")
        
        return " ".join(summary_parts)