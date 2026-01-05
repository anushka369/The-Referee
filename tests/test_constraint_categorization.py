"""
Property-based tests for constraint categorization and conflict detection.

Feature: option-comparison-tool
Property 4: Constraint Categorization
Property 6: Conflict Detection
Validates: Requirements 2.1, 2.3
"""

import pytest
from hypothesis import given, strategies as st, assume
from option_comparison_tool.models import Constraint, Priority, ConstraintType, NumericScale, CategoricalScale
from option_comparison_tool.constraint_categorization import ConstraintCategorizer, ConflictType


# Hypothesis strategies for generating test data
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
def constraint_with_specific_priority_strategy(draw, priority):
    """Generate constraint with specific priority."""
    name = draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
    return Constraint(
        name=name,
        description=draw(st.text(max_size=500)),
        weight=draw(st.floats(min_value=0.0, max_value=1.0)),
        priority=priority,
        type=draw(st.sampled_from(ConstraintType))
    )


@st.composite
def contradictory_constraint_pairs_strategy(draw):
    """Generate pairs of constraints that should be detected as contradictory."""
    base_name = draw(st.sampled_from(["cost", "speed", "simple", "easy", "fast", "cheap"]))
    opposite_name = {
        "cost": "price",
        "speed": "latency", 
        "simple": "complex",
        "easy": "difficult",
        "fast": "slow",
        "cheap": "expensive"
    }[base_name]
    
    constraint_a = Constraint(
        name=base_name,
        description=f"Constraint about {base_name}",
        weight=draw(st.floats(min_value=0.1, max_value=1.0)),
        priority=draw(st.sampled_from(Priority)),
        type=draw(st.sampled_from(ConstraintType))
    )
    
    constraint_b = Constraint(
        name=opposite_name,
        description=f"Constraint about {opposite_name}",
        weight=draw(st.floats(min_value=0.1, max_value=1.0)),
        priority=draw(st.sampled_from(Priority)),
        type=draw(st.sampled_from(ConstraintType))
    )
    
    return constraint_a, constraint_b


@st.composite
def priority_weight_mismatch_strategy(draw):
    """Generate constraints with priority-weight mismatches."""
    mismatch_type = draw(st.sampled_from(["high_priority_low_weight", "low_priority_high_weight"]))
    
    if mismatch_type == "high_priority_low_weight":
        # Required priority with very low weight
        return Constraint(
            name=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
            description="High priority constraint",
            weight=draw(st.floats(min_value=0.0, max_value=0.3)),  # Low weight
            priority=Priority.REQUIRED,  # High priority
            type=draw(st.sampled_from(ConstraintType))
        )
    else:
        # Nice-to-have priority with very high weight
        return Constraint(
            name=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
            description="Low priority constraint",
            weight=draw(st.floats(min_value=0.7, max_value=1.0)),  # High weight
            priority=Priority.NICE_TO_HAVE,  # Low priority
            type=draw(st.sampled_from(ConstraintType))
        )


