"""
Pydantic models for the FastAPI web service.

These models provide request/response validation and OpenAPI documentation
for all API endpoints.
"""

from typing import Dict, Any, List, Optional, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .models import ConstraintType, Priority


class ConstraintTypeAPI(str, Enum):
    """API enum for constraint types."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class PriorityAPI(str, Enum):
    """API enum for priority levels."""
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice-to-have"


class NumericScaleAPI(BaseModel):
    """API model for numeric scale definition."""
    min: float = Field(..., description="Minimum value for the scale")
    max: float = Field(..., description="Maximum value for the scale")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    direction: Literal["higher-better", "lower-better"] = Field(
        "higher-better", description="Whether higher or lower values are better"
    )
    normalization_method: Literal["min-max", "z-score"] = Field(
        "min-max", description="Method for normalizing values"
    )


class CategoricalScaleAPI(BaseModel):
    """API model for categorical scale definition."""
    values: List[str] = Field(..., description="List of categorical values")
    scores: List[float] = Field(..., description="Corresponding numeric scores")
    ordered: bool = Field(True, description="Whether the categories are ordered")

    @field_validator('scores')
    @classmethod
    def validate_scores_length(cls, v, info):
        if 'values' in info.data and len(v) != len(info.data['values']):
            raise ValueError('scores must have the same length as values')
        return v


class OptionCreateAPI(BaseModel):
    """API model for creating an option."""
    name: str = Field(..., description="Name of the option", min_length=1)
    description: str = Field("", description="Description of the option")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Option attributes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class OptionAPI(BaseModel):
    """API model for option response."""
    id: str = Field(..., description="Unique identifier for the option")
    name: str = Field(..., description="Name of the option")
    description: str = Field(..., description="Description of the option")
    attributes: Dict[str, Any] = Field(..., description="Option attributes")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")


class ConstraintCreateAPI(BaseModel):
    """API model for creating a constraint."""
    name: str = Field(..., description="Name of the constraint", min_length=1)
    description: str = Field("", description="Description of the constraint")
    weight: float = Field(1.0, description="Weight of the constraint", ge=0.0, le=1.0)
    priority: PriorityAPI = Field(PriorityAPI.PREFERRED, description="Priority level")
    type: ConstraintTypeAPI = Field(ConstraintTypeAPI.NUMERIC, description="Type of constraint")
    scale: Optional[Union[NumericScaleAPI, CategoricalScaleAPI]] = Field(
        None, description="Scale definition for the constraint"
    )


class ConstraintAPI(BaseModel):
    """API model for constraint response."""
    id: str = Field(..., description="Unique identifier for the constraint")
    name: str = Field(..., description="Name of the constraint")
    description: str = Field(..., description="Description of the constraint")
    weight: float = Field(..., description="Weight of the constraint")
    priority: PriorityAPI = Field(..., description="Priority level")
    type: ConstraintTypeAPI = Field(..., description="Type of constraint")
    scale: Optional[Union[NumericScaleAPI, CategoricalScaleAPI]] = Field(
        None, description="Scale definition for the constraint"
    )


class ComparisonSessionCreateAPI(BaseModel):
    """API model for creating a comparison session."""
    options: List[OptionCreateAPI] = Field(
        ..., description="List of options to compare", min_length=2, max_length=10
    )
    constraints: List[ConstraintCreateAPI] = Field(
        default_factory=list, description="List of constraints for evaluation"
    )
    template: Optional[str] = Field(None, description="Template identifier")


class ComparisonSessionAPI(BaseModel):
    """API model for comparison session response."""
    id: str = Field(..., description="Unique identifier for the session")
    options: List[OptionAPI] = Field(..., description="List of options in the comparison")
    constraints: List[ConstraintAPI] = Field(..., description="List of constraints")
    analysis_results: Optional[Dict[str, Any]] = Field(
        None, description="Analysis results if available"
    )
    template: Optional[str] = Field(None, description="Template identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ComparisonSessionUpdateAPI(BaseModel):
    """API model for updating a comparison session."""
    constraints: List[ConstraintCreateAPI] = Field(
        ..., description="Updated list of constraints"
    )


class WeightAdjustmentAPI(BaseModel):
    """API model for constraint weight adjustments."""
    weight_adjustments: Dict[str, float] = Field(
        ..., description="Dictionary mapping constraint names to new weights"
    )

    @field_validator('weight_adjustments')
    @classmethod
    def validate_weights(cls, v):
        for constraint_name, weight in v.items():
            if not (0.0 <= weight <= 1.0):
                raise ValueError(f'Weight for {constraint_name} must be between 0.0 and 1.0')
        return v


class WhatIfScenarioAPI(BaseModel):
    """API model for creating what-if scenarios."""
    scenario_name: str = Field(..., description="Name for the scenario", min_length=1)
    weight_adjustments: Dict[str, float] = Field(
        ..., description="Dictionary mapping constraint names to new weights"
    )

    @field_validator('weight_adjustments')
    @classmethod
    def validate_weights(cls, v):
        for constraint_name, weight in v.items():
            if not (0.0 <= weight <= 1.0):
                raise ValueError(f'Weight for {constraint_name} must be between 0.0 and 1.0')
        return v


class AnalysisMethodAPI(str, Enum):
    """API enum for analysis methods."""
    WEIGHTED_SCORING = "weighted_scoring"


class AnalysisRequestAPI(BaseModel):
    """API model for analysis requests."""
    method: AnalysisMethodAPI = Field(
        AnalysisMethodAPI.WEIGHTED_SCORING, description="Analysis method to use"
    )


class ExportFormatAPI(str, Enum):
    """API enum for export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"


