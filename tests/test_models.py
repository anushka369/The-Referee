"""
Unit tests for core data models.
"""

import pytest
from datetime import datetime
from option_comparison_tool.models import (
    Option, Constraint, ComparisonSession, 
    ConstraintType, Priority, NumericScale, CategoricalScale
)


class TestOption:
    """Test Option model functionality."""

    def test_option_creation_with_valid_data(self):
        """Test creating an option with valid data."""
        option = Option(
            name="Test API",
            description="A test API for comparison",
            attributes={"cost": 100, "performance": "high"},
            metadata={"source": "manual"}
        )
        
        assert option.name == "Test API"
        assert option.description == "A test API for comparison"
        assert option.attributes["cost"] == 100
        assert option.attributes["performance"] == "high"
        assert option.metadata["source"] == "manual"
        assert option.id is not None

    def test_option_creation_with_empty_name_raises_error(self):
        """Test that creating an option with empty name raises ValueError."""
        with pytest.raises(ValueError, match="Option name cannot be empty"):
            Option(name="")

    def test_option_creation_with_whitespace_name_raises_error(self):
        """Test that creating an option with whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Option name cannot be empty"):
            Option(name="   ")


class TestConstraint:
    """Test Constraint model functionality."""

    def test_constraint_creation_with_valid_data(self):
        """Test creating a constraint with valid data."""
        scale = NumericScale(min=0, max=100, unit="USD")
        constraint = Constraint(
            name="Cost",
            description="Total cost of ownership",
            weight=0.8,
            priority=Priority.REQUIRED,
            type=ConstraintType.NUMERIC,
            scale=scale
        )
        
        assert constraint.name == "Cost"
        assert constraint.description == "Total cost of ownership"
        assert constraint.weight == 0.8
        assert constraint.priority == Priority.REQUIRED
        assert constraint.type == ConstraintType.NUMERIC
        assert constraint.scale == scale
        assert constraint.id is not None

    def test_constraint_creation_with_empty_name_raises_error(self):
        """Test that creating a constraint with empty name raises ValueError."""
        with pytest.raises(ValueError, match="Constraint name cannot be empty"):
            Constraint(name="")

    def test_constraint_creation_with_invalid_weight_raises_error(self):
        """Test that creating a constraint with invalid weight raises ValueError."""
        with pytest.raises(ValueError, match="Constraint weight must be between 0.0 and 1.0"):
            Constraint(name="Test", weight=1.5)
        
        with pytest.raises(ValueError, match="Constraint weight must be between 0.0 and 1.0"):
            Constraint(name="Test", weight=-0.1)


class TestComparisonSession:
    """Test ComparisonSession model functionality."""

    def test_comparison_session_creation_with_valid_data(self):
        """Test creating a comparison session with valid data."""
        options = [
            Option(name="Option 1"),
            Option(name="Option 2"),
            Option(name="Option 3")
        ]
        constraints = [
            Constraint(name="Cost"),
            Constraint(name="Performance")
        ]
        
        session = ComparisonSession(
            options=options,
            constraints=constraints,
            template="api_comparison"
        )
        
        assert len(session.options) == 3
        assert len(session.constraints) == 2
        assert session.template == "api_comparison"
        assert session.id is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    def test_comparison_session_with_too_few_options_raises_error(self):
        """Test that creating a session with fewer than 2 options raises ValueError."""
        with pytest.raises(ValueError, match="Comparison session must have at least 2 options"):
            ComparisonSession(options=[Option(name="Only One")])

    def test_comparison_session_with_too_many_options_raises_error(self):
        """Test that creating a session with more than 10 options raises ValueError."""
        options = [Option(name=f"Option {i}") for i in range(11)]
        with pytest.raises(ValueError, match="Comparison session cannot have more than 10 options"):
            ComparisonSession(options=options)

    def test_add_option_to_session(self):
        """Test adding an option to an existing session."""
        session = ComparisonSession(options=[
            Option(name="Option 1"),
            Option(name="Option 2")
        ])
        
        initial_count = len(session.options)
        initial_updated_at = session.updated_at
        
        new_option = Option(name="Option 3")
        session.add_option(new_option)
        
        assert len(session.options) == initial_count + 1
        assert session.options[-1] == new_option
        assert session.updated_at > initial_updated_at

    def test_add_option_to_full_session_raises_error(self):
        """Test that adding an option to a session with 10 options raises ValueError."""
        options = [Option(name=f"Option {i}") for i in range(10)]
        session = ComparisonSession(options=options)
        
        with pytest.raises(ValueError, match="Cannot add more than 10 options to a comparison"):
            session.add_option(Option(name="Option 11"))

    def test_add_constraint_to_session(self):
        """Test adding a constraint to an existing session."""
        session = ComparisonSession(options=[
            Option(name="Option 1"),
            Option(name="Option 2")
        ])
        
        initial_count = len(session.constraints)
        initial_updated_at = session.updated_at
        
        new_constraint = Constraint(name="New Constraint")
        session.add_constraint(new_constraint)
        
        assert len(session.constraints) == initial_count + 1
        assert session.constraints[-1] == new_constraint
        assert session.updated_at > initial_updated_at


class TestScales:
    """Test scale model functionality."""

    def test_numeric_scale_creation(self):
        """Test creating a numeric scale."""
        scale = NumericScale(
            min=0,
            max=100,
            unit="USD",
            direction="lower-better",
            normalization_method="z-score"
        )
        
        assert scale.min == 0
        assert scale.max == 100
        assert scale.unit == "USD"
        assert scale.direction == "lower-better"
        assert scale.normalization_method == "z-score"

    def test_categorical_scale_creation(self):
        """Test creating a categorical scale."""
        scale = CategoricalScale(
            values=["low", "medium", "high"],
            scores=[1, 5, 10],
            ordered=True
        )
        
        assert scale.values == ["low", "medium", "high"]
        assert scale.scores == [1, 5, 10]
        assert scale.ordered is True