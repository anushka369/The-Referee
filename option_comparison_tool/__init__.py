"""
Option Comparison Tool - A system for comparing multiple alternatives with structured analysis.
"""

__version__ = "0.1.0"

from .models import Option, Constraint, ComparisonSession, ConstraintType, Priority
from .comparison_manager import ComparisonManager
from .config import Config
from .integration import SystemIntegrator, get_system_integrator, shutdown_system

__all__ = [
    'Option', 'Constraint', 'ComparisonSession', 'ConstraintType', 'Priority',
    'ComparisonManager', 'Config', 'SystemIntegrator', 'get_system_integrator', 
    'shutdown_system'
]