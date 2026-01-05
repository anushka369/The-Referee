"""
Property-based tests for data model persistence.

Feature: option-comparison-tool
Property 1: Data Persistence Round Trip
Validates: Requirements 1.1, 1.2
"""

import json
import pickle
from copy import deepcopy
from hypothesis import given, strategies as st
from option_comparison_tool.models import (
    Option, Constraint, ComparisonSession, 
    ConstraintType, Priority, NumericScale, CategoricalScale
)


# Hypothesis strategies for generating test data
@st.composite
def numeric_scale_strategy(draw):
    """Generate valid NumericScale instances."""
    min_val = draw(st.floats(min_value=-1000, max_value=1000))
    max_val = draw(st.floats(min_value=min_val + 0.1, max_value=min_val + 1000))
    return NumericScale(
        min=min_val,
        max=max_val,
        unit=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10))),
        direction=draw(st.sampled_from(["higher-better", "lower-better"])),
        normalization_method=draw(st.sampled_from(["min-max", "z-score"]))
    )


@st.composite
def categorical_scale_strategy(draw):
    """Generate valid CategoricalScale instances."""
    values = draw(st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=10, unique=True))
    scores = draw(st.lists(st.floats(min_value=0, max_value=100), min_size=len(values), max_size=len(values)))
    return CategoricalScale(
        values=values,
        scores=scores,
        ordered=draw(st.booleans())
    )


@st.composite
def option_strategy(draw):
    """Generate valid Option instances."""
    # Generate non-empty, non-whitespace names
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    return Option(
        name=name,
        description=draw(st.text(max_size=500)),
        attributes=draw(st.dictionaries(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            st.one_of(st.text(), st.integers(), st.floats().filter(lambda x: not (x != x)), st.booleans()),
            max_size=20
        )),
        metadata=draw(st.dictionaries(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            st.text(),
            max_size=10
        ))
    )


@st.composite
def constraint_strategy(draw):
    """Generate valid Constraint instances."""
    constraint_type = draw(st.sampled_from(ConstraintType))
    
    # Generate appropriate scale based on constraint type
    scale = None
    if constraint_type == ConstraintType.NUMERIC:
        scale = draw(st.one_of(st.none(), numeric_scale_strategy()))
    elif constraint_type == ConstraintType.CATEGORICAL:
        scale = draw(st.one_of(st.none(), categorical_scale_strategy()))
    
    # Generate non-empty, non-whitespace names
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    
    return Constraint(
        name=name,
        description=draw(st.text(max_size=500)),
        weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        priority=draw(st.sampled_from(Priority)),
        type=constraint_type,
        scale=scale
    )


@st.composite
def comparison_session_strategy(draw):
    """Generate valid ComparisonSession instances."""
    options = draw(st.lists(option_strategy(), min_size=2, max_size=10))
    constraints = draw(st.lists(constraint_strategy(), min_size=0, max_size=20))
    
    return ComparisonSession(
        options=options,
        constraints=constraints,
        template=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    )