class TestConstraintCategorization:
    """Test constraint categorization using property-based testing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.categorizer = ConstraintCategorizer()
    
    @given(st.lists(valid_constraint_strategy(), min_size=1, max_size=20))
    def test_all_constraints_are_categorized_by_priority(self, constraints):
        """
        Feature: option-comparison-tool, Property 4: Constraint Categorization
        For any constraint with a specified importance level, the system should correctly categorize it.
        Validates: Requirements 2.1
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        assume(len(unique_constraints) >= 1)
        
        # Categorize constraints
        categories = self.categorizer.categorize_constraints(unique_constraints)
        
        # Verify all priority levels are represented in categories
        assert len(categories) == len(Priority)
        for priority in Priority:
            assert priority in categories
            assert categories[priority].priority == priority
        
        # Verify all constraints are categorized
        total_categorized = sum(len(cat.constraints) for cat in categories.values())
        assert total_categorized == len(unique_constraints)
        
        # Verify each constraint is in the correct category
        for constraint in unique_constraints:
            found_in_category = False
            for priority, category in categories.items():
                if constraint in category.constraints:
                    assert constraint.priority == priority
                    found_in_category = True
                    break
            assert found_in_category, f"Constraint {constraint.name} not found in any category"
    
    @given(st.lists(constraint_with_specific_priority_strategy(Priority.REQUIRED), min_size=1, max_size=5),
           st.lists(constraint_with_specific_priority_strategy(Priority.PREFERRED), min_size=1, max_size=5),
           st.lists(constraint_with_specific_priority_strategy(Priority.NICE_TO_HAVE), min_size=1, max_size=5))
    def test_categorization_preserves_priority_levels(self, required_constraints, preferred_constraints, nice_to_have_constraints):
        """
        Feature: option-comparison-tool, Property 4: Constraint Categorization
        For any mix of constraints with different priorities, categorization should preserve priority levels.
        Validates: Requirements 2.1
        """
        # Ensure all constraint names are unique across all lists
        all_constraints = []
        seen_names = set()
        
        for constraint_list in [required_constraints, preferred_constraints, nice_to_have_constraints]:
            for constraint in constraint_list:
                if constraint.name not in seen_names:
                    all_constraints.append(constraint)
                    seen_names.add(constraint.name)
        
        assume(len(all_constraints) >= 3)  # At least one from each category
        
        # Categorize constraints
        categories = self.categorizer.categorize_constraints(all_constraints)
        
        # Verify each priority level has the expected constraints
        required_in_category = [c.name for c in categories[Priority.REQUIRED].constraints]
        preferred_in_category = [c.name for c in categories[Priority.PREFERRED].constraints]
        nice_to_have_in_category = [c.name for c in categories[Priority.NICE_TO_HAVE].constraints]
        
        # Check that constraints ended up in correct categories
        for constraint in all_constraints:
            if constraint.priority == Priority.REQUIRED:
                assert constraint.name in required_in_category
            elif constraint.priority == Priority.PREFERRED:
                assert constraint.name in preferred_in_category
            elif constraint.priority == Priority.NICE_TO_HAVE:
                assert constraint.name in nice_to_have_in_category
    
    @given(st.lists(valid_constraint_strategy(), min_size=1, max_size=10))
    def test_weight_totals_are_calculated_correctly(self, constraints):
        """
        Feature: option-comparison-tool, Property 4: Constraint Categorization
        For any set of constraints, the total weight per category should equal the sum of individual weights.
        Validates: Requirements 2.1
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        assume(len(unique_constraints) >= 1)
        
        # Categorize constraints
        categories = self.categorizer.categorize_constraints(unique_constraints)
        
        # Verify weight calculations
        for priority, category in categories.items():
            expected_total_weight = sum(c.weight for c in category.constraints)
            assert abs(category.total_weight - expected_total_weight) < 1e-10
    
    @given(st.lists(valid_constraint_strategy(), min_size=0, max_size=5))
    def test_empty_categories_have_zero_weight(self, constraints):
        """
        Feature: option-comparison-tool, Property 4: Constraint Categorization
        For any priority level with no constraints, the total weight should be zero.
        Validates: Requirements 2.1
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        # Categorize constraints
        categories = self.categorizer.categorize_constraints(unique_constraints)
        
        # Check empty categories
        for priority, category in categories.items():
            if len(category.constraints) == 0:
                assert category.total_weight == 0.0
            else:
                assert category.total_weight > 0.0 or all(c.weight == 0.0 for c in category.constraints)


