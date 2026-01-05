"""
Property-based tests for ComparisonManager constraint validation.

Feature: option-comparison-tool
Property 2: Constraint Validation
Validates: Requirements 1.3
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, assume
from option_comparison_tool.models import (
    Option, Constraint, ConstraintType, Priority, NumericScale, CategoricalScale
)
from option_comparison_tool.comparison_manager import ComparisonManager


# Hypothesis strategies for generating test data
@st.composite
def valid_option_strategy(draw):
    """Generate valid Option instances."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    # Ensure at least one of description or attributes is non-empty
    has_description = draw(st.booleans())
    has_attributes = draw(st.booleans())
    
    # If both are False, force at least one to be True
    if not has_description and not has_attributes:
        has_description = True
    
    description = draw(st.text(min_size=1, max_size=500)) if has_description else ""
    attributes = draw(st.dictionaries(
        st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        st.one_of(st.text(), st.integers(), st.floats(), st.booleans()),
        min_size=1, max_size=20
    )) if has_attributes else {}
    
    return Option(
        name=name,
        description=description,
        attributes=attributes
    )


@st.composite
def valid_constraint_strategy(draw):
    """Generate valid Constraint instances."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    return Constraint(
        name=name,
        description=draw(st.text(max_size=500)),
        weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        priority=draw(st.sampled_from(Priority)),
        type=draw(st.sampled_from(ConstraintType))
    )


@st.composite
def invalid_constraint_strategy(draw):
    """Generate invalid Constraint instances for testing validation."""
    constraint_type = draw(st.sampled_from(['empty_name', 'whitespace_name', 'invalid_weight']))
    
    if constraint_type == 'empty_name':
        return Constraint(
            name="",  # Invalid: empty name
            description=draw(st.text(max_size=500)),
            weight=draw(st.floats(min_value=0.0, max_value=1.0))
        )
    elif constraint_type == 'whitespace_name':
        return Constraint(
            name="   ",  # Invalid: whitespace-only name
            description=draw(st.text(max_size=500)),
            weight=draw(st.floats(min_value=0.0, max_value=1.0))
        )
    else:  # invalid_weight
        valid_name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
        invalid_weight = draw(st.one_of(
            st.floats(min_value=-10.0, max_value=-0.1),  # Negative weights
            st.floats(min_value=1.1, max_value=10.0)     # Weights > 1.0
        ))
        return Constraint(
            name=valid_name,
            description=draw(st.text(max_size=500)),
            weight=invalid_weight
        )


@st.composite
def options_with_missing_info_strategy(draw):
    """Generate options with missing essential information."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    return Option(
        name=name,
        description="",  # Empty description
        attributes={}    # Empty attributes - violates requirement 1.3
    )


class TestConstraintValidation:
    """Test constraint validation using property-based testing."""
    
    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ComparisonManager(data_dir=Path(self.temp_dir))
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10),
           st.lists(valid_constraint_strategy(), min_size=1, max_size=20))
    def test_valid_constraints_are_accepted(self, options, constraints):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any option with complete required fields, the system should accept and process it.
        Validates: Requirements 1.3
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough unique options
        assume(len(unique_options) >= 2)
        
        # Should not raise any exception
        session = self.manager.create_comparison(unique_options, unique_constraints)
        assert session is not None
        assert len(session.options) == len(unique_options)
        assert len(session.constraints) == len(unique_constraints)
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10))
    def test_empty_constraints_list_is_accepted(self, options):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any comparison, an empty constraints list should be accepted.
        Validates: Requirements 1.3
        """
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough unique options
        assume(len(unique_options) >= 2)
        
        # Empty constraints should be allowed
        session = self.manager.create_comparison(unique_options, [])
        assert session is not None
        assert len(session.constraints) == 0
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10),
           st.lists(valid_constraint_strategy(), min_size=2, max_size=10))
    def test_duplicate_constraint_names_are_rejected(self, options, constraints):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any constraints with duplicate names, the system should reject them.
        Validates: Requirements 1.3
        """
        assume(len(constraints) >= 2)
        
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough unique options
        assume(len(unique_options) >= 2)
        
        # Make the first two constraints have the same name
        constraints[1].name = constraints[0].name
        
        with pytest.raises(ValueError, match="Constraint names must be unique"):
            self.manager.create_comparison(unique_options, constraints)
    
    @given(st.lists(options_with_missing_info_strategy(), min_size=2, max_size=10))
    def test_options_with_missing_essential_info_are_rejected(self, options):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any option with missing essential information, the system should identify and report it.
        Validates: Requirements 1.3
        """
        # Ensure option names are unique by modifying names
        for i, option in enumerate(options):
            option.name = f"Option_{i}"
        
        # Skip if we don't have enough options
        assume(len(options) >= 2)
        
        # Should raise ValueError for missing essential information
        with pytest.raises(ValueError, match="is missing both description and attributes"):
            self.manager.create_comparison(options, [])
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10))
    def test_invalid_constraint_weights_are_rejected(self, options):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any constraint with invalid weight, the system should reject it.
        Validates: Requirements 1.3
        """
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough unique options
        assume(len(unique_options) >= 2)
        
        # This should fail during constraint creation, not in ComparisonManager
        with pytest.raises(ValueError, match="Constraint weight must be between 0.0 and 1.0"):
            invalid_constraint = Constraint(name="Test", weight=1.5)  # Invalid weight > 1.0
            self.manager.create_comparison(unique_options, [invalid_constraint])
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10))
    def test_constraints_with_empty_names_are_rejected(self, options):
        """
        Feature: option-comparison-tool, Property 2: Constraint Validation
        For any constraint with empty name, the system should reject it.
        Validates: Requirements 1.3
        """
        # Ensure option names are unique
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names:
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough unique options
        assume(len(unique_options) >= 2)
        
        # This should fail during constraint creation due to empty name
        with pytest.raises(ValueError, match="Constraint name cannot be empty"):
            invalid_constraint = Constraint(name="", weight=0.5)
            self.manager.create_comparison(unique_options, [invalid_constraint])


