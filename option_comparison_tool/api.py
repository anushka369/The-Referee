"""
FastAPI web service for the Option Comparison Tool.

This module provides REST endpoints for all core functionality including
comparison creation, analysis, templates, and export capabilities.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from . import __version__
from .comparison_manager import ComparisonManager
from .template_engine import TemplateEngine
from .weighted_scoring import WeightedScoringAnalyzer
from .tradeoff_analyzer import TradeoffAnalyzer
from .results_formatter import ResultsFormatter, OutputFormat
from .executive_summary import ExecutiveSummaryGenerator
from .export_engine import ExportEngine
from .integration import get_system_integrator, shutdown_system
from .models import (
    Option, Constraint, ComparisonSession, ConstraintType, Priority,
    NumericScale, CategoricalScale
)
from .api_models import (
    ComparisonSessionCreateAPI, ComparisonSessionAPI, ComparisonSessionUpdateAPI,
    OptionCreateAPI, OptionAPI, ConstraintCreateAPI, ConstraintAPI,
    WeightAdjustmentAPI, WhatIfScenarioAPI, WhatIfScenarioResponseAPI,
    AnalysisRequestAPI, ExportRequestAPI, TemplateAPI,
    ErrorResponseAPI, SuccessResponseAPI, SessionListAPI,
    ImpactAnalysisAPI, SensitivityAnalysisAPI, HealthCheckAPI,
    ConstraintTypeAPI, PriorityAPI, NumericScaleAPI, CategoricalScaleAPI
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Global service instances
system_integrator: Optional[Any] = None
comparison_manager: Optional[ComparisonManager] = None
template_engine: Optional[TemplateEngine] = None
export_engine: Optional[ExportEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global system_integrator, comparison_manager, template_engine, export_engine
    
    # Startup
    logger.info("Starting Option Comparison Tool API")
    system_integrator = get_system_integrator()
    comparison_manager = system_integrator._comparison_manager
    template_engine = system_integrator._template_engine
    export_engine = system_integrator._export_engine
    
    yield
    
    # Shutdown
    logger.info("Shutting down Option Comparison Tool API")
    shutdown_system()


# Create FastAPI application
app = FastAPI(
    title="Option Comparison Tool API",
    description="A comprehensive API for comparing multiple options with structured analysis",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for comprehensive error handling."""
    logger.error(f"Unhandled exception in {request.method} {request.url}: {exc}")
    
    # Don't override HTTP exceptions
    if isinstance(exc, HTTPException):
        raise exc
    
    # Handle specific exception types
    if isinstance(exc, ValueError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)}
        )
    
    # Generic server error
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def get_comparison_manager() -> ComparisonManager:
    """Dependency to get comparison manager instance."""
    if comparison_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return comparison_manager


def get_template_engine() -> TemplateEngine:
    """Dependency to get template engine instance."""
    if template_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return template_engine


def get_export_engine() -> ExportEngine:
    """Dependency to get export engine instance."""
    if export_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    return export_engine


def convert_to_internal_option(option_api: OptionCreateAPI) -> Option:
    """Convert API option model to internal model."""
    return Option(
        name=option_api.name,
        description=option_api.description,
        attributes=option_api.attributes,
        metadata=option_api.metadata
    )


def convert_to_api_option(option: Option) -> OptionAPI:
    """Convert internal option model to API model."""
    return OptionAPI(
        id=option.id,
        name=option.name,
        description=option.description,
        attributes=option.attributes,
        metadata=option.metadata
    )


def convert_to_internal_constraint(constraint_api: ConstraintCreateAPI) -> Constraint:
    """Convert API constraint model to internal model."""
    # Convert scale if provided
    scale = None
    if constraint_api.scale:
        if constraint_api.type == ConstraintTypeAPI.NUMERIC:
            if isinstance(constraint_api.scale, NumericScaleAPI):
                scale = NumericScale(
                    min=constraint_api.scale.min,
                    max=constraint_api.scale.max,
                    unit=constraint_api.scale.unit,
                    direction=constraint_api.scale.direction,
                    normalization_method=constraint_api.scale.normalization_method
                )
        elif constraint_api.type == ConstraintTypeAPI.CATEGORICAL:
            if isinstance(constraint_api.scale, CategoricalScaleAPI):
                scale = CategoricalScale(
                    values=constraint_api.scale.values,
                    scores=constraint_api.scale.scores,
                    ordered=constraint_api.scale.ordered
                )
    
    return Constraint(
        name=constraint_api.name,
        description=constraint_api.description,
        weight=constraint_api.weight,
        priority=Priority(constraint_api.priority.value),
        type=ConstraintType(constraint_api.type.value),
        scale=scale
    )