class ExportRequestAPI(BaseModel):
    """API model for export requests."""
    formats: List[ExportFormatAPI] = Field(
        ..., description="List of export formats", min_length=1
    )


class TemplateAPI(BaseModel):
    """API model for template response."""
    id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    domain: str = Field(..., description="Template domain")
    constraints: List[ConstraintAPI] = Field(..., description="Template constraints")
    suggested_options: List[OptionAPI] = Field(..., description="Suggested options")


class ErrorResponseAPI(BaseModel):
    """API model for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class SuccessResponseAPI(BaseModel):
    """API model for success responses."""
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


class SessionListAPI(BaseModel):
    """API model for session list response."""
    sessions: List[str] = Field(..., description="List of session IDs")
    total: int = Field(..., description="Total number of sessions")


class ImpactAnalysisAPI(BaseModel):
    """API model for impact analysis response."""
    ranking_changes: List[Dict[str, Any]] = Field(
        ..., description="List of ranking changes"
    )
    most_affected_options: List[str] = Field(
        ..., description="Options most affected by changes"
    )
    impact_summary: str = Field(..., description="Summary of the impact")


class WhatIfScenarioResponseAPI(BaseModel):
    """API model for what-if scenario response."""
    scenario_name: str = Field(..., description="Name of the scenario")
    weight_adjustments: Dict[str, float] = Field(
        ..., description="Weight adjustments applied"
    )
    original_rankings: List[Dict[str, Any]] = Field(
        ..., description="Original option rankings"
    )
    modified_rankings: List[Dict[str, Any]] = Field(
        ..., description="Modified option rankings"
    )
    ranking_changes: List[Dict[str, Any]] = Field(
        ..., description="Summary of ranking changes"
    )


class SensitivityAnalysisAPI(BaseModel):
    """API model for sensitivity analysis request."""
    constraint_name: str = Field(..., description="Name of constraint to analyze")
    weight_range: tuple[float, float] = Field(
        (0.0, 1.0), description="Weight range to test"
    )
    steps: int = Field(10, description="Number of weight values to test", ge=2, le=50)


class HealthCheckAPI(BaseModel):
    """API model for health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Current timestamp")