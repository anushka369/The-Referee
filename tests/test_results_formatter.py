"""
Property-based tests for ResultsFormatter functionality.

Tests Properties 9, 10, and 11 from the design document:
- Property 9: Multi-format Output
- Property 10: Differentiator Highlighting  
- Property 11: Categorical Organization
"""

import pytest
from hypothesis import given, strategies as st, assume
from typing import List, Dict, Any

from option_comparison_tool.models import Option, Constraint, ConstraintType, Priority
from option_comparison_tool.weighted_scoring import WeightedScoringAnalyzer, OptionScore, ScoringResult
from option_comparison_tool.tradeoff_analyzer import TradeoffAnalyzer, OptionTradeoff, TradeoffResult
from option_comparison_tool.results_formatter import ResultsFormatter, OutputFormat


# Generators for test data
@st.composite
def generate_option(draw):
    """Generate a valid Option for testing."""
    name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    description = draw(st.text(max_size=200))
    
    # Generate attributes with some numeric values for scoring
    num_attributes = draw(st.integers(min_value=1, max_value=5))
    attributes = {}
    for i in range(num_attributes):
        attr_name = f"attr_{i}"
        attr_value = draw(st.one_of(
            st.floats(min_value=0, max_value=100),
            st.integers(min_value=0, max_value=100),
            st.booleans(),
            st.sampled_from(["low", "medium", "high"])
        ))
        attributes[attr_name] = attr_value
    
    return Option(name=name, description=description, attributes=attributes)


@st.composite
def generate_constraint(draw):
    """Generate a valid Constraint for testing."""
    name = draw(st.text(min_size=1, max_size=30).filter(lambda x: x.strip()))
    description = draw(st.text(max_size=100))
    weight = draw(st.floats(min_value=0.0, max_value=1.0))
    priority = draw(st.sampled_from(list(Priority)))
    constraint_type = draw(st.sampled_from(list(ConstraintType)))
    
    return Constraint(
        name=name,
        description=description,
        weight=weight,
        priority=priority,
        type=constraint_type
    )


@st.composite
def generate_options_and_constraints(draw):
    """Generate a valid set of options and constraints for testing."""
    # Generate 2-5 options
    num_options = draw(st.integers(min_value=2, max_value=5))
    options = []
    option_names = set()
    
    for _ in range(num_options):
        option = draw(generate_option())
        # Ensure unique names
        while option.name in option_names:
            option.name = option.name + "_" + str(len(option_names))
        option_names.add(option.name)
        options.append(option)
    
    # Generate 1-4 constraints
    num_constraints = draw(st.integers(min_value=1, max_value=4))
    constraints = []
    constraint_names = set()
    
    for _ in range(num_constraints):
        constraint = draw(generate_constraint())
        # Ensure unique names
        while constraint.name in constraint_names:
            constraint.name = constraint.name + "_" + str(len(constraint_names))
        constraint_names.add(constraint.name)
        
        # Ensure all options have this constraint attribute
        for option in options:
            if constraint.name not in option.attributes:
                if constraint.type == ConstraintType.NUMERIC:
                    option.attributes[constraint.name] = draw(st.floats(min_value=0, max_value=100))
                elif constraint.type == ConstraintType.BOOLEAN:
                    option.attributes[constraint.name] = draw(st.booleans())
                else:  # CATEGORICAL
                    option.attributes[constraint.name] = draw(st.sampled_from(["low", "medium", "high"]))
        
        constraints.append(constraint)
    
    return options, constraints