def convert_to_api_constraint(constraint: Constraint) -> ConstraintAPI:
    """Convert internal constraint model to API model."""
    # Convert scale if present
    scale = None
    if constraint.scale:
        if isinstance(constraint.scale, NumericScale):
            scale = NumericScaleAPI(
                min=constraint.scale.min,
                max=constraint.scale.max,
                unit=constraint.scale.unit,
                direction=constraint.scale.direction,
                normalization_method=constraint.scale.normalization_method
            )
        elif isinstance(constraint.scale, CategoricalScale):
            scale = CategoricalScaleAPI(
                values=constraint.scale.values,
                scores=constraint.scale.scores,
                ordered=constraint.scale.ordered
            )
    
    return ConstraintAPI(
        id=constraint.id,
        name=constraint.name,
        description=constraint.description,
        weight=constraint.weight,
        priority=PriorityAPI(constraint.priority.value),
        type=ConstraintTypeAPI(constraint.type.value),
        scale=scale
    )


def convert_to_api_session(session: ComparisonSession) -> ComparisonSessionAPI:
    """Convert internal session model to API model."""
    return ComparisonSessionAPI(
        id=session.id,
        options=[convert_to_api_option(opt) for opt in session.options],
        constraints=[convert_to_api_constraint(cons) for cons in session.constraints],
        analysis_results=session.analysis_results,
        template=session.template,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@app.get("/health", response_model=HealthCheckAPI)
async def health_check():
    """Health check endpoint with integrated system status."""
    global system_integrator
    
    if system_integrator is None:
        return HealthCheckAPI(
            status="unhealthy",
            version=__version__,
            timestamp=datetime.now()
        )
    
    try:
        health = system_integrator.get_system_health()
        return HealthCheckAPI(
            status=health.status,
            version=__version__,
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckAPI(
            status="unhealthy",
            version=__version__,
            timestamp=datetime.now()
        )


@app.post("/sessions", response_model=ComparisonSessionAPI, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: ComparisonSessionCreateAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Create a new comparison session."""
    try:
        # Convert API models to internal models
        options = [convert_to_internal_option(opt) for opt in session_data.options]
        constraints = [convert_to_internal_constraint(cons) for cons in session_data.constraints]
        
        # Create the session
        session = manager.create_comparison(options, constraints, session_data.template)
        
        return convert_to_api_session(session)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/sessions", response_model=SessionListAPI)
async def list_sessions(
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """List all comparison sessions."""
    try:
        session_ids = manager.list_sessions()
        return SessionListAPI(
            sessions=session_ids,
            total=len(session_ids)
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/sessions/{session_id}", response_model=ComparisonSessionAPI)
async def get_session(
    session_id: str,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Get a specific comparison session."""
    try:
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return convert_to_api_session(session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.put("/sessions/{session_id}", response_model=ComparisonSessionAPI)
async def update_session(
    session_id: str,
    update_data: ComparisonSessionUpdateAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Update constraints for a comparison session."""
    try:
        # Convert API constraints to internal models
        constraints = [convert_to_internal_constraint(cons) for cons in update_data.constraints]
        
        # Update the session
        session = manager.update_constraints(session_id, constraints)
        
        return convert_to_api_session(session)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.delete("/sessions/{session_id}", response_model=SuccessResponseAPI)
async def delete_session(
    session_id: str,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Delete a comparison session."""
    try:
        success = manager.delete_session(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SuccessResponseAPI(
            message=f"Session {session_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/options", response_model=ComparisonSessionAPI)
async def add_option_to_session(
    session_id: str,
    option_data: OptionCreateAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Add an option to an existing comparison session."""
    try:
        # Convert API option to internal model
        option = convert_to_internal_option(option_data)
        
        # Add the option
        session = manager.add_option_to_session(session_id, option)
        
        return convert_to_api_session(session)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding option to session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/analyze")
async def analyze_session(
    session_id: str,
    analysis_request: AnalysisRequestAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Run analysis on a comparison session."""
    try:
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        # Run weighted scoring analysis
        analyzer = WeightedScoringAnalyzer()
        scoring_results = analyzer.analyze(session.options, session.constraints)
        
        # Run trade-off analysis
        tradeoff_analyzer = TradeoffAnalyzer()
        tradeoffs = tradeoff_analyzer.analyze_tradeoffs(session.options, session.constraints)
        
        # Generate executive summary
        summary_generator = ExecutiveSummaryGenerator()
        summary = summary_generator.generate_summary(scoring_results, tradeoffs, session.constraints)
        
        # Format results
        formatter = ResultsFormatter()
        formatted_results = formatter.format_results(
            scoring_results, tradeoffs, session.constraints, OutputFormat.TABLE
        )
        
        # Store results in session
        session.analysis_results = {
            'method': analysis_request.method.value,
            'scoring_results': scoring_results,
            'tradeoffs': tradeoffs,
            'summary': summary,
            'formatted_results': formatted_results,
            'analysis_timestamp': datetime.now().isoformat()
        }
        session.update_timestamp()
        
        return {
            'session_id': session_id,
            'method': analysis_request.method.value,
            'results': session.analysis_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/adjust-weights", response_model=ImpactAnalysisAPI)
async def adjust_weights(
    session_id: str,
    weight_data: WeightAdjustmentAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Adjust constraint weights and get impact analysis."""
    try:
        updated_session, impact_analysis = manager.adjust_constraint_weights(
            session_id, weight_data.weight_adjustments
        )
        
        # Convert ranking_changes from dict to list format expected by API
        ranking_changes_list = []
        for option_name, (old_rank, new_rank) in impact_analysis.ranking_changes.items():
            ranking_changes_list.append({
                'option_name': option_name,
                'old_rank': old_rank,
                'new_rank': new_rank
            })
        
        return ImpactAnalysisAPI(
            ranking_changes=ranking_changes_list,
            most_affected_options=impact_analysis.most_affected_options,
            impact_summary=impact_analysis.summary
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adjusting weights for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/what-if", response_model=WhatIfScenarioResponseAPI)
async def create_what_if_scenario(
    session_id: str,
    scenario_data: WhatIfScenarioAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Create a what-if scenario analysis."""
    try:
        scenario = manager.create_what_if_scenario(
            session_id, scenario_data.scenario_name, scenario_data.weight_adjustments
        )
        
        # Extract weight adjustments from impact analysis
        weight_adjustments = {
            adj.constraint_name: adj.new_weight 
            for adj in scenario.impact_analysis.weight_adjustments
        }
        
        # Convert scoring results to rankings format
        original_rankings = [
            {
                "option_name": score.option_name,
                "rank": score.rank,
                "score": score.total_score
            }
            for score in scenario.original_result.option_scores
        ]
        
        modified_rankings = [
            {
                "option_name": score.option_name,
                "rank": score.rank,
                "score": score.total_score
            }
            for score in scenario.modified_result.option_scores
        ]
        
        # Convert ranking changes
        ranking_changes = [
            {
                "option_name": option_name,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "rank_change": new_rank - old_rank
            }
            for option_name, (old_rank, new_rank) in scenario.impact_analysis.ranking_changes.items()
        ]
        
        return WhatIfScenarioResponseAPI(
            scenario_name=scenario.scenario_name,
            weight_adjustments=weight_adjustments,
            original_rankings=original_rankings,
            modified_rankings=modified_rankings,
            ranking_changes=ranking_changes
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating what-if scenario for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/sensitivity")
async def analyze_sensitivity(
    session_id: str,
    sensitivity_data: SensitivityAnalysisAPI,
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Analyze constraint sensitivity."""
    try:
        sensitivity_results = manager.analyze_constraint_sensitivity(
            session_id,
            sensitivity_data.constraint_name,
            sensitivity_data.weight_range,
            sensitivity_data.steps
        )
        
        return {
            'session_id': session_id,
            'constraint_name': sensitivity_data.constraint_name,
            'weight_range': sensitivity_data.weight_range,
            'steps': sensitivity_data.steps,
            'results': sensitivity_results
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing sensitivity for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/sessions/{session_id}/critical-constraints")
async def get_critical_constraints(
    session_id: str,
    sensitivity_threshold: float = Query(0.1, ge=0.0, le=1.0),
    manager: ComparisonManager = Depends(get_comparison_manager)
):
    """Identify critical constraints that most impact rankings."""
    try:
        critical_constraints = manager.identify_critical_constraints(
            session_id, sensitivity_threshold
        )
        
        return {
            'session_id': session_id,
            'sensitivity_threshold': sensitivity_threshold,
            'critical_constraints': [
                {'constraint_name': name, 'impact_score': score}
                for name, score in critical_constraints
            ]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error identifying critical constraints for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    export_request: ExportRequestAPI,
    manager: ComparisonManager = Depends(get_comparison_manager),
    exporter: ExportEngine = Depends(get_export_engine)
):
    """Export session results in specified formats."""
    try:
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        if not session.analysis_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session has no analysis results to export. Run analysis first."
            )
        
        exported_files = []
        
        for format_type in export_request.formats:
            if format_type.value in ["json", "markdown"]:
                filename = exporter.export_comparison(
                    session, format_type.value, include_analysis=True, include_reasoning=True
                )
                exported_files.append({"format": format_type.value, "filename": str(filename)})
            elif format_type.value == "pdf":
                # PDF export would be implemented here
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="PDF export not yet implemented"
                )
        
        return {
            'session_id': session_id,
            'exported_files': exported_files,
            'export_timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/templates", response_model=List[TemplateAPI])
async def list_templates(
    template_engine: TemplateEngine = Depends(get_template_engine)
):
    """List all available templates."""
    try:
        templates = template_engine.list_templates()
        
        api_templates = []
        for template in templates:
            # Convert template constraint templates to API constraints
            api_constraints = []
            for constraint_template in template.constraints:
                # Convert constraint template to actual constraint first
                constraint = constraint_template.to_constraint()
                api_constraints.append(convert_to_api_constraint(constraint))
            
            # Convert template options to API options
            api_options = []
            for option_template in template.suggested_options:
                # Convert option template to actual option first
                option = option_template.to_option()
                api_options.append(convert_to_api_option(option))
            
            api_templates.append(TemplateAPI(
                id=template.id,
                name=template.name,
                description=template.description,
                domain=template.domain.value,
                constraints=api_constraints,
                suggested_options=api_options
            ))
        
        return api_templates
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/templates/{template_id}", response_model=TemplateAPI)
async def get_template(
    template_id: str,
    template_engine: TemplateEngine = Depends(get_template_engine)
):
    """Get a specific template."""
    try:
        template = template_engine.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        # Convert template constraint templates to API constraints
        api_constraints = []
        for constraint_template in template.constraints:
            # Convert constraint template to actual constraint first
            constraint = constraint_template.to_constraint()
            api_constraints.append(convert_to_api_constraint(constraint))
        
        # Convert template options to API options
        api_options = []
        for option_template in template.suggested_options:
            # Convert option template to actual option first
            option = option_template.to_option()
            api_options.append(convert_to_api_option(option))
        
        return TemplateAPI(
            id=template.id,
            name=template.name,
            description=template.description,
            domain=template.domain.value,
            constraints=api_constraints,
            suggested_options=api_options
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/templates/{template_id}/apply", response_model=ComparisonSessionAPI)
async def apply_template(
    template_id: str,
    manager: ComparisonManager = Depends(get_comparison_manager),
    template_engine: TemplateEngine = Depends(get_template_engine)
):
    """Apply a template to create a new comparison session."""
    try:
        constraints, options = template_engine.apply_template(template_id)
        
        # Create the session
        session = manager.create_comparison(options, constraints, template_id)
        
        return convert_to_api_session(session)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponseAPI(
            error="ValidationError",
            message=str(exc)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponseAPI(
            error="InternalServerError",
            message="An unexpected error occurred"
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)