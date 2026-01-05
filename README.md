# Option Comparison Tool

A Python-based tool to master Agent Steering by comparing multiple alternatives with structured analysis and explaining complex trade-offs, instead of giving a single answer. The goal is to help users choose, not just consume information.

## Installation

```bash
pip install -e .
```

## CLI Usage

The tool provides a command-line interface for creating and analyzing comparisons:

### Basic Commands

```bash
# List available templates
option-compare templates

# Create a comparison using a template
option-compare create --template api_comparison

# List all comparison sessions
option-compare list-sessions

# Show details of a specific session
option-compare show <session-id>

# Run analysis on a session
option-compare analyze <session-id>

# Export analysis results
option-compare analyze <session-id> --export json --export markdown
```

### Interactive Mode

```bash
# Create a comparison interactively
option-compare create --interactive
```

### Advanced Features

```bash
# Adjust constraint weights and see impact
option-compare adjust <session-id>

# Create what-if scenarios
option-compare whatif <session-id> --name "High Performance Scenario"
```

### Available Templates

- **api_comparison**: Compare different APIs or web services
- **cloud_services**: Compare cloud service providers and offerings  
- **tech_stack**: Compare different technology stacks and frameworks
- **database_selection**: Compare different database systems and technologies

## Features

- **Multi-criteria Analysis**: Weighted scoring with customizable constraints
- **Trade-off Identification**: Automatic detection of competing factors
- **Executive Summaries**: Clear recommendations with reasoning
- **Multiple Export Formats**: JSON, Markdown, and PDF support
- **Interactive Exploration**: What-if scenarios and weight adjustments
- **Template System**: Pre-built templates for common comparison scenarios

## Example Workflow

```bash
# 1. List available templates
option-compare templates

# 2. Create a new comparison
option-compare create --template api_comparison

# 3. Show the comparison details
option-compare show <session-id>

# 4. Run analysis
option-compare analyze <session-id>

# 5. Export results
option-compare analyze <session-id> --export json --export markdown
```

## Project Structure

```
option-comparison-tool/
├── option_comparison_tool/       # Main package
│   ├── __init__.py               # Package initialization
│   ├── models.py                 # Core data models
│   └── config.py                 # Configuration and logging
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_models.py            # Unit tests for models
│   └── test_data_persistence.py  # Property-based tests
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── setup.py                      # Package setup
└── README.md                     # This file
```

## Core Data Models

- **Option**: Represents a single alternative in a comparison
- **Constraint**: Represents criteria for evaluation (cost, performance, etc.)
- **ComparisonSession**: Manages a complete comparison with options and constraints
- **NumericScale** / **CategoricalScale**: Define measurement scales for constraints

## Features

- Support for 2-10 options per comparison
- Multiple constraint types (numeric, categorical, boolean)
- Constraint prioritization (required, preferred, nice-to-have)
- Data persistence with round-trip validation
- Comprehensive property-based testing

## Installation

```bash
pip install -r requirements.txt
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py
```

## Development Status

This is the initial implementation focusing on core data models and project structure. Future tasks will add:

- Comparison engine and analysis algorithms
- Weighted scoring and trade-off analysis
- Multiple output formats
- Template system for common scenarios
- Command-line and web interfaces
