"""
Property-based tests for WeightedScoringAnalyzer.

Feature: option-comparison-tool
Property 5: Scoring Consistency
Validates: Requirements 2.2, 5.1
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, assume
from option_comparison_tool.models import (
    Option, Constraint, ConstraintType, Priority, NumericScale, CategoricalScale
)
from option_comparison_tool.weighted_scoring import WeightedScoringAnalyzer


# Hypothesis strategies for generating test data
@st.composite
def valid_option_with_attributes_strategy(draw):
    """Generate valid Option instances with attributes for scoring."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    description = draw(st.text(max_size=500))
    
    # Generate attributes that will be used by constraints
    attributes = {}
    
    # Add some numeric attributes
    for i in range(draw(st.integers(min_value=1, max_value=5))):
        attr_name = f"numeric_attr_{i}"
        attributes[attr_name] = draw(st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False))
    
    # Add some boolean attributes
    for i in range(draw(st.integers(min_value=1, max_value=3))):
        attr_name = f"boolean_attr_{i}"
        attributes[attr_name] = draw(st.booleans())
    
    # Add some categorical attributes
    for i in range(draw(st.integers(min_value=1, max_value=3))):
        attr_name = f"categorical_attr_{i}"
        attributes[attr_name] = draw(st.sampled_from(["low", "medium", "high"]))
    
    return Option(
        name=name,
        description=description,
        attributes=attributes
    )


@st.composite
def valid_constraint_with_scale_strategy(draw):
    """Generate valid Constraint instances with appropriate scales."""
    constraint_type = draw(st.sampled_from(ConstraintType))
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    # Generate scale based on constraint type
    scale = None
    if constraint_type == ConstraintType.NUMERIC:
        scale = NumericScale(
            min=draw(st.floats(min_value=0, max_value=100)),
            max=draw(st.floats(min_value=101, max_value=1000)),
            direction=draw(st.sampled_from(["higher-better", "lower-better"])),
            normalization_method=draw(st.sampled_from(["min-max", "z-score"]))
        )
    elif constraint_type == ConstraintType.CATEGORICAL:
        values = ["low", "medium", "high"]
        scores = [1.0, 5.0, 10.0]
        scale = CategoricalScale(values=values, scores=scores, ordered=True)
    
    return Constraint(
        name=name,
        description=draw(st.text(max_size=500)),
        weight=draw(st.floats(min_value=0.1, max_value=1.0)),
        priority=draw(st.sampled_from(Priority)),
        type=constraint_type,
        scale=scale
    )


@st.composite
def matching_options_and_constraints_strategy(draw):
    """Generate options and constraints where options have attributes matching constraint names."""
    # First generate constraints
    constraints = draw(st.lists(valid_constraint_with_scale_strategy(), min_size=1, max_size=5))
    
    # Make constraint names unique
    unique_constraints = []
    seen_names = set()
    for constraint in constraints:
        if constraint.name not in seen_names:
            unique_constraints.append(constraint)
            seen_names.add(constraint.name)
    
    assume(len(unique_constraints) >= 1)
    
    # Generate options with attributes matching constraint names
    options = []
    for i in range(draw(st.integers(min_value=2, max_value=5))):
        option_name = f"Option_{i}"
        attributes = {}
        
        # Add attributes for each constraint
        for constraint in unique_constraints:
            if constraint.type == ConstraintType.NUMERIC:
                attributes[constraint.name] = draw(st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False))
            elif constraint.type == ConstraintType.BOOLEAN:
                attributes[constraint.name] = draw(st.booleans())
            elif constraint.type == ConstraintType.CATEGORICAL:
                attributes[constraint.name] = draw(st.sampled_from(["low", "medium", "high"]))
        
        option = Option(
            name=option_name,
            description=f"Test option {i}",
            attributes=attributes
        )
        options.append(option)
    
    return options, unique_constraints


