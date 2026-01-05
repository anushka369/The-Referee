"""
Constraint categorization system for importance levels and conflict detection.

This module provides functionality to categorize constraints by importance
and detect conflicts between constraints in a comparison session.
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .models import Constraint, Priority, ConstraintType

logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of conflicts that can occur between constraints."""
    LOGICAL_CONTRADICTION = "logical_contradiction"
    PRIORITY_MISMATCH = "priority_mismatch"
    WEIGHT_IMBALANCE = "weight_imbalance"
    SEMANTIC_OVERLAP = "semantic_overlap"


@dataclass
class ConstraintConflict:
    """Represents a conflict between constraints."""
    constraint_a: str  # Constraint name
    constraint_b: str  # Constraint name
    conflict_type: ConflictType
    description: str
    severity: str  # "high", "medium", "low"
    suggestion: Optional[str] = None


@dataclass
class ConstraintCategory:
    """Represents a category of constraints by importance level."""
    priority: Priority
    constraints: List[Constraint]
    total_weight: float
    description: str


class ConstraintCategorizer:
    """
    Categorizes constraints by importance levels and detects conflicts.
    
    This class implements constraint categorization according to requirements 2.1 and 2.3,
    organizing constraints by their priority levels and identifying potential conflicts.
    """
    
    def __init__(self):
        """Initialize the constraint categorizer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def categorize_constraints(self, constraints: List[Constraint]) -> Dict[Priority, ConstraintCategory]:
        """
        Categorize constraints by their importance levels.
        
        Args:
            constraints: List of constraints to categorize
            
        Returns:
            Dictionary mapping Priority levels to ConstraintCategory objects
        """
        self.logger.info(f"Categorizing {len(constraints)} constraints by importance level")
        
        categories = {}
        
        # Initialize categories for all priority levels
        for priority in Priority:
            categories[priority] = ConstraintCategory(
                priority=priority,
                constraints=[],
                total_weight=0.0,
                description=self._get_priority_description(priority)
            )
        
        # Categorize constraints
        for constraint in constraints:
            category = categories[constraint.priority]
            category.constraints.append(constraint)
            category.total_weight += constraint.weight
        
        # Log categorization results
        for priority, category in categories.items():
            if category.constraints:
                self.logger.info(
                    f"{priority.value}: {len(category.constraints)} constraints, "
                    f"total weight: {category.total_weight:.2f}"
                )
        
        return categories
    
    def detect_conflicts(self, constraints: List[Constraint]) -> List[ConstraintConflict]:
        """
        Detect conflicts between constraints.
        
        Args:
            constraints: List of constraints to analyze for conflicts
            
        Returns:
            List of detected conflicts
        """
        self.logger.info(f"Analyzing {len(constraints)} constraints for conflicts")
        
        conflicts = []
        
        # Check for various types of conflicts
        conflicts.extend(self._detect_logical_contradictions(constraints))
        conflicts.extend(self._detect_priority_mismatches(constraints))
        conflicts.extend(self._detect_weight_imbalances(constraints))
        conflicts.extend(self._detect_semantic_overlaps(constraints))
        
        self.logger.info(f"Detected {len(conflicts)} conflicts")
        return conflicts
    
    def get_importance_summary(self, constraints: List[Constraint]) -> Dict[str, any]:
        """
        Get a summary of constraint importance distribution.
        
        Args:
            constraints: List of constraints to analyze
            
        Returns:
            Dictionary with importance distribution summary
        """
        categories = self.categorize_constraints(constraints)
        
        summary = {
            "total_constraints": len(constraints),
            "total_weight": sum(c.weight for c in constraints),
            "categories": {}
        }
        
        for priority, category in categories.items():
            if category.constraints:
                summary["categories"][priority.value] = {
                    "count": len(category.constraints),
                    "total_weight": category.total_weight,
                    "percentage": (category.total_weight / summary["total_weight"] * 100) if summary["total_weight"] > 0 else 0,
                    "constraints": [c.name for c in category.constraints]
                }
        
        return summary
    
    def _get_priority_description(self, priority: Priority) -> str:
        """Get description for a priority level."""
        descriptions = {
            Priority.REQUIRED: "Must-have constraints that are essential for the decision",
            Priority.PREFERRED: "Important constraints that significantly influence the decision",
            Priority.NICE_TO_HAVE: "Optional constraints that provide additional value"
        }
        return descriptions.get(priority, "Unknown priority level")
    
    def _detect_logical_contradictions(self, constraints: List[Constraint]) -> List[ConstraintConflict]:
        """
        Detect logical contradictions between constraints.
        
        This looks for constraints that are mutually exclusive or contradictory.
        """
        conflicts = []
        
        # Look for constraints with similar names but opposite meanings
        constraint_pairs = []
        for i, constraint_a in enumerate(constraints):
            for constraint_b in constraints[i+1:]:
                constraint_pairs.append((constraint_a, constraint_b))
        
        for constraint_a, constraint_b in constraint_pairs:
            # Check for contradictory naming patterns
            if self._are_contradictory_names(constraint_a.name, constraint_b.name):
                conflicts.append(ConstraintConflict(
                    constraint_a=constraint_a.name,
                    constraint_b=constraint_b.name,
                    conflict_type=ConflictType.LOGICAL_CONTRADICTION,
                    description=f"Constraints '{constraint_a.name}' and '{constraint_b.name}' appear to be contradictory",
                    severity="high",
                    suggestion="Consider combining these into a single constraint or clarifying their relationship"
                ))
        
        return conflicts
    
    def _detect_priority_mismatches(self, constraints: List[Constraint]) -> List[ConstraintConflict]:
        """
        Detect mismatches between constraint priorities and weights.
        
        This identifies cases where high-priority constraints have low weights or vice versa.
        """
        conflicts = []
        
        # Define expected weight ranges for each priority
        priority_weight_expectations = {
            Priority.REQUIRED: (0.7, 1.0),      # Required should have high weights
            Priority.PREFERRED: (0.3, 0.8),     # Preferred should have medium weights
            Priority.NICE_TO_HAVE: (0.0, 0.4)   # Nice-to-have should have low weights
        }
        
        for constraint in constraints:
            expected_min, expected_max = priority_weight_expectations[constraint.priority]
            
            if constraint.weight < expected_min:
                conflicts.append(ConstraintConflict(
                    constraint_a=constraint.name,
                    constraint_b="",
                    conflict_type=ConflictType.PRIORITY_MISMATCH,
                    description=f"Constraint '{constraint.name}' has {constraint.priority.value} priority but low weight ({constraint.weight:.2f})",
                    severity="medium",
                    suggestion=f"Consider increasing weight to at least {expected_min:.1f} or lowering priority"
                ))
            elif constraint.weight > expected_max:
                conflicts.append(ConstraintConflict(
                    constraint_a=constraint.name,
                    constraint_b="",
                    conflict_type=ConflictType.PRIORITY_MISMATCH,
                    description=f"Constraint '{constraint.name}' has {constraint.priority.value} priority but high weight ({constraint.weight:.2f})",
                    severity="medium",
                    suggestion=f"Consider lowering weight to at most {expected_max:.1f} or raising priority"
                ))
        
        return conflicts
    
    def _detect_weight_imbalances(self, constraints: List[Constraint]) -> List[ConstraintConflict]:
        """
        Detect significant weight imbalances between constraints.
        
        This identifies cases where one constraint dominates others excessively.
        """
        conflicts = []
        
        if len(constraints) < 2:
            return conflicts
        
        total_weight = sum(c.weight for c in constraints)
        if total_weight == 0:
            return conflicts
        
        # Check for constraints that dominate (>70% of total weight)
        for constraint in constraints:
            weight_percentage = constraint.weight / total_weight
            
            if weight_percentage > 0.7:
                other_constraints = [c.name for c in constraints if c.name != constraint.name]
                conflicts.append(ConstraintConflict(
                    constraint_a=constraint.name,
                    constraint_b=", ".join(other_constraints[:3]) + ("..." if len(other_constraints) > 3 else ""),
                    conflict_type=ConflictType.WEIGHT_IMBALANCE,
                    description=f"Constraint '{constraint.name}' dominates with {weight_percentage:.1%} of total weight",
                    severity="medium",
                    suggestion="Consider redistributing weights more evenly or removing less important constraints"
                ))
        
        return conflicts
    
    def _detect_semantic_overlaps(self, constraints: List[Constraint]) -> List[ConstraintConflict]:
        """
        Detect semantic overlaps between constraints.
        
        This identifies constraints that might be measuring similar things.
        """
        conflicts = []
        
        # Look for constraints with similar names or descriptions
        for i, constraint_a in enumerate(constraints):
            for constraint_b in constraints[i+1:]:
                if self._are_semantically_similar(constraint_a, constraint_b):
                    conflicts.append(ConstraintConflict(
                        constraint_a=constraint_a.name,
                        constraint_b=constraint_b.name,
                        conflict_type=ConflictType.SEMANTIC_OVERLAP,
                        description=f"Constraints '{constraint_a.name}' and '{constraint_b.name}' may be measuring similar aspects",
                        severity="low",
                        suggestion="Consider combining these constraints or ensuring they measure distinct aspects"
                    ))
        
        return conflicts
    
    def _are_contradictory_names(self, name_a: str, name_b: str) -> bool:
        """
        Check if two constraint names suggest they are contradictory.
        
        Args:
            name_a: First constraint name
            name_b: Second constraint name
            
        Returns:
            True if names suggest contradiction
        """
        name_a_lower = name_a.lower()
        name_b_lower = name_b.lower()
        
        # Define contradictory pairs
        contradictory_pairs = [
            ("cost", "price"),  # These might not be contradictory, but could be redundant
            ("speed", "latency"),  # Speed vs latency could be contradictory
            ("simple", "complex"),
            ("easy", "difficult"),
            ("fast", "slow"),
            ("cheap", "expensive"),
            ("high", "low"),
            ("maximum", "minimum"),
            ("best", "worst")
        ]
        
        # Check for direct contradictions
        for word1, word2 in contradictory_pairs:
            if (word1 in name_a_lower and word2 in name_b_lower) or \
               (word2 in name_a_lower and word1 in name_b_lower):
                return True
        
        return False
    
    def _are_semantically_similar(self, constraint_a: Constraint, constraint_b: Constraint) -> bool:
        """
        Check if two constraints are semantically similar.
        
        Args:
            constraint_a: First constraint
            constraint_b: Second constraint
            
        Returns:
            True if constraints appear to be measuring similar things
        """
        # Simple similarity check based on name and description
        name_a = constraint_a.name.lower()
        name_b = constraint_b.name.lower()
        desc_a = constraint_a.description.lower()
        desc_b = constraint_b.description.lower()
        
        # Check for similar words in names
        similar_word_pairs = [
            ("cost", "price", "expense", "budget"),
            ("performance", "speed", "efficiency", "throughput"),
            ("quality", "reliability", "stability"),
            ("usability", "ease", "user-friendly"),
            ("scalability", "capacity", "volume"),
            ("security", "safety", "protection"),
            ("maintenance", "support", "upkeep")
        ]
        
        for word_group in similar_word_pairs:
            name_a_matches = any(word in name_a for word in word_group)
            name_b_matches = any(word in name_b for word in word_group)
            desc_a_matches = any(word in desc_a for word in word_group)
            desc_b_matches = any(word in desc_b for word in word_group)
            
            if (name_a_matches and name_b_matches) or \
               (name_a_matches and desc_b_matches) or \
               (desc_a_matches and name_b_matches):
                return True
        
        return False
    
    def validate_constraint_system(self, constraints: List[Constraint]) -> Dict[str, any]:
        """
        Perform comprehensive validation of the constraint system.
        
        Args:
            constraints: List of constraints to validate
            
        Returns:
            Dictionary with validation results and recommendations
        """
        self.logger.info(f"Validating constraint system with {len(constraints)} constraints")
        
        categories = self.categorize_constraints(constraints)
        conflicts = self.detect_conflicts(constraints)
        importance_summary = self.get_importance_summary(constraints)
        
        # Generate recommendations
        recommendations = []
        
        # Check if we have required constraints
        if not categories[Priority.REQUIRED].constraints:
            recommendations.append("Consider adding at least one REQUIRED constraint to ensure essential needs are met")
        
        # Check weight distribution
        total_weight = sum(c.weight for c in constraints)
        if total_weight == 0:
            recommendations.append("All constraints have zero weight - consider assigning meaningful weights")
        elif total_weight < 0.5:
            recommendations.append("Total constraint weight is low - consider increasing weights for more decisive analysis")
        
        # Check for conflicts
        high_severity_conflicts = [c for c in conflicts if c.severity == "high"]
        if high_severity_conflicts:
            recommendations.append(f"Address {len(high_severity_conflicts)} high-severity conflicts before proceeding")
        
        return {
            "is_valid": len(high_severity_conflicts) == 0,
            "categories": {p.value: len(cat.constraints) for p, cat in categories.items()},
            "conflicts": {
                "total": len(conflicts),
                "by_severity": {
                    "high": len([c for c in conflicts if c.severity == "high"]),
                    "medium": len([c for c in conflicts if c.severity == "medium"]),
                    "low": len([c for c in conflicts if c.severity == "low"])
                }
            },
            "importance_summary": importance_summary,
            "recommendations": recommendations,
            "detailed_conflicts": conflicts
        }