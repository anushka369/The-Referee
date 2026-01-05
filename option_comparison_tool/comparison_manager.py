"""
ComparisonManager - Core orchestration class for managing comparison sessions.

This module provides the main interface for creating, storing, and retrieving
comparison sessions with validation for options and constraints.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import json
import pickle

from .models import ComparisonSession, Option, Constraint
from .config import Config
from .dynamic_analysis import DynamicAnalyzer, ImpactAnalysis, WhatIfScenario

logger = logging.getLogger(__name__)


class ComparisonManager:
    """
    Orchestrates the entire comparison workflow from input to output.
    
    Handles session creation, storage, retrieval, and basic validation
    for options and constraints according to requirements 1.1, 1.2, 1.3.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the ComparisonManager.
        
        Args:
            data_dir: Directory for storing comparison sessions. 
                     Defaults to Config.DATA_DIR if not provided.
        """
        self.data_dir = data_dir or Config.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, ComparisonSession] = {}
        self.dynamic_analyzer = DynamicAnalyzer()
        logger.info(f"ComparisonManager initialized with data directory: {self.data_dir}")
    
    def create_comparison(
        self, 
        options: List[Option], 
        constraints: List[Constraint], 
        template: Optional[str] = None
    ) -> ComparisonSession:
        """
        Create a new comparison session with validation.
        
        Args:
            options: List of options to compare (must be 2-10 options)
            constraints: List of constraints for evaluation
            template: Optional template identifier
            
        Returns:
            ComparisonSession: The created and stored session
            
        Raises:
            ValueError: If validation fails for options or constraints
        """
        logger.info(f"Creating comparison with {len(options)} options and {len(constraints)} constraints")
        
        # Validate options
        self._validate_options(options)
        
        # Validate constraints
        self._validate_constraints(constraints)
        
        # Create the session (validation happens in ComparisonSession.__post_init__)
        session = ComparisonSession(
            options=options,
            constraints=constraints,
            template=template
        )
        
        # Store the session
        self._sessions[session.id] = session
        self._persist_session(session)
        
        logger.info(f"Created comparison session {session.id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ComparisonSession]:
        """
        Retrieve a comparison session by ID.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            ComparisonSession if found, None otherwise
        """
        # Validate session ID format
        if not session_id or not session_id.strip():
            return None
        
        # Check if it looks like a valid UUID (our sessions use UUIDs)
        try:
            import uuid
            uuid.UUID(session_id)
        except ValueError:
            # Invalid UUID format, return None
            return None
        
        # Try to get from memory first
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        # Try to load from disk
        session = self._load_session(session_id)
        if session:
            self._sessions[session_id] = session
            
        return session
    
    def update_constraints(self, session_id: str, constraints: List[Constraint]) -> ComparisonSession:
        """
        Update constraints for an existing comparison session.
        
        Args:
            session_id: Unique identifier for the session
            constraints: New list of constraints
            
        Returns:
            Updated ComparisonSession
            
        Raises:
            ValueError: If session not found or constraints are invalid
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Validate new constraints
        self._validate_constraints(constraints)
        
        # Update the session
        session.constraints = constraints
        session.update_timestamp()
        
        # Persist the changes
        self._persist_session(session)
        
        logger.info(f"Updated constraints for session {session_id}")
        return session
    
    def can_add_option(self, session_id: str) -> bool:
        """
        Check if an option can be added to a session without violating capacity constraints.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            True if an option can be added, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        return len(session.options) < Config.MAX_OPTIONS_PER_COMPARISON
    
    def add_option_to_session(self, session_id: str, option: Option) -> ComparisonSession:
        """
        Add an option to an existing comparison session with capacity validation.
        
        Args:
            session_id: Unique identifier for the session
            option: Option to add
            
        Returns:
            Updated ComparisonSession
            
        Raises:
            ValueError: If session not found or capacity constraints violated
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check capacity constraints before adding
        if len(session.options) >= Config.MAX_OPTIONS_PER_COMPARISON:
            raise ValueError(
                f"Cannot add option: session already has maximum of "
                f"{Config.MAX_OPTIONS_PER_COMPARISON} options"
            )
        
        # Validate the new option (but not capacity constraints for single option)
        self._validate_single_option(option)
        
        # Check for duplicate names with existing options
        existing_names = {opt.name for opt in session.options}
        if option.name in existing_names:
            raise ValueError(f"Option name '{option.name}' already exists in this comparison")
        
        # Add the option
        session.add_option(option)
        
        # Persist the changes
        self._persist_session(session)
        
        logger.info(f"Added option '{option.name}' to session {session_id}")
        return session
    
    def list_sessions(self) -> List[str]:
        """
        List all available session IDs.
        
        Returns:
            List of session IDs
        """
        # Get sessions from memory
        memory_sessions = set(self._sessions.keys())
        
        # Get sessions from disk
        disk_sessions = set()
        if self.data_dir.exists():
            for file_path in self.data_dir.glob("*.pkl"):
                session_id = file_path.stem
                disk_sessions.add(session_id)
        
        # Return combined list
        all_sessions = memory_sessions.union(disk_sessions)
        return list(all_sessions)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a comparison session.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            True if session was deleted, False if not found
        """
        # Remove from memory
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        # Remove from disk
        session_file = self.data_dir / f"{session_id}.pkl"
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session {session_id}")
            return True
        
        return False
    
    def _validate_options(self, options: List[Option]) -> None:
        """
        Validate a list of options according to requirements 1.1, 1.3, 1.4.
        
        Args:
            options: List of options to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not options:
            raise ValueError("At least one option is required")
        
        # Validate capacity constraints (requirement 1.4)
        self._validate_capacity_constraints(options)
        
        # Check for duplicate names
        names = [option.name for option in options]
        if len(names) != len(set(names)):
            raise ValueError("Option names must be unique")
        
        # Validate each option has essential information
        for i, option in enumerate(options):
            if not option.name or not option.name.strip():
                raise ValueError(f"Option {i+1} is missing a name")
            
            # Check for essential missing information based on requirements 1.3
            if not option.description and not option.attributes:
                raise ValueError(f"Option '{option.name}' is missing both description and attributes")
    
    def _validate_constraints(self, constraints: List[Constraint]) -> None:
        """
        Validate a list of constraints according to requirements 1.2, 1.3.
        
        Args:
            constraints: List of constraints to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not constraints:
            # Empty constraints list is allowed
            return
        
        # Check for duplicate names
        names = [constraint.name for constraint in constraints]
        if len(names) != len(set(names)):
            raise ValueError("Constraint names must be unique")
        
        # Validate each constraint has essential information
        for i, constraint in enumerate(constraints):
            if not constraint.name or not constraint.name.strip():
                raise ValueError(f"Constraint {i+1} is missing a name")
            
            # Validate weight is in valid range (already checked in Constraint.__post_init__)
            if not (0.0 <= constraint.weight <= 1.0):
                raise ValueError(f"Constraint '{constraint.name}' has invalid weight: {constraint.weight}")
    
    def _validate_capacity_constraints(self, options: List[Option]) -> None:
        """
        Validate capacity constraints according to requirement 1.4.
        
        Args:
            options: List of options to validate
            
        Raises:
            ValueError: If capacity constraints are violated
        """
        option_count = len(options)
        
        if option_count < Config.MIN_OPTIONS_PER_COMPARISON:
            raise ValueError(
                f"Comparison must have at least {Config.MIN_OPTIONS_PER_COMPARISON} options, "
                f"but got {option_count}"
            )
        
        if option_count > Config.MAX_OPTIONS_PER_COMPARISON:
            raise ValueError(
                f"Comparison cannot have more than {Config.MAX_OPTIONS_PER_COMPARISON} options, "
                f"but got {option_count}"
            )
    
    def _validate_single_option(self, option: Option) -> None:
        """
        Validate a single option without capacity constraints.
        
        Args:
            option: Option to validate
            
        Raises:
            ValueError: If validation fails
        """
        if not option.name or not option.name.strip():
            raise ValueError("Option is missing a name")
        
        # Check for essential missing information based on requirements 1.3
        if not option.description and not option.attributes:
            raise ValueError(f"Option '{option.name}' is missing both description and attributes")
    
    def _persist_session(self, session: ComparisonSession) -> None:
        """
        Persist a session to disk using pickle.
        
        Args:
            session: Session to persist
        """
        try:
            session_file = self.data_dir / f"{session.id}.pkl"
            with open(session_file, 'wb') as f:
                pickle.dump(session, f)
            logger.debug(f"Persisted session {session.id} to {session_file}")
        except Exception as e:
            logger.error(f"Failed to persist session {session.id}: {e}")
            raise
    
    def _load_session(self, session_id: str) -> Optional[ComparisonSession]:
        """
        Load a session from disk.
        
        Args:
            session_id: ID of session to load
            
        Returns:
            ComparisonSession if found and loaded successfully, None otherwise
        """
        try:
            session_file = self.data_dir / f"{session_id}.pkl"
            if not session_file.exists():
                return None
            
            with open(session_file, 'rb') as f:
                session = pickle.load(f)
            
            logger.debug(f"Loaded session {session_id} from {session_file}")
            return session
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def adjust_constraint_weights(
        self, 
        session_id: str, 
        weight_adjustments: Dict[str, float]
    ) -> Tuple[ComparisonSession, ImpactAnalysis]:
        """
        Adjust constraint weights and recalculate analysis with impact analysis.
        
        Args:
            session_id: Unique identifier for the session
            weight_adjustments: Dictionary mapping constraint names to new weights
            
        Returns:
            Tuple of (updated_session, impact_analysis)
            
        Raises:
            ValueError: If session not found or weight adjustments are invalid
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Use dynamic analyzer to adjust weights and analyze impact
        updated_session, impact_analysis = self.dynamic_analyzer.adjust_constraint_weights(
            session, weight_adjustments
        )
        
        # Persist the updated session
        self._persist_session(updated_session)
        
        logger.info(f"Adjusted constraint weights for session {session_id}")
        return updated_session, impact_analysis
    
    def create_what_if_scenario(
        self, 
        session_id: str, 
        scenario_name: str,
        weight_adjustments: Dict[str, float]
    ) -> WhatIfScenario:
        """
        Create a what-if scenario without modifying the original session.
        
        Args:
            session_id: Unique identifier for the session
            scenario_name: Name for this scenario
            weight_adjustments: Dictionary mapping constraint names to new weights
            
        Returns:
            WhatIfScenario with original and modified results
            
        Raises:
            ValueError: If session not found or weight adjustments are invalid
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Use dynamic analyzer to create what-if scenario
        scenario = self.dynamic_analyzer.create_what_if_scenario(
            session, scenario_name, weight_adjustments
        )
        
        logger.info(f"Created what-if scenario '{scenario_name}' for session {session_id}")
        return scenario
    
    def analyze_constraint_sensitivity(
        self, 
        session_id: str, 
        constraint_name: str,
        weight_range: Tuple[float, float] = (0.0, 1.0),
        steps: int = 10
    ) -> Dict[float, Any]:
        """
        Analyze how sensitive rankings are to changes in a specific constraint weight.
        
        Args:
            session_id: Unique identifier for the session
            constraint_name: Name of constraint to analyze
            weight_range: Tuple of (min_weight, max_weight) to test
            steps: Number of weight values to test
            
        Returns:
            Dictionary mapping weight values to scoring results
            
        Raises:
            ValueError: If session not found or parameters invalid
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Use dynamic analyzer for sensitivity analysis
        sensitivity_results = self.dynamic_analyzer.analyze_constraint_sensitivity(
            session, constraint_name, weight_range, steps
        )
        
        logger.info(f"Completed sensitivity analysis for constraint '{constraint_name}' in session {session_id}")
        return sensitivity_results
    
    def identify_critical_constraints(
        self, 
        session_id: str,
        sensitivity_threshold: float = 0.1
    ) -> List[Tuple[str, float]]:
        """
        Identify constraints that have the most impact on rankings.
        
        Args:
            session_id: Unique identifier for the session
            sensitivity_threshold: Minimum weight change to test (default 0.1)
            
        Returns:
            List of (constraint_name, impact_score) tuples, sorted by impact
            
        Raises:
            ValueError: If session not found
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Use dynamic analyzer to identify critical constraints
        critical_constraints = self.dynamic_analyzer.identify_critical_constraints(
            session, sensitivity_threshold
        )
        
        logger.info(f"Identified {len(critical_constraints)} critical constraints for session {session_id}")
        return critical_constraints