class TestResultsFormatterProperties:
    """Property-based tests for ResultsFormatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResultsFormatter()
        self.scoring_analyzer = WeightedScoringAnalyzer()
        self.tradeoff_analyzer = TradeoffAnalyzer()
    
    @given(generate_options_and_constraints())
    def test_property_9_multi_format_output(self, options_and_constraints):
        """
        Property 9: Multi-format Output
        For any completed comparison, the system should generate results in all specified formats.
        **Validates: Requirements 4.1**
        """
        options, constraints = options_and_constraints
        assume(len(options) >= 2 and len(constraints) >= 1)
        
        # Generate analysis results
        scoring_result = self.scoring_analyzer.analyze(options, constraints)
        tradeoff_result = self.tradeoff_analyzer.analyze_tradeoffs(options, constraints)
        
        # Test that all supported formats can be generated
        supported_formats = [OutputFormat.TABLE, OutputFormat.PROS_CONS, 
                           OutputFormat.SUMMARY_CARDS, OutputFormat.DETAILED_REPORT]
        
        for format_type in supported_formats:
            formatted_result = self.formatter.format_results(
                scoring_result, tradeoff_result, constraints, format_type
            )
            
            # Verify the result has the expected format type
            assert formatted_result.format_type == format_type
            
            # Verify content is not empty
            assert formatted_result.content is not None
            assert len(formatted_result.content) > 0
            
            # Verify metadata is present
            assert formatted_result.metadata is not None
            assert formatted_result.metadata["format_type"] == format_type.value
            assert formatted_result.metadata["option_count"] == len(options)
            assert formatted_result.metadata["constraint_count"] == len(constraints)
    
    @given(generate_options_and_constraints())
    def test_property_10_differentiator_highlighting(self, options_and_constraints):
        """
        Property 10: Differentiator Highlighting
        For any comparison results, the system should identify and highlight 
        the most significant differences between options.
        **Validates: Requirements 4.2**
        """
        options, constraints = options_and_constraints
        assume(len(options) >= 2 and len(constraints) >= 1)
        
        # Generate analysis results
        scoring_result = self.scoring_analyzer.analyze(options, constraints)
        tradeoff_result = self.tradeoff_analyzer.analyze_tradeoffs(options, constraints)
        
        # Test differentiator identification
        differentiators = self.formatter.identify_differentiators(scoring_result, constraints)
        
        # Verify differentiators are identified for all options
        assert len(differentiators) == len(options)
        
        # Verify each option has differentiators as a list
        for option in options:
            assert option.name in differentiators
            assert isinstance(differentiators[option.name], list)
        
        # Test that differentiators are included in table format
        table_result = self.formatter.format_results(
            scoring_result, tradeoff_result, constraints, OutputFormat.TABLE
        )
        
        # Verify differentiators are present in table rows
        for row in table_result.content["rows"]:
            assert "differentiators" in row
            assert isinstance(row["differentiators"], list)
            
            # Verify differentiators match what was identified
            option_name = row["option_name"]
            expected_differentiators = differentiators[option_name]
            assert row["differentiators"] == expected_differentiators
    
    @given(generate_options_and_constraints())
    def test_property_11_categorical_organization(self, options_and_constraints):
        """
        Property 11: Categorical Organization
        For any pros and cons display, items should be organized and grouped 
        by their corresponding constraint categories.
        **Validates: Requirements 4.3**
        """
        options, constraints = options_and_constraints
        assume(len(options) >= 2 and len(constraints) >= 1)
        
        # Generate analysis results
        scoring_result = self.scoring_analyzer.analyze(options, constraints)
        tradeoff_result = self.tradeoff_analyzer.analyze_tradeoffs(options, constraints)
        
        # Test pros/cons format which should have categorical organization
        pros_cons_result = self.formatter.format_results(
            scoring_result, tradeoff_result, constraints, OutputFormat.PROS_CONS
        )
        
        # Verify categorical organization exists
        assert "options" in pros_cons_result.content
        assert "category_legend" in pros_cons_result.content
        
        # Verify each option has categorized pros and cons
        for option_data in pros_cons_result.content["options"]:
            assert "pros_by_category" in option_data
            assert "cons_by_category" in option_data
            
            pros_by_category = option_data["pros_by_category"]
            cons_by_category = option_data["cons_by_category"]
            
            # Verify categories are dictionaries
            assert isinstance(pros_by_category, dict)
            assert isinstance(cons_by_category, dict)
            
            # Verify valid category names are used
            valid_categories = {"Required", "Preferred", "Nice-to-Have", "Other"}
            for category in pros_by_category.keys():
                assert category in valid_categories
            for category in cons_by_category.keys():
                assert category in valid_categories
            
            # Verify each category contains a list of items
            for category, items in pros_by_category.items():
                assert isinstance(items, list)
            for category, items in cons_by_category.items():
                assert isinstance(items, list)
        
        # Test the organize_by_categories method directly
        test_items = [constraint.name for constraint in constraints]
        organized = self.formatter.organize_by_categories(test_items, constraints)
        
        # Verify organization produces valid categories
        assert isinstance(organized, dict)
        for category, items in organized.items():
            assert category in valid_categories
            assert isinstance(items, list)
        
        # Verify all items are categorized (no items lost)
        total_categorized = sum(len(items) for items in organized.values())
        assert total_categorized == len(test_items)


class TestResultsFormatterUnitTests:
    """Unit tests for specific ResultsFormatter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResultsFormatter()
    
    def test_format_results_with_empty_scoring_result_raises_error(self):
        """Test that formatting with empty scoring result raises ValueError."""
        from option_comparison_tool.tradeoff_analyzer import TradeoffResult
        
        empty_scoring_result = ScoringResult(option_scores=[], total_weight=0.0, analysis_metadata={})
        tradeoff_result = TradeoffResult(
            option_tradeoffs=[], global_tradeoffs=[], pareto_frontier=[], analysis_metadata={}
        )
        
        with pytest.raises(ValueError, match="Scoring result is required and must contain option scores"):
            self.formatter.format_results(
                empty_scoring_result, tradeoff_result, [], OutputFormat.TABLE
            )
    
    def test_format_results_with_none_tradeoff_result_raises_error(self):
        """Test that formatting with None trade-off result raises ValueError."""
        # Create minimal scoring result
        option_score = OptionScore(
            option_id="test", option_name="Test", total_score=1.0,
            constraint_scores={}, normalized_scores={}
        )
        scoring_result = ScoringResult(
            option_scores=[option_score], total_weight=1.0, analysis_metadata={}
        )
        
        with pytest.raises(ValueError, match="Trade-off result is required"):
            self.formatter.format_results(scoring_result, None, [], OutputFormat.TABLE)
    
    def test_format_results_with_unsupported_format_raises_error(self):
        """Test that formatting with unsupported format raises ValueError."""
        # Create minimal valid inputs
        option_score = OptionScore(
            option_id="test", option_name="Test", total_score=1.0,
            constraint_scores={}, normalized_scores={}
        )
        scoring_result = ScoringResult(
            option_scores=[option_score], total_weight=1.0, analysis_metadata={}
        )
        
        from option_comparison_tool.tradeoff_analyzer import TradeoffResult
        tradeoff_result = TradeoffResult(
            option_tradeoffs=[], global_tradeoffs=[], pareto_frontier=[], analysis_metadata={}
        )
        
        # Test with a mock format that doesn't exist in the enum
        # We'll create a mock object that has the same interface but invalid value
        class MockFormat:
            def __init__(self, value):
                self.value = value
        
        mock_format = MockFormat("UNSUPPORTED_FORMAT")
        
        with pytest.raises(ValueError, match="Unsupported format type"):
            self.formatter.format_results(scoring_result, tradeoff_result, [], mock_format)
    
    def test_identify_differentiators_with_single_option_returns_empty(self):
        """Test that differentiator identification with single option returns empty dict."""
        option_score = OptionScore(
            option_id="test", option_name="Test", total_score=1.0,
            constraint_scores={}, normalized_scores={}
        )
        scoring_result = ScoringResult(
            option_scores=[option_score], total_weight=1.0, analysis_metadata={}
        )
        
        differentiators = self.formatter.identify_differentiators(scoring_result, [])
        assert differentiators == {}
    
    def test_organize_by_categories_with_empty_items_returns_empty(self):
        """Test that organizing empty items returns empty dict."""
        constraint = Constraint(name="test", priority=Priority.REQUIRED)
        organized = self.formatter.organize_by_categories([], [constraint])
        assert organized == {}
    
    def test_organize_by_categories_removes_empty_categories(self):
        """Test that empty categories are removed from organization results."""
        constraints = [
            Constraint(name="required_item", priority=Priority.REQUIRED),
            Constraint(name="preferred_item", priority=Priority.PREFERRED)
        ]
        items = ["required_item"]  # Only one item, so other categories will be empty
        
        organized = self.formatter.organize_by_categories(items, constraints)
        
        # Should only contain categories with items
        assert "Required" in organized
        assert len(organized["Required"]) == 1
        
        # Empty categories should not be present
        assert "Preferred" not in organized or len(organized["Preferred"]) == 0
        assert "Nice-to-Have" not in organized or len(organized["Nice-to-Have"]) == 0