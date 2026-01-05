"""
Unit tests for the TemplateEngine class.
"""

import pytest
from option_comparison_tool.template_engine import (
    TemplateEngine, Template, ConstraintTemplate, OptionTemplate, TemplateDomain
)
from option_comparison_tool.models import ConstraintType, Priority, Constraint, Option


class TestTemplateEngine:
    """Test cases for TemplateEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemplateEngine()
    
    def test_builtin_templates_loaded(self):
        """Test that all built-in templates are loaded correctly."""
        templates = self.engine.list_templates()
        
        # Should have exactly 4 built-in templates
        assert len(templates) == 4
        
        # Check that all expected templates exist
        template_ids = {t.id for t in templates}
        expected_ids = {"api_comparison", "cloud_services", "tech_stack", "database_selection"}
        assert template_ids == expected_ids
    
    def test_api_template_structure(self):
        """Test API comparison template loads with correct structure."""
        template = self.engine.get_template("api_comparison")
        
        assert template is not None
        assert template.name == "API Comparison"
        assert template.domain == TemplateDomain.API
        assert len(template.constraints) == 6  # Performance, Reliability, Cost, Documentation, Rate Limiting, Authentication
        assert len(template.suggested_options) == 3  # REST, GraphQL, gRPC
        
        # Check specific constraints exist
        constraint_names = {c.name for c in template.constraints}
        expected_constraints = {"Performance", "Reliability", "Cost", "Documentation Quality", "Rate Limiting", "Authentication"}
        assert constraint_names == expected_constraints
        
        # Check constraint types and priorities
        performance_constraint = next(c for c in template.constraints if c.name == "Performance")
        assert performance_constraint.type == ConstraintType.NUMERIC
        assert performance_constraint.priority == Priority.REQUIRED
        assert performance_constraint.scale is not None
    
    def test_cloud_services_template_structure(self):
        """Test cloud services template loads with correct structure."""
        template = self.engine.get_template("cloud_services")
        
        assert template is not None
        assert template.name == "Cloud Services Comparison"
        assert template.domain == TemplateDomain.CLOUD_SERVICES
        assert len(template.constraints) == 5  # Cost, Performance, Scalability, Global Availability, Support Quality
        assert len(template.suggested_options) == 3  # AWS, Azure, Google Cloud
        
        # Check specific options exist
        option_names = {o.name for o in template.suggested_options}
        expected_options = {"AWS", "Azure", "Google Cloud"}
        assert option_names == expected_options
    
    def test_tech_stack_template_structure(self):
        """Test technology stack template loads with correct structure."""
        template = self.engine.get_template("tech_stack")
        
        assert template is not None
        assert template.name == "Technology Stack Comparison"
        assert template.domain == TemplateDomain.TECH_STACK
        assert len(template.constraints) == 5  # Learning Curve, Community Support, Performance, Ecosystem Maturity, Job Market
        assert len(template.suggested_options) == 3  # React+Node, Vue+Express, Django+Python
    
    def test_database_template_structure(self):
        """Test database selection template loads with correct structure."""
        template = self.engine.get_template("database_selection")
        
        assert template is not None
        assert template.name == "Database Selection"
        assert template.domain == TemplateDomain.DATABASE
        assert len(template.constraints) == 6  # Performance, Scalability, ACID, Query Flexibility, Operational Complexity, Cost
        assert len(template.suggested_options) == 3  # PostgreSQL, MongoDB, Redis
        
        # Check boolean constraint exists
        acid_constraint = next(c for c in template.constraints if c.name == "ACID Compliance")
        assert acid_constraint.type == ConstraintType.BOOLEAN
    
    def test_get_template_by_id(self):
        """Test retrieving templates by ID."""
        # Valid template ID
        template = self.engine.get_template("api_comparison")
        assert template is not None
        assert template.id == "api_comparison"
        
        # Invalid template ID
        template = self.engine.get_template("nonexistent")
        assert template is None
    
    def test_get_templates_by_domain(self):
        """Test filtering templates by domain."""
        api_templates = self.engine.get_templates_by_domain(TemplateDomain.API)
        assert len(api_templates) == 1
        assert api_templates[0].id == "api_comparison"
        
        cloud_templates = self.engine.get_templates_by_domain(TemplateDomain.CLOUD_SERVICES)
        assert len(cloud_templates) == 1
        assert cloud_templates[0].id == "cloud_services"
    
    def test_apply_template_success(self):
        """Test successfully applying a template."""
        constraints, options = self.engine.apply_template("api_comparison")
        
        # Should return actual Constraint and Option objects
        assert len(constraints) == 6
        assert len(options) == 3
        
        # Check that objects are properly instantiated
        assert all(isinstance(c, Constraint) for c in constraints)
        assert all(isinstance(o, Option) for o in options)
        
        # Check that constraints have proper attributes
        performance_constraint = next(c for c in constraints if c.name == "Performance")
        assert performance_constraint.weight == 0.9
        assert performance_constraint.priority == Priority.REQUIRED
        assert performance_constraint.type == ConstraintType.NUMERIC
        
        # Check that options have proper attributes
        rest_option = next(o for o in options if o.name == "REST API")
        assert rest_option.description == "Traditional REST-based API"
        assert "protocol" in rest_option.attributes
    
    def test_apply_template_invalid_id(self):
        """Test applying template with invalid ID raises error."""
        with pytest.raises(ValueError, match="Template 'invalid_id' not found"):
            self.engine.apply_template("invalid_id")
    
    def test_constraint_template_to_constraint(self):
        """Test converting ConstraintTemplate to Constraint."""
        template = ConstraintTemplate(
            name="Test Constraint",
            description="A test constraint",
            type=ConstraintType.NUMERIC,
            default_weight=0.8,
            priority=Priority.REQUIRED,
            scale={
                "min": 0,
                "max": 100,
                "unit": "points",
                "direction": "higher-better"
            }
        )
        
        constraint = template.to_constraint()
        
        assert isinstance(constraint, Constraint)
        assert constraint.name == "Test Constraint"
        assert constraint.description == "A test constraint"
        assert constraint.weight == 0.8
        assert constraint.priority == Priority.REQUIRED
        assert constraint.type == ConstraintType.NUMERIC
        assert constraint.scale is not None
        assert constraint.scale.min == 0
        assert constraint.scale.max == 100
    
    def test_option_template_to_option(self):
        """Test converting OptionTemplate to Option."""
        template = OptionTemplate(
            name="Test Option",
            description="A test option",
            typical_attributes={"key": "value"},
            metadata={"source": "test"}
        )
        
        option = template.to_option()
        
        assert isinstance(option, Option)
        assert option.name == "Test Option"
        assert option.description == "A test option"
        assert option.attributes == {"key": "value"}
        assert option.metadata == {"source": "test"}
    
    def test_constraint_pre_population(self):
        """Test that template constraints are properly pre-populated."""
        constraints, _ = self.engine.apply_template("database_selection")
        
        # Check that all constraints have proper default values
        for constraint in constraints:
            assert constraint.name.strip() != ""
            assert constraint.description.strip() != ""
            assert 0.0 <= constraint.weight <= 1.0
            assert constraint.priority in [Priority.REQUIRED, Priority.PREFERRED, Priority.NICE_TO_HAVE]
            assert constraint.type in [ConstraintType.NUMERIC, ConstraintType.CATEGORICAL, ConstraintType.BOOLEAN]
        
        # Check specific constraint configurations
        performance_constraint = next(c for c in constraints if c.name == "Performance")
        assert performance_constraint.weight == 0.9
        assert performance_constraint.priority == Priority.REQUIRED
        
        cost_constraint = next(c for c in constraints if c.name == "Cost")
        assert cost_constraint.weight == 0.6
        assert cost_constraint.priority == Priority.PREFERRED
    
    def test_template_analysis_preferences(self):
        """Test that templates include analysis preferences."""
        template = self.engine.get_template("api_comparison")
        
        assert "analysis_preferences" in template.__dict__
        prefs = template.analysis_preferences
        
        assert "default_method" in prefs
        assert "visualizations" in prefs
        assert "export_formats" in prefs
        
        assert prefs["default_method"] == "weighted_scoring"
        assert isinstance(prefs["visualizations"], list)
        assert isinstance(prefs["export_formats"], list)


class TestCustomConstraints:
    """Test cases for custom constraint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemplateEngine()
    
    def test_create_custom_numeric_constraint(self):
        """Test creating a custom numeric constraint."""
        constraint = self.engine.create_custom_constraint(
            name="Custom Performance",
            description="Custom performance metric",
            constraint_type=ConstraintType.NUMERIC,
            weight=0.8,
            priority=Priority.REQUIRED,
            scale_config={
                "min": 0,
                "max": 1000,
                "unit": "ms",
                "direction": "lower-better",
                "normalization_method": "min-max"
            }
        )
        
        assert constraint.name == "Custom Performance"
        assert constraint.description == "Custom performance metric"
        assert constraint.weight == 0.8
        assert constraint.priority == Priority.REQUIRED
        assert constraint.type == ConstraintType.NUMERIC
        assert constraint.scale is not None
        assert constraint.scale.min == 0
        assert constraint.scale.max == 1000
        assert constraint.scale.unit == "ms"
        assert constraint.scale.direction == "lower-better"
    
    def test_create_custom_categorical_constraint(self):
        """Test creating a custom categorical constraint."""
        constraint = self.engine.create_custom_constraint(
            name="Custom Quality",
            description="Custom quality rating",
            constraint_type=ConstraintType.CATEGORICAL,
            weight=0.6,
            priority=Priority.PREFERRED,
            scale_config={
                "values": ["Poor", "Good", "Excellent"],
                "scores": [1, 2, 3],
                "ordered": True
            }
        )
        
        assert constraint.name == "Custom Quality"
        assert constraint.type == ConstraintType.CATEGORICAL
        assert constraint.scale is not None
        assert constraint.scale.values == ["Poor", "Good", "Excellent"]
        assert constraint.scale.scores == [1, 2, 3]
        assert constraint.scale.ordered is True
    
    def test_create_custom_boolean_constraint(self):
        """Test creating a custom boolean constraint."""
        constraint = self.engine.create_custom_constraint(
            name="Has Feature X",
            description="Whether the option supports feature X",
            constraint_type=ConstraintType.BOOLEAN,
            weight=0.5,
            priority=Priority.NICE_TO_HAVE
        )
        
        assert constraint.name == "Has Feature X"
        assert constraint.type == ConstraintType.BOOLEAN
        assert constraint.weight == 0.5
        assert constraint.priority == Priority.NICE_TO_HAVE
        assert constraint.scale is None  # Boolean constraints don't need scales
    
    def test_create_custom_constraint_validation_errors(self):
        """Test validation errors when creating custom constraints."""
        # Empty name
        with pytest.raises(ValueError, match="Constraint name cannot be empty"):
            self.engine.create_custom_constraint("", "Description", ConstraintType.NUMERIC)
        
        # Empty description
        with pytest.raises(ValueError, match="Constraint description cannot be empty"):
            self.engine.create_custom_constraint("Name", "", ConstraintType.NUMERIC)
        
        # Invalid weight
        with pytest.raises(ValueError, match="Constraint weight must be between 0.0 and 1.0"):
            self.engine.create_custom_constraint("Name", "Description", ConstraintType.NUMERIC, weight=1.5)
        
        # Invalid numeric scale - missing required fields
        with pytest.raises(ValueError, match="Numeric scale must include"):
            self.engine.create_custom_constraint(
                "Name", "Description", ConstraintType.NUMERIC,
                scale_config={"min": 0}  # Missing max
            )
        
        # Invalid categorical scale - missing required fields
        with pytest.raises(ValueError, match="Categorical scale must include"):
            self.engine.create_custom_constraint(
                "Name", "Description", ConstraintType.CATEGORICAL,
                scale_config={"values": ["A", "B"]}  # Missing scores
            )
        
        # Invalid categorical scale - mismatched lengths
        with pytest.raises(ValueError, match="values and scores must have same length"):
            self.engine.create_custom_constraint(
                "Name", "Description", ConstraintType.CATEGORICAL,
                scale_config={
                    "values": ["A", "B", "C"],
                    "scores": [1, 2]  # Different length
                }
            )
    
    def test_validate_custom_constraint_success(self):
        """Test validation of valid custom constraints."""
        constraint = self.engine.create_custom_constraint(
            "Valid Constraint",
            "A valid constraint",
            ConstraintType.NUMERIC,
            weight=0.7,
            scale_config={"min": 0, "max": 100}
        )
        
        errors = self.engine.validate_custom_constraint(constraint)
        assert len(errors) == 0
    
    def test_validate_custom_constraint_errors(self):
        """Test validation errors for invalid custom constraints."""
        # Create constraint with valid data first, then modify to test validation
        constraint = Constraint(
            name="Valid Name",
            description="Valid Description",
            weight=0.5,
            type=ConstraintType.NUMERIC
        )
        
        # Modify to invalid values to test validation method
        constraint.name = ""
        constraint.description = ""
        constraint.weight = 1.5
        
        errors = self.engine.validate_custom_constraint(constraint)
        
        assert len(errors) >= 3
        assert any("name cannot be empty" in error for error in errors)
        assert any("description cannot be empty" in error for error in errors)
        assert any("weight must be between 0.0 and 1.0" in error for error in errors)
    
    def test_validate_numeric_constraint_scale_errors(self):
        """Test validation errors for numeric constraint scales."""
        from option_comparison_tool.models import NumericScale
        
        # Create constraint with invalid numeric scale
        constraint = Constraint(
            name="Test",
            description="Test constraint",
            weight=0.5,
            type=ConstraintType.NUMERIC,
            scale=NumericScale(min=100, max=50)  # min > max
        )
        
        errors = self.engine.validate_custom_constraint(constraint)
        assert any("minimum must be less than maximum" in error for error in errors)
    
    def test_validate_categorical_constraint_scale_errors(self):
        """Test validation errors for categorical constraint scales."""
        from option_comparison_tool.models import CategoricalScale
        
        # Create constraint with invalid categorical scale
        constraint = Constraint(
            name="Test",
            description="Test constraint",
            weight=0.5,
            type=ConstraintType.CATEGORICAL,
            scale=CategoricalScale(
                values=["A", "B", "C"],
                scores=[1, 2]  # Mismatched lengths
            )
        )
        
        errors = self.engine.validate_custom_constraint(constraint)
        assert any("values and scores must have same length" in error for error in errors)
        
        # Test with too few values
        constraint.scale = CategoricalScale(values=["A"], scores=[1])
        errors = self.engine.validate_custom_constraint(constraint)
        assert any("must have at least 2 values" in error for error in errors)

