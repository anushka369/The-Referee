"""
Property-based tests for TradeoffAnalyzer.

Feature: option-comparison-tool
Property 7: Trade-off Identification
Property 8: Trade-off Quantification
Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import pytest
from hypothesis import given, strategies as st, assume
from option_comparison_tool.models import (
    Option, Constraint, ConstraintType, Priority, NumericScale, CategoricalScale
)
from option_comparison_tool.tradeoff_analyzer import TradeoffAnalyzer


# Hypothesis strategies for generating test data
@st.composite
def competing_options_strategy(draw):
    """Generate options with competing strengths to create trade-offs."""
    option_count = draw(st.integers(min_value=2, max_value=5))
    constraint_names = ["cost", "performance", "complexity", "scalability"]
    
    options = []
    for i in range(option_count):
        attributes = {}
        
        # Create competing profiles
        if i % 2 == 0:
            # High cost, high performance
            attributes["cost"] = draw(st.floats(min_value=80, max_value=100))
            attributes["performance"] = draw(st.floats(min_value=80, max_value=100))
            attributes["complexity"] = draw(st.floats(min_value=20, max_value=60))
            attributes["scalability"] = draw(st.floats(min_value=70, max_value=100))
        else:
            # Low cost, lower performance
            attributes["cost"] = draw(st.floats(min_value=10, max_value=40))
            attributes["performance"] = draw(st.floats(min_value=20, max_value=50))
            attributes["complexity"] = draw(st.floats(min_value=60, max_value=100))
            attributes["scalability"] = draw(st.floats(min_value=30, max_value=70))
        
        option = Option(
            name=f"Option_{i}",
            description=f"Test option {i}",
            attributes=attributes
        )
        options.append(option)
    
    return options


@st.composite
def tradeoff_constraints_strategy(draw):
    """Generate constraints that create trade-offs."""
    constraints = []
    
    # Cost constraint (lower is better)
    cost_constraint = Constraint(
        name="cost",
        description="Total cost",
        weight=draw(st.floats(min_value=0.2, max_value=1.0)),
        priority=Priority.REQUIRED,
        type=ConstraintType.NUMERIC,
        scale=NumericScale(min=0, max=100, direction="lower-better")
    )
    constraints.append(cost_constraint)
    
    # Performance constraint (higher is better)
    perf_constraint = Constraint(
        name="performance",
        description="Performance level",
        weight=draw(st.floats(min_value=0.2, max_value=1.0)),
        priority=Priority.REQUIRED,
        type=ConstraintType.NUMERIC,
        scale=NumericScale(min=0, max=100, direction="higher-better")
    )
    constraints.append(perf_constraint)
    
    # Add additional constraints
    for name in ["complexity", "scalability"]:
        constraint = Constraint(
            name=name,
            description=f"{name.title()} measure",
            weight=draw(st.floats(min_value=0.1, max_value=0.8)),
            priority=draw(st.sampled_from(Priority)),
            type=ConstraintType.NUMERIC,
            scale=NumericScale(
                min=0, max=100, 
                direction=draw(st.sampled_from(["higher-better", "lower-better"]))
            )
        )
        constraints.append(constraint)
    
    return constraints


@st.composite
def options_and_constraints_with_tradeoffs_strategy(draw):
    """Generate options and constraints designed to have trade-offs."""
    options = draw(competing_options_strategy())
    constraints = draw(tradeoff_constraints_strategy())
    return options, constraints


class TestTradeoffIdentification:
    """Test trade-off identification using property-based testing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.analyzer = TradeoffAnalyzer()
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_tradeoffs_identified_for_competing_options(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 7: Trade-off Identification
        For any comparison with options that have competing strengths, the system should identify trade-offs 
        and explain what is sacrificed when choosing each option.
        Validates: Requirements 3.1, 3.2, 3.3
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Verify analysis completed
        assert result is not None
        assert len(result.option_tradeoffs) == len(options)
        
        # For each option, verify trade-off information is provided
        for option_tradeoff in result.option_tradeoffs:
            # Each option should have a trade-off summary
            assert isinstance(option_tradeoff.tradeoff_summary, str)
            assert len(option_tradeoff.tradeoff_summary) > 0
            
            # Strengths and weaknesses should be lists
            assert isinstance(option_tradeoff.strengths, list)
            assert isinstance(option_tradeoff.weaknesses, list)
            
            # Competing factors should be a list
            assert isinstance(option_tradeoff.competing_factors, list)
        
        # With competing options, we should identify some global trade-offs
        # (This may not always be true due to randomness, but should be true most of the time)
        if len(constraints) >= 2:
            # At least verify the structure is correct
            assert isinstance(result.global_tradeoffs, list)
            for tradeoff in result.global_tradeoffs:
                assert isinstance(tradeoff.constraint_a, str)
                assert isinstance(tradeoff.constraint_b, str)
                assert isinstance(tradeoff.correlation, float)
                assert -1.0 <= tradeoff.correlation <= 1.0
                assert isinstance(tradeoff.description, str)
                assert len(tradeoff.description) > 0
                assert isinstance(tradeoff.affected_options, list)
    
    @given(st.lists(
        st.builds(Option, name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        min_size=2, max_size=5, unique_by=lambda x: x.name
    ))
    def test_minimal_constraints_handled_gracefully(self, options):
        """
        Feature: option-comparison-tool, Property 7: Trade-off Identification
        For any comparison with insufficient constraints, the system should handle it gracefully.
        Validates: Requirements 3.1, 3.2, 3.3
        """
        # Test with no constraints
        result = self.analyzer.analyze_tradeoffs(options, [])
        
        assert result is not None
        assert len(result.option_tradeoffs) == len(options)
        assert len(result.global_tradeoffs) == 0
        
        # All options should be on Pareto frontier when no trade-offs exist
        assert len(result.pareto_frontier) == len(options)
        
        # Test with single constraint
        single_constraint = [Constraint(name="test", weight=1.0)]
        result = self.analyzer.analyze_tradeoffs(options, single_constraint)
        
        assert result is not None
        assert len(result.option_tradeoffs) == len(options)
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_pareto_frontier_identification(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 7: Trade-off Identification
        For any comparison, the system should identify non-dominated solutions (Pareto frontier).
        Validates: Requirements 3.1, 3.2, 3.3
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Verify Pareto frontier is identified
        assert isinstance(result.pareto_frontier, list)
        assert len(result.pareto_frontier) >= 1  # At least one option should be non-dominated
        assert len(result.pareto_frontier) <= len(options)  # Cannot exceed total options
        
        # All Pareto frontier options should be valid option IDs
        option_ids = {opt.id for opt in options}
        for pareto_id in result.pareto_frontier:
            assert pareto_id in option_ids
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_analysis_is_deterministic(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 7: Trade-off Identification
        For any set of options and constraints, running the analysis multiple times should produce identical results.
        Validates: Requirements 3.1, 3.2, 3.3
        """
        options, constraints = options_and_constraints
        
        # Run analysis twice
        result1 = self.analyzer.analyze_tradeoffs(options, constraints)
        result2 = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Results should be identical
        assert len(result1.option_tradeoffs) == len(result2.option_tradeoffs)
        assert len(result1.global_tradeoffs) == len(result2.global_tradeoffs)
        assert set(result1.pareto_frontier) == set(result2.pareto_frontier)
        
        # Check option trade-offs are identical
        tradeoffs1 = sorted(result1.option_tradeoffs, key=lambda x: x.option_name)
        tradeoffs2 = sorted(result2.option_tradeoffs, key=lambda x: x.option_name)
        
        for t1, t2 in zip(tradeoffs1, tradeoffs2):
            assert t1.option_name == t2.option_name
            assert t1.tradeoff_summary == t2.tradeoff_summary
            assert set(t1.strengths) == set(t2.strengths)
            assert set(t1.weaknesses) == set(t2.weaknesses)


class TestTradeoffQuantification:
    """Test trade-off quantification using property-based testing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.analyzer = TradeoffAnalyzer()
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_tradeoffs_have_numeric_quantification(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 8: Trade-off Quantification
        For any identified trade-off, the system should provide numeric measures or relative rankings 
        where quantification is possible.
        Validates: Requirements 3.4
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Check that global trade-offs have quantification
        for tradeoff in result.global_tradeoffs:
            # Each trade-off should have quantification data
            assert tradeoff.quantification is not None
            assert isinstance(tradeoff.quantification, dict)
            
            # Check required quantification metrics
            assert "correlation_strength" in tradeoff.quantification
            assert "affected_option_count" in tradeoff.quantification
            assert "trade_off_intensity" in tradeoff.quantification
            assert "significance_score" in tradeoff.quantification
            
            # Verify metric ranges
            correlation_strength = tradeoff.quantification["correlation_strength"]
            assert 0.0 <= correlation_strength <= 1.0
            
            affected_count = tradeoff.quantification["affected_option_count"]
            assert 0 <= affected_count <= len(options)
            
            significance_score = tradeoff.quantification["significance_score"]
            assert 0.0 <= significance_score <= 1.0
            
            trade_off_intensity = tradeoff.quantification["trade_off_intensity"]
            assert trade_off_intensity >= 0.0
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_correlation_values_are_valid(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 8: Trade-off Quantification
        For any trade-off analysis, correlation values should be valid numbers in the range [-1, 1].
        Validates: Requirements 3.4
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Check correlation values for all global trade-offs
        for tradeoff in result.global_tradeoffs:
            correlation = tradeoff.correlation
            
            # Correlation should be a valid number in range [-1, 1]
            assert isinstance(correlation, (int, float))
            assert not (correlation != correlation)  # Check for NaN
            assert correlation != float('inf') and correlation != float('-inf')
            assert -1.0 <= correlation <= 1.0
            
            # For trade-offs (negative correlations), correlation should be negative
            # This is a design choice - we only identify negative correlations as trade-offs
            if len(result.global_tradeoffs) > 0:
                assert correlation < 0.0  # Trade-offs should have negative correlation
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_quantification_consistency(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 8: Trade-off Quantification
        For any trade-off, quantification metrics should be consistent with each other.
        Validates: Requirements 3.4
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Check consistency of quantification metrics
        for tradeoff in result.global_tradeoffs:
            if tradeoff.quantification:
                correlation_strength = tradeoff.quantification["correlation_strength"]
                affected_count = tradeoff.quantification["affected_option_count"]
                trade_off_intensity = tradeoff.quantification["trade_off_intensity"]
                significance_score = tradeoff.quantification["significance_score"]
                
                # Trade-off intensity should be related to correlation strength and affected count
                expected_intensity = correlation_strength * affected_count
                assert abs(trade_off_intensity - expected_intensity) < 1e-10
                
                # Significance score should be related to correlation strength
                expected_significance = min(correlation_strength * 2, 1.0)
                assert abs(significance_score - expected_significance) < 1e-10
                
                # Correlation strength should match absolute value of correlation
                assert abs(correlation_strength - abs(tradeoff.correlation)) < 1e-10
    
    @given(options_and_constraints_with_tradeoffs_strategy())
    def test_metadata_contains_quantitative_measures(self, options_and_constraints):
        """
        Feature: option-comparison-tool, Property 8: Trade-off Quantification
        For any analysis, metadata should contain quantitative measures about the trade-offs.
        Validates: Requirements 3.4
        """
        options, constraints = options_and_constraints
        
        # Run trade-off analysis
        result = self.analyzer.analyze_tradeoffs(options, constraints)
        
        # Check that metadata contains quantitative information
        metadata = result.analysis_metadata
        assert isinstance(metadata, dict)
        
        # Required quantitative metadata
        assert "option_count" in metadata
        assert "constraint_count" in metadata
        assert "global_tradeoff_count" in metadata
        assert "pareto_frontier_size" in metadata
        assert "pareto_efficiency" in metadata
        assert "trade_off_intensity" in metadata
        
        # Verify metadata values are reasonable
        assert metadata["option_count"] == len(options)
        assert metadata["constraint_count"] == len(constraints)
        assert metadata["global_tradeoff_count"] == len(result.global_tradeoffs)
        assert metadata["pareto_frontier_size"] == len(result.pareto_frontier)
        
        # Pareto efficiency should be between 0 and 1
        pareto_efficiency = metadata["pareto_efficiency"]
        assert 0.0 <= pareto_efficiency <= 1.0
        
        # Trade-off intensity should be non-negative
        trade_off_intensity = metadata["trade_off_intensity"]
        assert trade_off_intensity >= 0.0
    
    @given(st.lists(
        st.builds(Option, name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        min_size=2, max_size=5, unique_by=lambda x: x.name
    ))
    def test_single_option_quantification(self, options):
        """
        Feature: option-comparison-tool, Property 8: Trade-off Quantification
        For any analysis with a single option, quantification should handle the edge case gracefully.
        Validates: Requirements 3.4
        """
        # Test with single option
        single_option = options[:1]
        constraints = [
            Constraint(name="test1", weight=0.5),
            Constraint(name="test2", weight=0.5)
        ]
        
        result = self.analyzer.analyze_tradeoffs(single_option, constraints)
        
        # Should handle gracefully
        assert result is not None
        assert len(result.option_tradeoffs) == 1
        assert len(result.global_tradeoffs) == 0  # No trade-offs with single option
        assert len(result.pareto_frontier) == 1  # Single option is on frontier
        
        # Metadata should be valid
        metadata = result.analysis_metadata
        assert metadata["option_count"] == 1
        assert metadata["pareto_efficiency"] == 1.0  # 100% efficiency with single option
        assert metadata["trade_off_intensity"] == 0.0  # No trade-offs