class TestCapacityConstraints:
    """Test capacity constraint validation using property-based testing."""
    
    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ComparisonManager(data_dir=Path(self.temp_dir))
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=10))
    def test_valid_capacity_ranges_are_accepted(self, options):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any comparison session with 2-10 options, the system should accept and process all options.
        Validates: Requirements 1.4
        """
        # Ensure option names are unique and have required info
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names and (option.description or option.attributes):
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough valid options after filtering
        assume(len(unique_options) >= 2)
        
        # Should not raise any exception for valid capacity range
        session = self.manager.create_comparison(unique_options, [])
        assert session is not None
        assert len(session.options) == len(unique_options)
        assert 2 <= len(session.options) <= 10
    
    @given(valid_option_strategy())
    def test_single_option_is_rejected(self, option):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any comparison session with fewer than 2 options, the system should enforce appropriate limits.
        Validates: Requirements 1.4
        """
        # Ensure option has required info
        if not option.description and not option.attributes:
            option.description = "Test description"
        
        with pytest.raises(ValueError, match="Comparison must have at least 2 options"):
            self.manager.create_comparison([option], [])
    
    def test_empty_options_list_is_rejected(self):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any comparison session with no options, the system should enforce appropriate limits.
        Validates: Requirements 1.4
        """
        with pytest.raises(ValueError, match="At least one option is required"):
            self.manager.create_comparison([], [])
    
    @given(st.lists(valid_option_strategy(), min_size=11, max_size=15))
    def test_too_many_options_are_rejected(self, options):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any comparison session with more than 10 options, the system should enforce appropriate limits.
        Validates: Requirements 1.4
        """
        # Ensure option names are unique and have required info
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names and (option.description or option.attributes):
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough options after filtering
        assume(len(unique_options) > 10)
        
        with pytest.raises(ValueError, match="Comparison cannot have more than 10 options"):
            self.manager.create_comparison(unique_options, [])
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=9))
    def test_adding_option_within_capacity_succeeds(self, options):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any session with fewer than 10 options, adding one more option should succeed.
        Validates: Requirements 1.4
        """
        # Ensure option names are unique and have required info
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names and (option.description or option.attributes):
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough valid options
        assume(len(unique_options) >= 2)
        
        # Create session with initial options
        session = self.manager.create_comparison(unique_options, [])
        
        # Create a new option with unique name
        new_option = Option(
            name=f"New Option {len(unique_options) + 1}",
            description="A new test option"
        )
        
        # Should be able to add the option
        initial_count = len(session.options)
        updated_session = self.manager.add_option_to_session(session.id, new_option)
        assert len(updated_session.options) == initial_count + 1
        assert new_option.name in [opt.name for opt in updated_session.options]
    
    @given(st.lists(valid_option_strategy(), min_size=10, max_size=10))
    def test_adding_option_to_full_session_fails(self, options):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any session with 10 options, adding another option should fail.
        Validates: Requirements 1.4
        """
        # Ensure option names are unique and have required info
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names and (option.description or option.attributes):
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have exactly 10 valid options
        assume(len(unique_options) == 10)
        
        # Create session with maximum options
        session = self.manager.create_comparison(unique_options, [])
        
        # Create a new option
        new_option = Option(
            name="Overflow Option",
            description="This should not be added"
        )
        
        # Should fail to add the option
        with pytest.raises(ValueError, match="Cannot add option: session already has maximum"):
            self.manager.add_option_to_session(session.id, new_option)
    
    @given(st.lists(valid_option_strategy(), min_size=2, max_size=9))
    def test_can_add_option_check_is_accurate(self, options):
        """
        Feature: option-comparison-tool, Property 3: Capacity Constraints
        For any session, can_add_option should accurately reflect capacity constraints.
        Validates: Requirements 1.4
        """
        # Ensure option names are unique and have required info
        unique_options = []
        seen_names = set()
        for option in options:
            if option.name not in seen_names and (option.description or option.attributes):
                unique_options.append(option)
                seen_names.add(option.name)
        
        # Skip if we don't have enough valid options
        assume(len(unique_options) >= 2)
        
        # Create session
        session = self.manager.create_comparison(unique_options, [])
        
        # Check capacity
        can_add = self.manager.can_add_option(session.id)
        expected_can_add = len(session.options) < 10
        
        assert can_add == expected_can_add