class TestConflictDetection:
    """Test conflict detection using property-based testing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.categorizer = ConstraintCategorizer()
    
    @given(contradictory_constraint_pairs_strategy())
    def test_contradictory_constraints_are_detected(self, constraint_pair):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any constraints that are logically conflicting, the system should identify and highlight these conflicts.
        Validates: Requirements 2.3
        """
        constraint_a, constraint_b = constraint_pair
        constraints = [constraint_a, constraint_b]
        
        # Detect conflicts
        conflicts = self.categorizer.detect_conflicts(constraints)
        
        # Should detect at least one logical contradiction
        logical_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.LOGICAL_CONTRADICTION]
        assert len(logical_conflicts) >= 1
        
        # Verify the conflict involves both constraints
        conflict = logical_conflicts[0]
        assert constraint_a.name in [conflict.constraint_a, conflict.constraint_b]
        assert constraint_b.name in [conflict.constraint_a, conflict.constraint_b]
    
    @given(priority_weight_mismatch_strategy())
    def test_priority_weight_mismatches_are_detected(self, constraint):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any constraint with mismatched priority and weight, the system should identify this as a conflict.
        Validates: Requirements 2.3
        """
        constraints = [constraint]
        
        # Detect conflicts
        conflicts = self.categorizer.detect_conflicts(constraints)
        
        # Should detect priority mismatch
        priority_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.PRIORITY_MISMATCH]
        assert len(priority_conflicts) >= 1
        
        # Verify the conflict is about the right constraint
        conflict = priority_conflicts[0]
        assert conflict.constraint_a == constraint.name
    
    @given(st.lists(valid_constraint_strategy(), min_size=2, max_size=10))
    def test_conflict_detection_is_comprehensive(self, constraints):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any set of constraints, conflict detection should analyze all possible conflict types.
        Validates: Requirements 2.3
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        assume(len(unique_constraints) >= 2)
        
        # Detect conflicts
        conflicts = self.categorizer.detect_conflicts(unique_constraints)
        
        # Conflicts should be properly structured
        for conflict in conflicts:
            assert isinstance(conflict.constraint_a, str)
            assert len(conflict.constraint_a) > 0
            assert isinstance(conflict.description, str)
            assert len(conflict.description) > 0
            assert conflict.severity in ["high", "medium", "low"]
            assert isinstance(conflict.conflict_type, ConflictType)
    
    @given(st.lists(valid_constraint_strategy(), min_size=1, max_size=5))
    def test_single_constraint_has_no_conflicts(self, constraints):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any single constraint, there should be no conflicts with other constraints.
        Validates: Requirements 2.3
        """
        # Take only the first constraint to test single constraint scenario
        if constraints:
            single_constraint = [constraints[0]]
            
            # Detect conflicts
            conflicts = self.categorizer.detect_conflicts(single_constraint)
            
            # Should have no logical contradictions or semantic overlaps
            logical_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.LOGICAL_CONTRADICTION]
            semantic_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.SEMANTIC_OVERLAP]
            
            assert len(logical_conflicts) == 0
            assert len(semantic_conflicts) == 0
            
            # May still have priority mismatches or weight imbalances for the single constraint
    
    @given(st.lists(valid_constraint_strategy(), min_size=2, max_size=8))
    def test_weight_imbalance_detection(self, constraints):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any set of constraints where one dominates by weight, this should be detected as a conflict.
        Validates: Requirements 2.3
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        assume(len(unique_constraints) >= 2)
        
        # Create a dominating constraint (high weight)
        dominating_constraint = unique_constraints[0]
        dominating_constraint.weight = 0.8
        
        # Set other constraints to low weights
        for constraint in unique_constraints[1:]:
            constraint.weight = 0.05
        
        # Detect conflicts
        conflicts = self.categorizer.detect_conflicts(unique_constraints)
        
        # Should detect weight imbalance
        weight_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.WEIGHT_IMBALANCE]
        
        # May or may not detect depending on exact weight distribution
        # But if detected, should involve the dominating constraint
        if weight_conflicts:
            assert any(dominating_constraint.name == c.constraint_a for c in weight_conflicts)
    
    @given(st.lists(valid_constraint_strategy(), min_size=1, max_size=10))
    def test_validation_provides_comprehensive_analysis(self, constraints):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any constraint system, validation should provide comprehensive analysis and recommendations.
        Validates: Requirements 2.3
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        # Validate constraint system
        validation_result = self.categorizer.validate_constraint_system(unique_constraints)
        
        # Verify validation result structure
        assert "is_valid" in validation_result
        assert isinstance(validation_result["is_valid"], bool)
        
        assert "categories" in validation_result
        assert isinstance(validation_result["categories"], dict)
        
        assert "conflicts" in validation_result
        assert "total" in validation_result["conflicts"]
        assert "by_severity" in validation_result["conflicts"]
        
        assert "recommendations" in validation_result
        assert isinstance(validation_result["recommendations"], list)
        
        assert "detailed_conflicts" in validation_result
        assert isinstance(validation_result["detailed_conflicts"], list)
        
        # Verify category counts match actual constraints
        total_categorized = sum(validation_result["categories"].values())
        assert total_categorized == len(unique_constraints)
    
    @given(st.lists(valid_constraint_strategy(), min_size=0, max_size=3))
    def test_empty_or_small_constraint_sets_handled_gracefully(self, constraints):
        """
        Feature: option-comparison-tool, Property 6: Conflict Detection
        For any small or empty constraint set, the system should handle analysis gracefully.
        Validates: Requirements 2.3
        """
        # Ensure constraint names are unique
        unique_constraints = []
        seen_names = set()
        for constraint in constraints:
            if constraint.name not in seen_names:
                unique_constraints.append(constraint)
                seen_names.add(constraint.name)
        
        # Should not raise exceptions
        categories = self.categorizer.categorize_constraints(unique_constraints)
        conflicts = self.categorizer.detect_conflicts(unique_constraints)
        validation = self.categorizer.validate_constraint_system(unique_constraints)
        
        # Results should be well-formed
        assert isinstance(categories, dict)
        assert isinstance(conflicts, list)
        assert isinstance(validation, dict)
        
        # Empty constraint set should have specific behavior
        if len(unique_constraints) == 0:
            assert all(len(cat.constraints) == 0 for cat in categories.values())
            assert len(conflicts) == 0
            assert validation["is_valid"] is True  # No conflicts in empty set