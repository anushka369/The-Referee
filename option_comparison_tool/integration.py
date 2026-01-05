"""
Integration module for the Option Comparison Tool.

This module provides comprehensive integration of all components with
proper error handling, performance optimization, and system validation.
"""

import logging
import asyncio
import time
import uuid
import re
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from .comparison_manager import ComparisonManager
from .template_engine import TemplateEngine
from .weighted_scoring import WeightedScoringAnalyzer
from .tradeoff_analyzer import TradeoffAnalyzer
from .results_formatter import ResultsFormatter, OutputFormat
from .executive_summary import ExecutiveSummaryGenerator
from .export_engine import ExportEngine
from .dynamic_analysis import DynamicAnalyzer
from .constraint_categorization import ConstraintCategorizer
from .models import ComparisonSession, Option, Constraint
from .config import Config, logger


@dataclass
class SystemHealth:
    """System health status information."""
    status: str
    components: Dict[str, bool]
    performance_metrics: Dict[str, float]
    error_count: int
    last_check: datetime


@dataclass
class IntegrationError:
    """Integration error information."""
    component: str
    error_type: str
    message: str
    timestamp: datetime
    session_id: Optional[str] = None


class ComponentIntegrationError(Exception):
    """Raised when component integration fails."""
    pass


class PerformanceError(Exception):
    """Raised when performance requirements are not met."""
    pass


