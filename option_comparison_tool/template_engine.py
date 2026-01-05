"""
Template engine for pre-built comparison templates.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pathlib import Path

from .models import Constraint, Option, ConstraintType, Priority, NumericScale, CategoricalScale
from .config import logger


class TemplateDomain(Enum):
    """Supported template domains."""
    API = "api"
    CLOUD_SERVICES = "cloud_services"
    TECH_STACK = "tech_stack"
    DATABASE = "database"


@dataclass
class ConstraintTemplate:
    """Template for creating constraints."""
    name: str
    description: str
    type: ConstraintType
    default_weight: float = 1.0
    priority: Priority = Priority.PREFERRED
    scale: Optional[Dict[str, Any]] = None
    help_text: Optional[str] = None

    def to_constraint(self) -> Constraint:
        """Convert template to actual constraint."""
        constraint = Constraint(
            name=self.name,
            description=self.description,
            weight=self.default_weight,
            priority=self.priority,
            type=self.type
        )
        
        # Set up scale based on type and template data
        if self.scale and self.type == ConstraintType.NUMERIC:
            constraint.scale = NumericScale(**self.scale)
        elif self.scale and self.type == ConstraintType.CATEGORICAL:
            constraint.scale = CategoricalScale(**self.scale)
            
        return constraint


@dataclass
class OptionTemplate:
    """Template for suggesting options."""
    name: str
    description: str
    typical_attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_option(self) -> Option:
        """Convert template to actual option."""
        return Option(
            name=self.name,
            description=self.description,
            attributes=self.typical_attributes.copy(),
            metadata=self.metadata.copy()
        )


@dataclass
class Template:
    """Complete comparison template."""
    id: str
    name: str
    description: str
    domain: TemplateDomain
    constraints: List[ConstraintTemplate] = field(default_factory=list)
    suggested_options: List[OptionTemplate] = field(default_factory=list)
    analysis_preferences: Dict[str, Any] = field(default_factory=dict)


class TemplateEngine:
    """Engine for managing and applying comparison templates."""
    
    def __init__(self):
        """Initialize the template engine with built-in templates."""
        self._templates: Dict[str, Template] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load all built-in templates."""
        self._templates.update({
            "api_comparison": self._create_api_template(),
            "cloud_services": self._create_cloud_services_template(),
            "tech_stack": self._create_tech_stack_template(),
            "database_selection": self._create_database_template()
        })
        logger.info(f"Loaded {len(self._templates)} built-in templates")
    
    def _create_api_template(self) -> Template:
        """Create API comparison template."""
        constraints = [
            ConstraintTemplate(
                name="Performance",
                description="API response time and throughput",
                type=ConstraintType.NUMERIC,
                default_weight=0.9,
                priority=Priority.REQUIRED,
                scale={
                    "min": 0,
                    "max": 5000,
                    "unit": "ms",
                    "direction": "lower-better",
                    "normalization_method": "min-max"
                },
                help_text="Lower response times are better"
            ),
            ConstraintTemplate(
                name="Reliability",
                description="API uptime and error rates",
                type=ConstraintType.NUMERIC,
                default_weight=0.95,
                priority=Priority.REQUIRED,
                scale={
                    "min": 90.0,
                    "max": 100.0,
                    "unit": "%",
                    "direction": "higher-better",
                    "normalization_method": "min-max"
                },
                help_text="Higher uptime percentages are better"
            ),
            ConstraintTemplate(
                name="Cost",
                description="Monthly cost per 1000 requests",
                type=ConstraintType.NUMERIC,
                default_weight=0.7,
                priority=Priority.PREFERRED,
                scale={
                    "min": 0,
                    "max": 100,
                    "unit": "$",
                    "direction": "lower-better",
                    "normalization_method": "min-max"
                },
                help_text="Lower costs are better"
            ),
            ConstraintTemplate(
                name="Documentation Quality",
                description="Quality and completeness of API documentation",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.6,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Poor", "Fair", "Good", "Excellent"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Rate the quality of documentation and examples"
            ),
            ConstraintTemplate(
                name="Rate Limiting",
                description="API rate limiting policies",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.5,
                priority=Priority.NICE_TO_HAVE,
                scale={
                    "values": ["Very Restrictive", "Moderate", "Generous", "No Limits"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="More generous rate limits are better"
            ),
            ConstraintTemplate(
                name="Authentication",
                description="Supported authentication methods",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.4,
                priority=Priority.NICE_TO_HAVE,
                scale={
                    "values": ["API Key", "OAuth 1.0", "OAuth 2.0", "JWT", "Multiple Methods"],
                    "scores": [1, 2, 3, 3, 4],
                    "ordered": False
                },
                help_text="Multiple authentication options provide flexibility"
            )
        ]
        
        suggested_options = [
            OptionTemplate(
                name="REST API",
                description="Traditional REST-based API",
                typical_attributes={
                    "protocol": "HTTP/HTTPS",
                    "data_format": "JSON",
                    "caching": "Standard HTTP caching"
                }
            ),
            OptionTemplate(
                name="GraphQL API",
                description="GraphQL-based API with flexible queries",
                typical_attributes={
                    "protocol": "HTTP/HTTPS",
                    "data_format": "JSON",
                    "query_flexibility": "High"
                }
            ),
            OptionTemplate(
                name="gRPC API",
                description="High-performance RPC framework",
                typical_attributes={
                    "protocol": "HTTP/2",
                    "data_format": "Protocol Buffers",
                    "streaming": "Bidirectional"
                }
            )
        ]
        
        return Template(
            id="api_comparison",
            name="API Comparison",
            description="Compare different APIs or web services",
            domain=TemplateDomain.API,
            constraints=constraints,
            suggested_options=suggested_options,
            analysis_preferences={
                "default_method": "weighted_scoring",
                "visualizations": ["table", "radar", "bar"],
                "export_formats": ["pdf", "markdown", "json"]
            }
        )
    
    def _create_cloud_services_template(self) -> Template:
        """Create cloud services comparison template."""
        constraints = [
            ConstraintTemplate(
                name="Cost",
                description="Monthly cost for typical usage",
                type=ConstraintType.NUMERIC,
                default_weight=0.8,
                priority=Priority.REQUIRED,
                scale={
                    "min": 0,
                    "max": 10000,
                    "unit": "$",
                    "direction": "lower-better",
                    "normalization_method": "min-max"
                },
                help_text="Lower monthly costs are better"
            ),
            ConstraintTemplate(
                name="Performance",
                description="Service performance and speed",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.9,
                priority=Priority.REQUIRED,
                scale={
                    "values": ["Slow", "Average", "Fast", "Very Fast"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Faster performance is better"
            ),
            ConstraintTemplate(
                name="Scalability",
                description="Ability to scale with demand",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.7,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Limited", "Moderate", "High", "Auto-scaling"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Better scalability provides more flexibility"
            ),
            ConstraintTemplate(
                name="Global Availability",
                description="Geographic distribution and availability",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.6,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Single Region", "Multi-Region", "Global", "Edge Locations"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Wider geographic coverage is better"
            ),
            ConstraintTemplate(
                name="Support Quality",
                description="Customer support and documentation",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.5,
                priority=Priority.NICE_TO_HAVE,
                scale={
                    "values": ["Community Only", "Email Support", "24/7 Support", "Premium Support"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Better support reduces operational risk"
            )
        ]
        
        suggested_options = [
            OptionTemplate(
                name="AWS",
                description="Amazon Web Services",
                typical_attributes={
                    "provider": "Amazon",
                    "market_share": "Leading",
                    "service_breadth": "Comprehensive"
                }
            ),
            OptionTemplate(
                name="Azure",
                description="Microsoft Azure",
                typical_attributes={
                    "provider": "Microsoft",
                    "enterprise_focus": "High",
                    "hybrid_cloud": "Strong"
                }
            ),
            OptionTemplate(
                name="Google Cloud",
                description="Google Cloud Platform",
                typical_attributes={
                    "provider": "Google",
                    "ai_ml_focus": "Strong",
                    "data_analytics": "Advanced"
                }
            )
        ]
        
        return Template(
            id="cloud_services",
            name="Cloud Services Comparison",
            description="Compare cloud service providers and offerings",
            domain=TemplateDomain.CLOUD_SERVICES,
            constraints=constraints,
            suggested_options=suggested_options,
            analysis_preferences={
                "default_method": "weighted_scoring",
                "visualizations": ["table", "radar", "scatter"],
                "export_formats": ["pdf", "markdown", "json"]
            }
        )
    
    def _create_tech_stack_template(self) -> Template:
        """Create technology stack comparison template."""
        constraints = [
            ConstraintTemplate(
                name="Learning Curve",
                description="Difficulty of learning and adoption",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.7,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Very Steep", "Steep", "Moderate", "Easy"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Easier learning curves reduce time to productivity"
            ),
            ConstraintTemplate(
                name="Community Support",
                description="Size and activity of developer community",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.8,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Small", "Growing", "Large", "Very Large"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Larger communities provide better support and resources"
            ),
            ConstraintTemplate(
                name="Performance",
                description="Runtime performance and efficiency",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.9,
                priority=Priority.REQUIRED,
                scale={
                    "values": ["Slow", "Average", "Fast", "Very Fast"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Better performance improves user experience"
            ),
            ConstraintTemplate(
                name="Ecosystem Maturity",
                description="Maturity of libraries and tooling",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.6,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Emerging", "Growing", "Mature", "Very Mature"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Mature ecosystems have more stable libraries and tools"
            ),
            ConstraintTemplate(
                name="Job Market",
                description="Availability of developers and job opportunities",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.5,
                priority=Priority.NICE_TO_HAVE,
                scale={
                    "values": ["Limited", "Moderate", "Good", "Excellent"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Better job markets make hiring and career growth easier"
            )
        ]
        
        suggested_options = [
            OptionTemplate(
                name="React + Node.js",
                description="JavaScript full-stack with React frontend",
                typical_attributes={
                    "language": "JavaScript",
                    "type": "Full-stack",
                    "paradigm": "Component-based"
                }
            ),
            OptionTemplate(
                name="Vue.js + Express",
                description="Progressive JavaScript framework with Express backend",
                typical_attributes={
                    "language": "JavaScript",
                    "type": "Full-stack",
                    "paradigm": "Progressive"
                }
            ),
            OptionTemplate(
                name="Django + Python",
                description="Python web framework with batteries included",
                typical_attributes={
                    "language": "Python",
                    "type": "Backend-focused",
                    "paradigm": "Batteries included"
                }
            )
        ]
        
        return Template(
            id="tech_stack",
            name="Technology Stack Comparison",
            description="Compare different technology stacks and frameworks",
            domain=TemplateDomain.TECH_STACK,
            constraints=constraints,
            suggested_options=suggested_options,
            analysis_preferences={
                "default_method": "weighted_scoring",
                "visualizations": ["table", "radar", "matrix"],
                "export_formats": ["pdf", "markdown", "json"]
            }
        )
    
    def _create_database_template(self) -> Template:
        """Create database comparison template."""
        constraints = [
            ConstraintTemplate(
                name="Performance",
                description="Query performance and throughput",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.9,
                priority=Priority.REQUIRED,
                scale={
                    "values": ["Slow", "Average", "Fast", "Very Fast"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Faster query performance improves application responsiveness"
            ),
            ConstraintTemplate(
                name="Scalability",
                description="Ability to handle growing data and load",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.8,
                priority=Priority.REQUIRED,
                scale={
                    "values": ["Limited", "Vertical Only", "Horizontal", "Auto-scaling"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Better scalability supports business growth"
            ),
            ConstraintTemplate(
                name="ACID Compliance",
                description="Support for ACID transactions",
                type=ConstraintType.BOOLEAN,
                default_weight=0.7,
                priority=Priority.PREFERRED,
                help_text="ACID compliance ensures data consistency"
            ),
            ConstraintTemplate(
                name="Query Flexibility",
                description="Flexibility and power of query language",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.6,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Basic", "Moderate", "Advanced", "Full SQL"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="More flexible queries enable complex data operations"
            ),
            ConstraintTemplate(
                name="Operational Complexity",
                description="Complexity of setup, maintenance, and operations",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.5,
                priority=Priority.NICE_TO_HAVE,
                scale={
                    "values": ["Very Complex", "Complex", "Moderate", "Simple"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Lower operational complexity reduces maintenance burden"
            ),
            ConstraintTemplate(
                name="Cost",
                description="Total cost of ownership including licensing",
                type=ConstraintType.CATEGORICAL,
                default_weight=0.6,
                priority=Priority.PREFERRED,
                scale={
                    "values": ["Very Expensive", "Expensive", "Moderate", "Low Cost"],
                    "scores": [1, 2, 3, 4],
                    "ordered": True
                },
                help_text="Lower costs improve project economics"
            )
        ]
        
        suggested_options = [
            OptionTemplate(
                name="PostgreSQL",
                description="Advanced open-source relational database",
                typical_attributes={
                    "type": "Relational",
                    "license": "Open Source",
                    "sql_compliance": "High"
                }
            ),
            OptionTemplate(
                name="MongoDB",
                description="Document-oriented NoSQL database",
                typical_attributes={
                    "type": "Document",
                    "license": "Open Source",
                    "schema": "Flexible"
                }
            ),
            OptionTemplate(
                name="Redis",
                description="In-memory data structure store",
                typical_attributes={
                    "type": "Key-Value",
                    "storage": "In-Memory",
                    "use_case": "Caching/Sessions"
                }
            )
        ]
        
        return Template(
            id="database_selection",
            name="Database Selection",
            description="Compare different database systems and technologies",
            domain=TemplateDomain.DATABASE,
            constraints=constraints,
            suggested_options=suggested_options,
            analysis_preferences={
                "default_method": "weighted_scoring",
                "visualizations": ["table", "radar", "bar"],
                "export_formats": ["pdf", "markdown", "json"]
            }
        )
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def list_templates(self) -> List[Template]:
        """Get all available templates."""
        return list(self._templates.values())
    
    def get_templates_by_domain(self, domain: TemplateDomain) -> List[Template]:
        """Get templates for a specific domain."""
        return [t for t in self._templates.values() if t.domain == domain]
    
    def apply_template(self, template_id: str) -> tuple[List[Constraint], List[Option]]:
        """Apply a template to generate constraints and suggested options."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        
        # Convert constraint templates to actual constraints
        constraints = [ct.to_constraint() for ct in template.constraints]
        
        # Convert option templates to actual options
        options = [ot.to_option() for ot in template.suggested_options]
        
        logger.info(f"Applied template '{template_id}': {len(constraints)} constraints, {len(options)} options")
        return constraints, options
    
    def create_custom_constraint(self, name: str, description: str, 
                                constraint_type: ConstraintType, weight: float = 1.0,
                                priority: Priority = Priority.PREFERRED,
                                scale_config: Optional[Dict[str, Any]] = None) -> Constraint:
        """Create a custom constraint with validation."""
        if not name.strip():
            raise ValueError("Constraint name cannot be empty")
        
        if not description.strip():
            raise ValueError("Constraint description cannot be empty")
        
        if not (0.0 <= weight <= 1.0):
            raise ValueError("Constraint weight must be between 0.0 and 1.0")
        
        constraint = Constraint(
            name=name,
            description=description,
            weight=weight,
            priority=priority,
            type=constraint_type
        )
        
        # Set up scale if provided
        if scale_config:
            if constraint_type == ConstraintType.NUMERIC:
                # Validate numeric scale configuration
                required_fields = ["min", "max"]
                if not all(field in scale_config for field in required_fields):
                    raise ValueError(f"Numeric scale must include: {required_fields}")
                constraint.scale = NumericScale(**scale_config)
            elif constraint_type == ConstraintType.CATEGORICAL:
                # Validate categorical scale configuration
                required_fields = ["values", "scores"]
                if not all(field in scale_config for field in required_fields):
                    raise ValueError(f"Categorical scale must include: {required_fields}")
                if len(scale_config["values"]) != len(scale_config["scores"]):
                    raise ValueError("Categorical scale values and scores must have same length")
                constraint.scale = CategoricalScale(**scale_config)
        
        logger.info(f"Created custom constraint: {name} ({constraint_type.value})")
        return constraint
    
    def validate_custom_constraint(self, constraint: Constraint) -> List[str]:
        """Validate a custom constraint and return any validation errors."""
        errors = []
        
        if not constraint.name.strip():
            errors.append("Constraint name cannot be empty")
        
        if not constraint.description.strip():
            errors.append("Constraint description cannot be empty")
        
        if not (0.0 <= constraint.weight <= 1.0):
            errors.append("Constraint weight must be between 0.0 and 1.0")
        
        # Validate scale based on constraint type
        if constraint.type == ConstraintType.NUMERIC and constraint.scale:
            if not isinstance(constraint.scale, NumericScale):
                errors.append("Numeric constraint must have NumericScale")
            elif constraint.scale.min >= constraint.scale.max:
                errors.append("Numeric scale minimum must be less than maximum")
        
        elif constraint.type == ConstraintType.CATEGORICAL and constraint.scale:
            if not isinstance(constraint.scale, CategoricalScale):
                errors.append("Categorical constraint must have CategoricalScale")
            elif len(constraint.scale.values) != len(constraint.scale.scores):
                errors.append("Categorical scale values and scores must have same length")
            elif len(constraint.scale.values) < 2:
                errors.append("Categorical scale must have at least 2 values")
        
        return errors