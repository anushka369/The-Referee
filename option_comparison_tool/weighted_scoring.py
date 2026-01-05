"""
WeightedScoringAnalyzer - Implements weighted scoring analysis for option comparison.

This module provides the core weighted scoring algorithm with normalization
support for different constraint types (numeric, categorical, boolean).
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import math
from dataclasses import dataclass

from .models import Option, Constraint, ConstraintType, Priority, NumericScale, CategoricalScale

logger = logging.getLogger(__name__)


@dataclass
class OptionScore:
    """Represents the scoring results for a single option."""
    option_id: str
    option_name: str
    total_score: float
    constraint_scores: Dict[str, float]
    normalized_scores: Dict[str, float]
    rank: int = 0


@dataclass
class ScoringResult:
    """Complete results from weighted scoring analysis."""
    option_scores: List[OptionScore]
    total_weight: float
    analysis_metadata: Dict[str, Any]


class WeightedScoringAnalyzer:
    """
    Implements weighted scoring analysis for multi-criteria decision making.
    
    This analyzer supports different constraint types with appropriate normalization
    methods and provides ranking based on weighted scores.
    """
    
    def __init__(self):
        """Initialize the weighted scoring analyzer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def analyze(self, options: List[Option], constraints: List[Constraint]) -> ScoringResult:
        """
        Perform weighted scoring analysis on options against constraints.
        
        Args:
            options: List of options to analyze
            constraints: List of constraints to evaluate against
            
        Returns:
            ScoringResult containing scores and rankings
            
        Raises:
            ValueError: If inputs are invalid or analysis cannot be performed
        """
        self.logger.info(f"Starting weighted scoring analysis for {len(options)} options and {len(constraints)} constraints")
        
        # Validate inputs
        self._validate_inputs(options, constraints)
        
        # If no constraints, return equal scores
        if not constraints:
            return self._create_equal_scores_result(options)
        
        # Calculate raw scores for each option against each constraint
        raw_scores = self._calculate_raw_scores(options, constraints)
        
        # Normalize scores based on constraint types and scales
        normalized_scores = self._normalize_scores(raw_scores, constraints)
        
        # Calculate weighted total scores
        option_scores = self._calculate_weighted_scores(options, constraints, normalized_scores)
        
        # Rank options by total score
        ranked_scores = self._rank_options(option_scores)
        
        # Create analysis metadata
        metadata = self._create_analysis_metadata(options, constraints, raw_scores, normalized_scores)
        
        result = ScoringResult(
            option_scores=ranked_scores,
            total_weight=sum(c.weight for c in constraints),
            analysis_metadata=metadata
        )
        
        self.logger.info(f"Completed weighted scoring analysis. Top option: {ranked_scores[0].option_name}")
        return result
    
    def _validate_inputs(self, options: List[Option], constraints: List[Constraint]) -> None:
        """
        Validate inputs for weighted scoring analysis.
        
        Args:
            options: List of options to validate
            constraints: List of constraints to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not options:
            raise ValueError("At least one option is required for analysis")
        
        if len(options) < 2:
            raise ValueError("At least two options are required for meaningful comparison")
        
        # Validate that all options have unique names
        option_names = [opt.name for opt in options]
        if len(option_names) != len(set(option_names)):
            raise ValueError("All options must have unique names")
        
        # Validate constraints have valid weights
        for constraint in constraints:
            if not (0.0 <= constraint.weight <= 1.0):
                raise ValueError(f"Constraint '{constraint.name}' has invalid weight: {constraint.weight}")
    
    def _create_equal_scores_result(self, options: List[Option]) -> ScoringResult:
        """
        Create a result with equal scores when no constraints are provided.
        
        Args:
            options: List of options
            
        Returns:
            ScoringResult with equal scores for all options
        """
        option_scores = []
        for i, option in enumerate(options):
            score = OptionScore(
                option_id=option.id,
                option_name=option.name,
                total_score=0.0,
                constraint_scores={},
                normalized_scores={},
                rank=i + 1  # All tied for rank 1, but we'll assign sequential ranks
            )
            option_scores.append(score)
        
        metadata = {
            "analysis_type": "weighted_scoring",
            "constraint_count": 0,
            "normalization_methods": {},
            "notes": "No constraints provided - all options scored equally"
        }
        
        return ScoringResult(
            option_scores=option_scores,
            total_weight=0.0,
            analysis_metadata=metadata
        )
    
    def _calculate_raw_scores(self, options: List[Option], constraints: List[Constraint]) -> Dict[str, Dict[str, float]]:
        """
        Calculate raw scores for each option against each constraint.
        
        Args:
            options: List of options to score
            constraints: List of constraints to evaluate
            
        Returns:
            Dictionary mapping option_id -> constraint_name -> raw_score
        """
        raw_scores = {}
        
        for option in options:
            raw_scores[option.id] = {}
            
            for constraint in constraints:
                raw_score = self._score_option_for_constraint(option, constraint)
                raw_scores[option.id][constraint.name] = raw_score
        
        return raw_scores
    
    def _score_option_for_constraint(self, option: Option, constraint: Constraint) -> float:
        """
        Calculate raw score for a single option against a single constraint.
        
        Args:
            option: Option to score
            constraint: Constraint to evaluate against
            
        Returns:
            Raw score (before normalization)
        """
        # Get the attribute value for this constraint
        attribute_value = option.attributes.get(constraint.name)
        
        if attribute_value is None:
            # Missing attribute - return 0 score
            self.logger.warning(f"Option '{option.name}' missing attribute '{constraint.name}'")
            return 0.0
        
        if constraint.type == ConstraintType.BOOLEAN:
            return self._score_boolean_constraint(attribute_value)
        elif constraint.type == ConstraintType.CATEGORICAL:
            return self._score_categorical_constraint(attribute_value, constraint)
        elif constraint.type == ConstraintType.NUMERIC:
            return self._score_numeric_constraint(attribute_value, constraint)
        else:
            raise ValueError(f"Unsupported constraint type: {constraint.type}")
    
    def _score_boolean_constraint(self, value: Any) -> float:
        """Score a boolean constraint."""
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        elif isinstance(value, str):
            # Handle string representations of boolean
            lower_val = value.lower()
            if lower_val in ('true', 'yes', '1', 'on'):
                return 1.0
            elif lower_val in ('false', 'no', '0', 'off'):
                return 0.0
            else:
                return 0.0
        elif isinstance(value, (int, float)):
            return 1.0 if value else 0.0
        else:
            return 0.0
    
    def _score_categorical_constraint(self, value: Any, constraint: Constraint) -> float:
        """Score a categorical constraint using its scale."""
        if not constraint.scale or not isinstance(constraint.scale, CategoricalScale):
            # No scale defined - try to convert to numeric if possible
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        
        scale = constraint.scale
        value_str = str(value).lower()
        
        # Find matching value in scale
        for i, scale_value in enumerate(scale.values):
            if scale_value.lower() == value_str:
                return scale.scores[i]
        
        # Value not found in scale
        self.logger.warning(f"Value '{value}' not found in categorical scale for constraint '{constraint.name}'")
        return 0.0
    
    def _score_numeric_constraint(self, value: Any, constraint: Constraint) -> float:
        """Score a numeric constraint."""
        try:
            numeric_value = float(value)
            return numeric_value
        except (ValueError, TypeError):
            self.logger.warning(f"Could not convert value '{value}' to numeric for constraint '{constraint.name}'")
            return 0.0
    
    def _normalize_scores(self, raw_scores: Dict[str, Dict[str, float]], constraints: List[Constraint]) -> Dict[str, Dict[str, float]]:
        """
        Normalize raw scores based on constraint types and scales.
        
        Args:
            raw_scores: Raw scores for all options and constraints
            constraints: List of constraints with normalization info
            
        Returns:
            Dictionary mapping option_id -> constraint_name -> normalized_score
        """
        normalized_scores = {}
        
        for constraint in constraints:
            # Get all raw scores for this constraint
            constraint_scores = [
                raw_scores[option_id][constraint.name] 
                for option_id in raw_scores.keys()
            ]
            
            # Normalize based on constraint type and scale
            if constraint.type == ConstraintType.BOOLEAN:
                # Boolean scores are already 0 or 1
                normalized_constraint_scores = constraint_scores
            elif constraint.type == ConstraintType.CATEGORICAL:
                # Categorical scores use the scale values directly
                normalized_constraint_scores = constraint_scores
            elif constraint.type == ConstraintType.NUMERIC:
                normalized_constraint_scores = self._normalize_numeric_scores(
                    constraint_scores, constraint
                )
            else:
                # Default: no normalization
                normalized_constraint_scores = constraint_scores
            
            # Store normalized scores
            for i, option_id in enumerate(raw_scores.keys()):
                if option_id not in normalized_scores:
                    normalized_scores[option_id] = {}
                normalized_scores[option_id][constraint.name] = normalized_constraint_scores[i]
        
        return normalized_scores
    
    def _normalize_numeric_scores(self, scores: List[float], constraint: Constraint) -> List[float]:
        """
        Normalize numeric scores using the specified method.
        
        Args:
            scores: List of raw numeric scores
            constraint: Constraint with normalization settings
            
        Returns:
            List of normalized scores
        """
        if not scores or all(s == 0 for s in scores):
            return scores
        
        # Get normalization method from scale or use default
        normalization_method = "min-max"
        direction = "higher-better"
        
        if constraint.scale and isinstance(constraint.scale, NumericScale):
            normalization_method = constraint.scale.normalization_method
            direction = constraint.scale.direction
        
        if normalization_method == "min-max":
            return self._min_max_normalize(scores, direction)
        elif normalization_method == "z-score":
            return self._z_score_normalize(scores, direction)
        else:
            # Default to min-max
            return self._min_max_normalize(scores, direction)
    
    def _min_max_normalize(self, scores: List[float], direction: str) -> List[float]:
        """Perform min-max normalization on scores."""
        min_score = min(scores)
        max_score = max(scores)
        
        if min_score == max_score:
            # All scores are the same
            return [0.5] * len(scores)
        
        normalized = []
        for score in scores:
            norm_score = (score - min_score) / (max_score - min_score)
            
            # Reverse if lower is better
            if direction == "lower-better":
                norm_score = 1.0 - norm_score
            
            normalized.append(norm_score)
        
        return normalized
    
    def _z_score_normalize(self, scores: List[float], direction: str) -> List[float]:
        """Perform z-score normalization on scores."""
        if len(scores) <= 1:
            return [0.5] * len(scores)
        
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        
        if variance == 0:
            return [0.5] * len(scores)
        
        std_dev = math.sqrt(variance)
        
        normalized = []
        for score in scores:
            z_score = (score - mean_score) / std_dev
            
            # Convert z-score to 0-1 range using sigmoid function
            norm_score = 1 / (1 + math.exp(-z_score))
            
            # Reverse if lower is better
            if direction == "lower-better":
                norm_score = 1.0 - norm_score
            
            normalized.append(norm_score)
        
        return normalized
    
    def _calculate_weighted_scores(self, options: List[Option], constraints: List[Constraint], 
                                 normalized_scores: Dict[str, Dict[str, float]]) -> List[OptionScore]:
        """
        Calculate weighted total scores for all options.
        
        Args:
            options: List of options
            constraints: List of constraints with weights
            normalized_scores: Normalized scores for all options and constraints
            
        Returns:
            List of OptionScore objects with calculated totals
        """
        option_scores = []
        
        for option in options:
            constraint_scores = {}
            norm_scores = {}
            total_score = 0.0
            
            for constraint in constraints:
                raw_score = normalized_scores[option.id].get(constraint.name, 0.0)
                weighted_score = raw_score * constraint.weight
                
                constraint_scores[constraint.name] = weighted_score
                norm_scores[constraint.name] = raw_score
                total_score += weighted_score
            
            option_score = OptionScore(
                option_id=option.id,
                option_name=option.name,
                total_score=total_score,
                constraint_scores=constraint_scores,
                normalized_scores=norm_scores
            )
            option_scores.append(option_score)
        
        return option_scores
    
    def _rank_options(self, option_scores: List[OptionScore]) -> List[OptionScore]:
        """
        Rank options by total score (highest first).
        
        Args:
            option_scores: List of OptionScore objects
            
        Returns:
            List of OptionScore objects sorted by rank
        """
        # Sort by total score (descending)
        sorted_scores = sorted(option_scores, key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks (handle ties)
        current_rank = 1
        for i, score in enumerate(sorted_scores):
            if i > 0 and sorted_scores[i-1].total_score != score.total_score:
                current_rank = i + 1
            score.rank = current_rank
        
        return sorted_scores
    
    def _create_analysis_metadata(self, options: List[Option], constraints: List[Constraint],
                                raw_scores: Dict[str, Dict[str, float]], 
                                normalized_scores: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Create metadata about the analysis."""
        normalization_methods = {}
        for constraint in constraints:
            if constraint.type == ConstraintType.NUMERIC and constraint.scale:
                normalization_methods[constraint.name] = constraint.scale.normalization_method
            else:
                normalization_methods[constraint.name] = "none"
        
        return {
            "analysis_type": "weighted_scoring",
            "option_count": len(options),
            "constraint_count": len(constraints),
            "total_weight": sum(c.weight for c in constraints),
            "normalization_methods": normalization_methods,
            "constraint_types": {c.name: c.type.value for c in constraints},
            "constraint_priorities": {c.name: c.priority.value for c in constraints}
        }