class SystemIntegrator:
    """
    Main system integrator that wires all components together with
    comprehensive error handling and performance optimization.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the system integrator.
        
        Args:
            data_dir: Directory for data storage
        """
        self.data_dir = data_dir or Config.DATA_DIR
        self.logger = logging.getLogger(__name__)
        
        # Component instances
        self._comparison_manager: Optional[ComparisonManager] = None
        self._template_engine: Optional[TemplateEngine] = None
        self._weighted_scoring: Optional[WeightedScoringAnalyzer] = None
        self._tradeoff_analyzer: Optional[TradeoffAnalyzer] = None
        self._results_formatter: Optional[ResultsFormatter] = None
        self._executive_summary: Optional[ExecutiveSummaryGenerator] = None
        self._export_engine: Optional[ExportEngine] = None
        self._dynamic_analyzer: Optional[DynamicAnalyzer] = None
        self._constraint_categorizer: Optional[ConstraintCategorizer] = None
        
        # System state
        self._initialized = False
        self._errors: List[IntegrationError] = []
        self._performance_metrics: Dict[str, float] = {}
        
        self.logger.info("SystemIntegrator initialized")
    
    def initialize(self) -> None:
        """
        Initialize all system components with proper error handling.
        
        Raises:
            ComponentIntegrationError: If component initialization fails
        """
        if self._initialized:
            self.logger.warning("System already initialized")
            return
        
        try:
            self.logger.info("Initializing system components...")
            
            # Initialize core components in dependency order
            self._initialize_comparison_manager()
            self._initialize_template_engine()
            self._initialize_analysis_components()
            self._initialize_formatting_components()
            self._initialize_export_engine()
            
            # Validate component integration
            self._validate_component_integration()
            
            self._initialized = True
            
            # Run system health check
            health = self.get_system_health()
            if health.status not in ['healthy', 'degraded']:
                self._initialized = False
                raise ComponentIntegrationError(f"System health check failed: {health.status}")
            
            self.logger.info("System initialization completed successfully")
            
        except Exception as e:
            self._record_error("system", "initialization", str(e))
            self.logger.error(f"System initialization failed: {e}")
            raise ComponentIntegrationError(f"Failed to initialize system: {e}") from e
    
    def _initialize_comparison_manager(self) -> None:
        """Initialize the comparison manager."""
        try:
            self._comparison_manager = ComparisonManager(self.data_dir)
            self.logger.debug("ComparisonManager initialized")
        except Exception as e:
            raise ComponentIntegrationError(f"Failed to initialize ComparisonManager: {e}") from e
    
    def _initialize_template_engine(self) -> None:
        """Initialize the template engine."""
        try:
            self._template_engine = TemplateEngine()
            self.logger.debug("TemplateEngine initialized")
        except Exception as e:
            raise ComponentIntegrationError(f"Failed to initialize TemplateEngine: {e}") from e
    
    def _initialize_analysis_components(self) -> None:
        """Initialize analysis components."""
        try:
            self._weighted_scoring = WeightedScoringAnalyzer()
            self._tradeoff_analyzer = TradeoffAnalyzer()
            self._dynamic_analyzer = DynamicAnalyzer()
            self._constraint_categorizer = ConstraintCategorizer()
            self.logger.debug("Analysis components initialized")
        except Exception as e:
            raise ComponentIntegrationError(f"Failed to initialize analysis components: {e}") from e
    
    def _initialize_formatting_components(self) -> None:
        """Initialize formatting and presentation components."""
        try:
            self._results_formatter = ResultsFormatter()
            self._executive_summary = ExecutiveSummaryGenerator()
            self.logger.debug("Formatting components initialized")
        except Exception as e:
            raise ComponentIntegrationError(f"Failed to initialize formatting components: {e}") from e
    
    def _initialize_export_engine(self) -> None:
        """Initialize the export engine."""
        try:
            self._export_engine = ExportEngine()
            self.logger.debug("ExportEngine initialized")
        except Exception as e:
            raise ComponentIntegrationError(f"Failed to initialize ExportEngine: {e}") from e
    
    def _validate_component_integration(self) -> None:
        """Validate that all components are properly integrated."""
        components = {
            "comparison_manager": self._comparison_manager,
            "template_engine": self._template_engine,
            "weighted_scoring": self._weighted_scoring,
            "tradeoff_analyzer": self._tradeoff_analyzer,
            "results_formatter": self._results_formatter,
            "executive_summary": self._executive_summary,
            "export_engine": self._export_engine,
            "dynamic_analyzer": self._dynamic_analyzer,
            "constraint_categorizer": self._constraint_categorizer,
        }
        
        for name, component in components.items():
            if component is None:
                raise ComponentIntegrationError(f"Component {name} is not initialized")
        
        self.logger.debug("Component integration validation passed")
    
    @contextmanager
    def error_handling(self, operation: str, session_id: Optional[str] = None):
        """
        Context manager for comprehensive error handling.
        
        Args:
            operation: Name of the operation being performed
            session_id: Optional session ID for context
        """
        start_time = time.time()
        try:
            yield
        except Exception as e:
            self._record_error("operation", operation, str(e), session_id)
            self.logger.error(f"Error in {operation}: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self._performance_metrics[operation] = duration
            
            # Check for performance issues
            if duration > 30.0:  # 30 second threshold
                self.logger.warning(f"Operation {operation} took {duration:.2f}s (performance concern)")
    
    def _record_error(self, component: str, error_type: str, message: str, session_id: Optional[str] = None) -> None:
        """Record an integration error."""
        error = IntegrationError(
            component=component,
            error_type=error_type,
            message=message,
            timestamp=datetime.now(),
            session_id=session_id
        )
        self._errors.append(error)
        
        # Keep only last 100 errors to prevent memory issues
        if len(self._errors) > 100:
            self._errors = self._errors[-100:]
    
    def get_system_health(self) -> SystemHealth:
        """
        Get comprehensive system health status.
        
        Returns:
            SystemHealth object with current status
        """
        if not self._initialized:
            return SystemHealth(
                status="not_initialized",
                components={},
                performance_metrics={},
                error_count=len(self._errors),
                last_check=datetime.now()
            )
        
        # Check component health
        components = {
            "comparison_manager": self._comparison_manager is not None,
            "template_engine": self._template_engine is not None,
            "weighted_scoring": self._weighted_scoring is not None,
            "tradeoff_analyzer": self._tradeoff_analyzer is not None,
            "results_formatter": self._results_formatter is not None,
            "executive_summary": self._executive_summary is not None,
            "export_engine": self._export_engine is not None,
            "dynamic_analyzer": self._dynamic_analyzer is not None,
            "constraint_categorizer": self._constraint_categorizer is not None,
        }
        
        # Determine overall status
        all_healthy = all(components.values())
        recent_errors = len([e for e in self._errors if (datetime.now() - e.timestamp).seconds < 300])  # 5 minutes
        
        if not all_healthy:
            status = "unhealthy"
        elif recent_errors > 10:
            status = "degraded"
        else:
            status = "healthy"
        
        return SystemHealth(
            status=status,
            components=components,
            performance_metrics=self._performance_metrics.copy(),
            error_count=len(self._errors),
            last_check=datetime.now()
        )
    
    def create_integrated_comparison(
        self,
        options: List[Option],
        constraints: List[Constraint],
        template: Optional[str] = None
    ) -> ComparisonSession:
        """
        Create a comparison with full integration and error handling.
        
        Args:
            options: List of options to compare
            constraints: List of constraints for evaluation
            template: Optional template identifier
            
        Returns:
            ComparisonSession with full integration
            
        Raises:
            ComponentIntegrationError: If integration fails
        """
        if not self._initialized:
            raise ComponentIntegrationError("System not initialized")
        
        with self.error_handling("create_comparison"):
            # Validate inputs
            self._validate_comparison_inputs(options, constraints)
            
            # Create the comparison session
            session = self._comparison_manager.create_comparison(options, constraints, template)
            
            # Perform initial constraint categorization
            if constraints:
                categorization = self._constraint_categorizer.categorize_constraints(constraints)
                conflicts = self._constraint_categorizer.detect_conflicts(constraints)
                
                # Store categorization results in session metadata
                if not hasattr(session, 'metadata'):
                    session.metadata = {}
                session.metadata['constraint_categorization'] = categorization
                session.metadata['constraint_conflicts'] = conflicts
            
            self.logger.info(f"Created integrated comparison session {session.id}")
            return session
    
    def run_comprehensive_analysis(
        self,
        session_id: str,
        include_tradeoffs: bool = True,
        include_sensitivity: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive analysis with all components integrated.
        
        Args:
            session_id: Session to analyze
            include_tradeoffs: Whether to include tradeoff analysis
            include_sensitivity: Whether to include sensitivity analysis
            
        Returns:
            Comprehensive analysis results
            
        Raises:
            ComponentIntegrationError: If analysis fails
        """
        if not self._initialized:
            raise ComponentIntegrationError("System not initialized")
        
        with self.error_handling("comprehensive_analysis", session_id):
            # Get the session
            session = self._comparison_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            results = {}
            
            # Run weighted scoring analysis
            scoring_result = self._weighted_scoring.analyze(session.options, session.constraints)
            results['scoring'] = scoring_result
            
            # Run tradeoff analysis if requested
            if include_tradeoffs:
                tradeoff_result = self._tradeoff_analyzer.analyze_tradeoffs(
                    session.options, session.constraints
                )
                results['tradeoffs'] = tradeoff_result
            
            # Generate executive summary
            summary = self._executive_summary.generate_summary(
                scoring_result, 
                results.get('tradeoffs'),
                session.constraints
            )
            results['executive_summary'] = summary
            
            # Run sensitivity analysis if requested
            if include_sensitivity and session.constraints:
                sensitivity_results = {}
                for constraint in session.constraints[:3]:  # Limit to first 3 for performance
                    try:
                        sensitivity = self._comparison_manager.analyze_constraint_sensitivity(
                            session_id, constraint.name, steps=5
                        )
                        sensitivity_results[constraint.name] = sensitivity
                    except Exception as e:
                        self.logger.warning(f"Sensitivity analysis failed for {constraint.name}: {e}")
                
                if sensitivity_results:
                    results['sensitivity'] = sensitivity_results
            
            # Store results in session
            session.analysis_results = results
            
            self.logger.info(f"Completed comprehensive analysis for session {session_id}")
            return results
    
    def generate_formatted_results(
        self,
        session_id: str,
        formats: List[OutputFormat],
        analysis_results: Optional[Dict[str, Any]] = None
    ) -> Dict[OutputFormat, str]:
        """
        Generate formatted results in multiple formats.
        
        Args:
            session_id: Session to format results for
            formats: List of output formats to generate
            analysis_results: Optional pre-computed analysis results
            
        Returns:
            Dictionary mapping formats to formatted content
            
        Raises:
            ComponentIntegrationError: If formatting fails
        """
        if not self._initialized:
            raise ComponentIntegrationError("System not initialized")
        
        with self.error_handling("format_results", session_id):
            # Get the session to access constraints
            session = self._comparison_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get analysis results if not provided
            if analysis_results is None:
                if not hasattr(session, 'analysis_results'):
                    raise ValueError(f"No analysis results found for session {session_id}")
                analysis_results = session.analysis_results
            
            formatted_results = {}
            
            for format_type in formats:
                try:
                    formatted_content = self._results_formatter.format_results(
                        analysis_results['scoring'],
                        analysis_results.get('tradeoffs'),
                        session.constraints,
                        format_type
                    )
                    formatted_results[format_type] = formatted_content
                except Exception as e:
                    self.logger.error(f"Failed to format results in {format_type}: {e}")
                    # Continue with other formats
            
            self.logger.info(f"Generated {len(formatted_results)} formatted results for session {session_id}")
            return formatted_results
    
    def export_comprehensive_results(
        self,
        session_id: str,
        export_formats: List[str],
        include_analysis: bool = True
    ) -> Dict[str, str]:
        """
        Export comprehensive results with full integration.
        
        Args:
            session_id: Session to export
            export_formats: List of export formats
            include_analysis: Whether to include full analysis
            
        Returns:
            Dictionary mapping formats to file paths
            
        Raises:
            ComponentIntegrationError: If export fails
        """
        if not self._initialized:
            raise ComponentIntegrationError("System not initialized")
        
        with self.error_handling("export_results", session_id):
            # Get the session
            session = self._comparison_manager.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Run analysis if needed
            if include_analysis and not hasattr(session, 'analysis_results'):
                self.run_comprehensive_analysis(session_id)
                # Refresh session to get updated results
                session = self._comparison_manager.get_session(session_id)
            
            # Export in requested formats
            export_paths = {}
            for format_type in export_formats:
                try:
                    file_path = self._export_engine.export_comparison(
                        session,
                        format_type,
                        getattr(session, 'analysis_results', None)
                    )
                    export_paths[format_type] = file_path
                except Exception as e:
                    self.logger.error(f"Failed to export in {format_type}: {e}")
                    # Continue with other formats
            
            self.logger.info(f"Exported session {session_id} in {len(export_paths)} formats")
            return export_paths
    
    def _validate_session_id(self, session_id: str) -> None:
        """
        Validate session ID format.
        
        Args:
            session_id: Session ID to validate
            
        Raises:
            ValueError: If session ID format is invalid
        """
        if not session_id or not session_id.strip():
            raise ValueError("Session ID cannot be empty")
        
        # Check if it's a valid UUID format (our sessions use UUIDs)
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise ValueError(f"Invalid session ID format: {session_id}")
    
    def _validate_comparison_inputs(self, options: List[Option], constraints: List[Constraint]) -> None:
        """
        Validate comparison inputs with comprehensive checks.
        
        Args:
            options: Options to validate
            constraints: Constraints to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Basic validation
        if not options:
            raise ValueError("At least one option is required")
        
        if len(options) < Config.MIN_OPTIONS_PER_COMPARISON:
            raise ValueError(f"At least {Config.MIN_OPTIONS_PER_COMPARISON} options required")
        
        if len(options) > Config.MAX_OPTIONS_PER_COMPARISON:
            raise ValueError(f"Maximum {Config.MAX_OPTIONS_PER_COMPARISON} options allowed")
        
        # Validate option uniqueness
        option_names = [opt.name for opt in options]
        if len(option_names) != len(set(option_names)):
            raise ValueError("Option names must be unique")
        
        # Validate constraint uniqueness
        if constraints:
            constraint_names = [const.name for const in constraints]
            if len(constraint_names) != len(set(constraint_names)):
                raise ValueError("Constraint names must be unique")
        
        # Validate constraint weights
        for constraint in constraints:
            if not (0.0 <= constraint.weight <= 1.0):
                raise ValueError(f"Constraint '{constraint.name}' has invalid weight: {constraint.weight}")
    
    def optimize_performance(self) -> Dict[str, Any]:
        """
        Optimize system performance for maximum supported load.
        
        Returns:
            Performance optimization results
        """
        if not self._initialized:
            raise ComponentIntegrationError("System not initialized")
        
        optimization_results = {
            "cache_cleared": False,
            "memory_optimized": False,
            "performance_metrics": self._performance_metrics.copy()
        }
        
        try:
            # Clear old error records
            if len(self._errors) > 50:
                self._errors = self._errors[-50:]
                optimization_results["cache_cleared"] = True
            
            # Reset performance metrics if they're getting large
            if len(self._performance_metrics) > 100:
                self._performance_metrics.clear()
                optimization_results["memory_optimized"] = True
            
            self.logger.info("Performance optimization completed")
            
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")
            raise PerformanceError(f"Failed to optimize performance: {e}") from e
        
        return optimization_results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get comprehensive integration status.
        
        Returns:
            Integration status information
        """
        health = self.get_system_health()
        
        return {
            "initialized": self._initialized,
            "health": health,
            "recent_errors": [
                {
                    "component": e.component,
                    "type": e.error_type,
                    "message": e.message,
                    "timestamp": e.timestamp.isoformat(),
                    "session_id": e.session_id
                }
                for e in self._errors[-10:]  # Last 10 errors
            ],
            "performance_summary": {
                "total_operations": len(self._performance_metrics),
                "average_duration": sum(self._performance_metrics.values()) / len(self._performance_metrics) if self._performance_metrics else 0,
                "slowest_operation": max(self._performance_metrics.items(), key=lambda x: x[1]) if self._performance_metrics else None
            }
        }
    
    def shutdown(self) -> None:
        """Gracefully shutdown the system."""
        if not self._initialized:
            return
        
        try:
            self.logger.info("Shutting down system integrator...")
            
            # Clear component references
            self._comparison_manager = None
            self._template_engine = None
            self._weighted_scoring = None
            self._tradeoff_analyzer = None
            self._results_formatter = None
            self._executive_summary = None
            self._export_engine = None
            self._dynamic_analyzer = None
            self._constraint_categorizer = None
            
            self._initialized = False
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Global system integrator instance
_system_integrator: Optional[SystemIntegrator] = None


def get_system_integrator(data_dir: Optional[Path] = None) -> SystemIntegrator:
    """
    Get the global system integrator instance.
    
    Args:
        data_dir: Optional data directory
        
    Returns:
        SystemIntegrator instance
    """
    global _system_integrator
    
    if _system_integrator is None:
        _system_integrator = SystemIntegrator(data_dir)
        _system_integrator.initialize()
    
    return _system_integrator


def shutdown_system() -> None:
    """Shutdown the global system integrator."""
    global _system_integrator
    
    if _system_integrator is not None:
        _system_integrator.shutdown()
        _system_integrator = None