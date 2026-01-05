"""
Core data models for the Option Comparison Tool.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum
import uuid


class ConstraintType(Enum):
    """Types of constraints supported by the system."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class Priority(Enum):
    """Priority levels for constraints."""
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice-to-have"


@dataclass
class NumericScale:
    """Scale definition for numeric constraints."""
    min: float
    max: float
    unit: Optional[str] = None
    direction: Literal["higher-better", "lower-better"] = "higher-better"
    normalization_method: Literal["min-max", "z-score"] = "min-max"


@dataclass
class CategoricalScale:
    """Scale definition for categorical constraints."""
    values: List[str]
    scores: List[float]
    ordered: bool = True


@dataclass
class Option:
    """Represents a single option in a comparison."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate option data after initialization."""
        if not self.name.strip():
            raise ValueError("Option name cannot be empty")


@dataclass
class Constraint:
    """Represents a constraint or criterion for comparison."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    weight: float = 1.0
    priority: Priority = Priority.PREFERRED
    type: ConstraintType = ConstraintType.NUMERIC
    scale: Optional[NumericScale | CategoricalScale] = None

    def __post_init__(self):
        """Validate constraint data after initialization."""
        if not self.name.strip():
            raise ValueError("Constraint name cannot be empty")
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError("Constraint weight must be between 0.0 and 1.0")


@dataclass
class ComparisonSession:
    """Represents a complete comparison session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    options: List[Option] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    analysis_results: Optional[Dict[str, Any]] = None
    template: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate session data after initialization."""
        if len(self.options) < 2:
            raise ValueError("Comparison session must have at least 2 options")
        if len(self.options) > 10:
            raise ValueError("Comparison session cannot have more than 10 options")

    def update_timestamp(self):
        """Update the last modified timestamp."""
        self.updated_at = datetime.now()

    def add_option(self, option: Option):
        """Add an option to the comparison session."""
        if len(self.options) >= 10:
            raise ValueError("Cannot add more than 10 options to a comparison")
        self.options.append(option)
        self.update_timestamp()

    def add_constraint(self, constraint: Constraint):
        """Add a constraint to the comparison session."""
        self.constraints.append(constraint)
        self.update_timestamp()