class TestDataPersistence:
    """Test data model persistence using property-based testing."""

    @given(option_strategy())
    def test_option_deepcopy_round_trip(self, option):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid option, deep copying and retrieving should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Deep copy the option (simulates serialization/deserialization)
        copied_option = deepcopy(option)
        
        # Verify all fields are preserved
        assert copied_option.name == option.name
        assert copied_option.description == option.description
        assert copied_option.attributes == option.attributes
        assert copied_option.metadata == option.metadata
        assert copied_option.id == option.id

    @given(constraint_strategy())
    def test_constraint_deepcopy_round_trip(self, constraint):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid constraint, deep copying and retrieving should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Deep copy the constraint
        copied_constraint = deepcopy(constraint)
        
        # Verify all fields are preserved
        assert copied_constraint.name == constraint.name
        assert copied_constraint.description == constraint.description
        assert copied_constraint.weight == constraint.weight
        assert copied_constraint.priority == constraint.priority
        assert copied_constraint.type == constraint.type
        assert copied_constraint.id == constraint.id
        
        # Verify scale is preserved if present
        if constraint.scale is not None:
            assert copied_constraint.scale is not None
            if isinstance(constraint.scale, NumericScale):
                assert copied_constraint.scale.min == constraint.scale.min
                assert copied_constraint.scale.max == constraint.scale.max
                assert copied_constraint.scale.unit == constraint.scale.unit
                assert copied_constraint.scale.direction == constraint.scale.direction
                assert copied_constraint.scale.normalization_method == constraint.scale.normalization_method
            elif isinstance(constraint.scale, CategoricalScale):
                assert copied_constraint.scale.values == constraint.scale.values
                assert copied_constraint.scale.scores == constraint.scale.scores
                assert copied_constraint.scale.ordered == constraint.scale.ordered

    @given(comparison_session_strategy())
    def test_comparison_session_deepcopy_round_trip(self, session):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid comparison session, deep copying and retrieving should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Deep copy the session
        copied_session = deepcopy(session)
        
        # Verify basic fields are preserved
        assert copied_session.id == session.id
        assert copied_session.template == session.template
        assert copied_session.created_at == session.created_at
        assert copied_session.updated_at == session.updated_at
        
        # Verify options are preserved
        assert len(copied_session.options) == len(session.options)
        for original_option, copied_option in zip(session.options, copied_session.options):
            assert copied_option.name == original_option.name
            assert copied_option.description == original_option.description
            assert copied_option.attributes == original_option.attributes
            assert copied_option.metadata == original_option.metadata
            assert copied_option.id == original_option.id
        
        # Verify constraints are preserved
        assert len(copied_session.constraints) == len(session.constraints)
        for original_constraint, copied_constraint in zip(session.constraints, copied_session.constraints):
            assert copied_constraint.name == original_constraint.name
            assert copied_constraint.description == original_constraint.description
            assert copied_constraint.weight == original_constraint.weight
            assert copied_constraint.priority == original_constraint.priority
            assert copied_constraint.type == original_constraint.type
            assert copied_constraint.id == original_constraint.id

    @given(option_strategy())
    def test_option_pickle_round_trip(self, option):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid option, pickle serialization and deserialization should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Serialize and deserialize using pickle
        serialized = pickle.dumps(option)
        deserialized_option = pickle.loads(serialized)
        
        # Verify all fields are preserved
        assert deserialized_option.name == option.name
        assert deserialized_option.description == option.description
        assert deserialized_option.attributes == option.attributes
        assert deserialized_option.metadata == option.metadata
        assert deserialized_option.id == option.id

    @given(constraint_strategy())
    def test_constraint_pickle_round_trip(self, constraint):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid constraint, pickle serialization and deserialization should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Serialize and deserialize using pickle
        serialized = pickle.dumps(constraint)
        deserialized_constraint = pickle.loads(serialized)
        
        # Verify all fields are preserved
        assert deserialized_constraint.name == constraint.name
        assert deserialized_constraint.description == constraint.description
        assert deserialized_constraint.weight == constraint.weight
        assert deserialized_constraint.priority == constraint.priority
        assert deserialized_constraint.type == constraint.type
        assert deserialized_constraint.id == constraint.id

    @given(comparison_session_strategy())
    def test_comparison_session_pickle_round_trip(self, session):
        """
        Feature: option-comparison-tool, Property 1: Data Persistence Round Trip
        For any valid comparison session, pickle serialization and deserialization should preserve all data.
        Validates: Requirements 1.1, 1.2
        """
        # Serialize and deserialize using pickle
        serialized = pickle.dumps(session)
        deserialized_session = pickle.loads(serialized)
        
        # Verify basic fields are preserved
        assert deserialized_session.id == session.id
        assert deserialized_session.template == session.template
        assert deserialized_session.created_at == session.created_at
        assert deserialized_session.updated_at == session.updated_at
        
        # Verify options count matches
        assert len(deserialized_session.options) == len(session.options)
        
        # Verify constraints count matches
        assert len(deserialized_session.constraints) == len(session.constraints)