class TestScoringConsistency:
    """Test scoring consistency using property-based testing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.analyzer = WeightedScoringAnalyzer()
    
    @given(matching_options_and_constraints_strategy())
    def test_identical_options_receive_identical_scores(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any set of options and constraints, options with identical attributes should receive identical scores.
        Validates: Requirements 2.2, 5.1
        """
        options, constraints = options_and_constraints
        
        # Create two identical options
        original_option = options[0]
        identical_option = Option(
            name="Identical_Option",
            description=original_option.description,
            attributes=original_option.attributes.copy()
        )
        
        # Test with original and identical option
        test_options = [original_option, identical_option]
        
        # Run analysis
        result = self.analyzer.analyze(test_options, constraints)
        
        # Find scores for both options
        original_score = None
        identical_score = None
        
        for option_score in result.option_scores:
            if option_score.option_name == original_option.name:
                original_score = option_score
            elif option_score.option_name == "Identical_Option":
                identical_score = option_score
        
        # Verify identical options have identical scores
        assert original_score is not None
        assert identical_score is not None
        assert abs(original_score.total_score - identical_score.total_score) < 1e-10
        
        # Verify constraint-level scores are also identical
        for constraint_name in original_score.constraint_scores:
            original_constraint_score = original_score.constraint_scores[constraint_name]
            identical_constraint_score = identical_score.constraint_scores[constraint_name]
            assert abs(original_constraint_score - identical_constraint_score) < 1e-10
    
    @given(matching_options_and_constraints_strategy())
    def test_all_options_receive_scores(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any set of options and constraints, the system should calculate scores for all options.
        Validates: Requirements 2.2, 5.1
        """
        options, constraints = options_and_constraints
        
        # Run analysis
        result = self.analyzer.analyze(options, constraints)
        
        # Verify all options received scores
        assert len(result.option_scores) == len(options)
        
        # Verify each option has a score entry
        option_names = {opt.name for opt in options}
        scored_names = {score.option_name for score in result.option_scores}
        assert option_names == scored_names
        
        # Verify each option has scores for all constraints
        for option_score in result.option_scores:
            for constraint in constraints:
                assert constraint.name in option_score.constraint_scores
                assert constraint.name in option_score.normalized_scores
                # Scores should be finite numbers
                assert isinstance(option_score.constraint_scores[constraint.name], (int, float))
                assert isinstance(option_score.normalized_scores[constraint.name], (int, float))
    
    @given(matching_options_and_constraints_strategy())
    def test_scoring_is_deterministic(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any set of options and constraints, running the analysis multiple times should produce identical results.
        Validates: Requirements 2.2, 5.1
        """
        options, constraints = options_and_constraints
        
        # Run analysis twice
        result1 = self.analyzer.analyze(options, constraints)
        result2 = self.analyzer.analyze(options, constraints)
        
        # Results should be identical
        assert len(result1.option_scores) == len(result2.option_scores)
        
        # Sort both results by option name for comparison
        scores1 = sorted(result1.option_scores, key=lambda x: x.option_name)
        scores2 = sorted(result2.option_scores, key=lambda x: x.option_name)
        
        for score1, score2 in zip(scores1, scores2):
            assert score1.option_name == score2.option_name
            assert abs(score1.total_score - score2.total_score) < 1e-10
            assert score1.rank == score2.rank
            
            # Check constraint-level scores
            for constraint_name in score1.constraint_scores:
                assert abs(score1.constraint_scores[constraint_name] - score2.constraint_scores[constraint_name]) < 1e-10
                assert abs(score1.normalized_scores[constraint_name] - score2.normalized_scores[constraint_name]) < 1e-10
    
    @given(st.lists(valid_option_with_attributes_strategy(), min_size=2, max_size=5))
    def test_empty_constraints_produce_equal_scores(self, options):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any set of options with no constraints, all options should receive equal scores.
        Validates: Requirements 2.2, 5.1
        """
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        assume(len(unique_options) >= 2)
        
        # Run analysis with empty constraints
        result = self.analyzer.analyze(unique_options, [])
        
        # All options should have the same total score (0.0)
        total_scores = [score.total_score for score in result.option_scores]
        assert all(score == 0.0 for score in total_scores)
        
        # All options should have empty constraint scores
        for option_score in result.option_scores:
            assert len(option_score.constraint_scores) == 0
            assert len(option_score.normalized_scores) == 0
    
    @given(matching_options_and_constraints_strategy())
    def test_normalized_scores_are_in_valid_range(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any analysis, normalized scores should be finite and reasonable.
        Validates: Requirements 2.2, 5.1
        """
        options, constraints = options_and_constraints
        
        # Run analysis
        result = self.analyzer.analyze(options, constraints)
        
        # Check that normalized scores are in reasonable range
        for option_score in result.option_scores:
            for constraint_name, norm_score in option_score.normalized_scores.items():
                # Normalized scores should be finite
                assert isinstance(norm_score, (int, float))
                assert not (norm_score != norm_score)  # Check for NaN
                assert norm_score != float('inf') and norm_score != float('-inf')
                
                # Find the constraint to check its type
                constraint = next((c for c in constraints if c.name == constraint_name), None)
                assert constraint is not None
                
                # Different constraints have different valid ranges
                if constraint.type == ConstraintType.BOOLEAN:
                    # Boolean scores should be 0 or 1
                    assert norm_score in [0.0, 1.0]
                elif constraint.type == ConstraintType.CATEGORICAL:
                    # Categorical scores use scale values directly - should be reasonable but not necessarily 0-1
                    assert -1000 <= norm_score <= 1000  # Reasonable bounds
                elif constraint.type == ConstraintType.NUMERIC:
                    # Numeric scores are normalized to 0-1 range (with some tolerance)
                    assert -0.1 <= norm_score <= 1.1
    
    @given(matching_options_and_constraints_strategy())
    def test_ranking_is_consistent_with_scores(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any analysis, option rankings should be consistent with total scores (higher score = better rank).
        Validates: Requirements 2.2, 5.1
        """
        options, constraints = options_and_constraints
        
        # Run analysis
        result = self.analyzer.analyze(options, constraints)
        
        # Sort by rank
        sorted_by_rank = sorted(result.option_scores, key=lambda x: x.rank)
        
        # Verify scores are in descending order (higher scores get better/lower ranks)
        for i in range(len(sorted_by_rank) - 1):
            current_score = sorted_by_rank[i].total_score
            next_score = sorted_by_rank[i + 1].total_score
            
            # Current option should have score >= next option (allowing for ties)
            assert current_score >= next_score - 1e-10
    
    @given(st.lists(valid_option_with_attributes_strategy(), min_size=2, max_size=3),
           st.lists(valid_constraint_with_scale_strategy(), min_size=1, max_size=3))
    def test_analysis_handles_missing_attributes_gracefully(self, options, constraints):
        """
        Feature: option-comparison-tool, Property 5: Scoring Consistency
        For any options missing constraint attributes, the system should handle them gracefully with consistent scoring.
        Validates: Requirements 2.2, 5.1
        """
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        assume(len(unique_options) >= 2)
        assume(len(unique_constraints) >= 1)
        
        # Run analysis (options likely won't have attributes matching constraint names)
        result = self.analyzer.analyze(unique_options, unique_constraints)
        
        # Analysis should complete without errors
        assert result is not None
        assert len(result.option_scores) == len(unique_options)
        
        # All options should have scores (even if 0 for missing attributes)
        for option_score in result.option_scores:
            assert isinstance(option_score.total_score, (int, float))
            assert len(option_score.constraint_scores) == len(unique_constraints)
            assert len(option_score.normalized_scores) == len(unique_constraints)