from hypothesis import given, strategies as st


class TestCustomConstraintsProperties:
    """Property-based tests for custom constraint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TemplateEngine()
    
    @given(st.data())
    def test_property_custom_constraint_support(self, data):
        """
        **Property 19: Custom Constraint Support**
        *For any* scenario where templates are insufficient, the system should allow users to define 
        custom constraints with appropriate validation.
        **Validates: Requirements 7.4**
        """
        # Generate test data
        name = data.draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip()))
        description = data.draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip()))
        weight = data.draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
        constraint_type = data.draw(st.sampled_from([ConstraintType.NUMERIC, ConstraintType.CATEGORICAL, ConstraintType.BOOLEAN]))
        priority = data.draw(st.sampled_from([Priority.REQUIRED, Priority.PREFERRED, Priority.NICE_TO_HAVE]))
        
        # Generate appropriate scale config based on constraint type
        scale_config = None
        if constraint_type == ConstraintType.NUMERIC:
            min_val = data.draw(st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
            max_val = min_val + abs(data.draw(st.floats(min_value=1, max_value=1000, allow_nan=False, allow_infinity=False)))
            scale_config = {
                "min": min_val,
                "max": max_val,
                "unit": data.draw(st.text(min_size=0, max_size=10)),
                "direction": data.draw(st.sampled_from(["higher-better", "lower-better"])),
                "normalization_method": data.draw(st.sampled_from(["min-max", "z-score"]))
            }
        elif constraint_type == ConstraintType.CATEGORICAL:
            num_values = data.draw(st.integers(min_value=2, max_value=10))
            values = [f"Value_{i}" for i in range(num_values)]
            scores = list(range(1, num_values + 1))
            scale_config = {
                "values": values,
                "scores": scores,
                "ordered": data.draw(st.booleans())
            }
        
        # Create custom constraint
        constraint = self.engine.create_custom_constraint(
            name=name,
            description=description,
            constraint_type=constraint_type,
            weight=weight,
            priority=priority,
            scale_config=scale_config
        )
        
        # Verify the constraint was created successfully
        assert constraint is not None
        assert isinstance(constraint, Constraint)
        assert constraint.name == name
        assert constraint.description == description
        assert constraint.weight == weight
        assert constraint.type == constraint_type
        assert constraint.priority == priority
        
        # Verify scale is set correctly based on type
        if constraint_type == ConstraintType.NUMERIC and scale_config:
            assert constraint.scale is not None
            assert constraint.scale.min == scale_config["min"]
            assert constraint.scale.max == scale_config["max"]
        elif constraint_type == ConstraintType.CATEGORICAL and scale_config:
            assert constraint.scale is not None
            assert constraint.scale.values == scale_config["values"]
            assert constraint.scale.scores == scale_config["scores"]
        elif constraint_type == ConstraintType.BOOLEAN:
            # Boolean constraints don't need scales
            assert constraint.scale is None
        
        # Verify validation passes for valid constraint
        validation_errors = self.engine.validate_custom_constraint(constraint)
        assert len(validation_errors) == 0, f"Valid constraint failed validation: {validation_errors}"
    
    @given(st.data())
    def test_property_custom_constraint_validation_errors(self, data):
        """
        Property test for custom constraint validation errors.
        *For any* invalid constraint parameters, the system should identify and report validation errors.
        """
        # Generate invalid parameters
        invalid_name = data.draw(st.one_of(st.just(""), st.text().filter(lambda x: not x.strip())))
        invalid_description = data.draw(st.one_of(st.just(""), st.text().filter(lambda x: not x.strip())))
        invalid_weight = data.draw(st.one_of(
            st.floats(min_value=-10.0, max_value=-0.1),
            st.floats(min_value=1.1, max_value=10.0)
        ).filter(lambda x: not (0.0 <= x <= 1.0)))
        # Test invalid name
        try:
            self.engine.create_custom_constraint(
                name=invalid_name,
                description="Valid description",
                constraint_type=ConstraintType.NUMERIC
            )
            assert False, "Should have raised ValueError for invalid name"
        except ValueError as e:
            assert "name cannot be empty" in str(e)
        
        # Test invalid description
        try:
            self.engine.create_custom_constraint(
                name="Valid Name",
                description=invalid_description,
                constraint_type=ConstraintType.NUMERIC
            )
            assert False, "Should have raised ValueError for invalid description"
        except ValueError as e:
            assert "description cannot be empty" in str(e)
        
        # Test invalid weight
        try:
            self.engine.create_custom_constraint(
                name="Valid Name",
                description="Valid description",
                constraint_type=ConstraintType.NUMERIC,
                weight=invalid_weight
            )
            assert False, "Should have raised ValueError for invalid weight"
        except ValueError as e:
            assert "weight must be between 0.0 and 1.0" in str(e)