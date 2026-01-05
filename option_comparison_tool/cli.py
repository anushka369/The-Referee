"""
Command-line interface for the Option Comparison Tool.

This module provides a comprehensive CLI for creating comparisons, loading templates,
setting constraints, and running interactive comparisons. Supports all requirements
via command-line interface.
"""

import click
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from .comparison_manager import ComparisonManager
from .template_engine import TemplateEngine, TemplateDomain
from .models import Option, Constraint, ConstraintType, Priority, NumericScale, CategoricalScale
from .weighted_scoring import WeightedScoringAnalyzer
from .tradeoff_analyzer import TradeoffAnalyzer
from .results_formatter import ResultsFormatter, OutputFormat
from .executive_summary import ExecutiveSummaryGenerator
from .export_engine import ExportEngine
from .config import Config
from .integration import get_system_integrator

console = Console()


class CLIContext:
    """Context object for CLI state management."""
    
    def __init__(self):
        self.system_integrator = get_system_integrator()
        self.comparison_manager = self.system_integrator._comparison_manager
        self.template_engine = self.system_integrator._template_engine
        self.export_engine = self.system_integrator._export_engine
        self.current_session_id: Optional[str] = None


@click.group()
@click.pass_context
def cli(ctx):
    """Option Comparison Tool - Compare multiple options with structured analysis."""
    ctx.ensure_object(dict)
    ctx.obj['cli_context'] = CLIContext()


@cli.command()
@click.option('--template', '-t', help='Template to use for comparison')
@click.option('--interactive', '-i', is_flag=True, help='Run in interactive mode')
@click.option('--name', help='Name for the comparison session')
@click.pass_context
def create(ctx, template: Optional[str], interactive: bool, name: Optional[str]):
    """Create a new comparison session."""
    cli_ctx = ctx.obj['cli_context']
    
    try:
        if interactive:
            session = _create_interactive_comparison(cli_ctx, template)
        else:
            session = _create_basic_comparison(cli_ctx, template, name)
        
        cli_ctx.current_session_id = session.id
        
        console.print(f"\n✅ Created comparison session: [bold green]{session.id}[/bold green]")
        if template:
            console.print(f"📋 Using template: [bold blue]{template}[/bold blue]")
        console.print(f"📊 Options: {len(session.options)}, Constraints: {len(session.constraints)}")
        
    except Exception as e:
        console.print(f"❌ Error creating comparison: [bold red]{str(e)}[/bold red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def templates(ctx):
    """List available templates."""
    cli_ctx = ctx.obj['cli_context']
    
    templates = cli_ctx.template_engine.list_templates()
    
    if not templates:
        console.print("No templates available.")
        return
    
    table = Table(title="Available Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Domain", style="blue")
    table.add_column("Description", style="white")
    table.add_column("Constraints", justify="center", style="yellow")
    table.add_column("Options", justify="center", style="magenta")
    
    for template in templates:
        table.add_row(
            template.id,
            template.name,
            template.domain.value,
            template.description,
            str(len(template.constraints)),
            str(len(template.suggested_options))
        )
    
    console.print(table)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--method', '-m', default='weighted_scoring', 
              type=click.Choice(['weighted_scoring']), 
              help='Analysis method to use')
@click.option('--export', '-e', multiple=True, 
              type=click.Choice(['json', 'markdown', 'pdf']),
              help='Export formats (can specify multiple)')
@click.pass_context
def analyze(ctx, session_id: Optional[str], method: str, export: Tuple[str]):
    """Run analysis on a comparison session."""
    cli_ctx = ctx.obj['cli_context']
    
    # Use current session if no session_id provided
    if not session_id:
        session_id = cli_ctx.current_session_id
    
    if not session_id:
        console.print("❌ No session ID provided and no current session active.")
        console.print("Use 'create' command first or specify a session ID.")
        sys.exit(1)
    
    session = cli_ctx.comparison_manager.get_session(session_id)
    if not session:
        console.print(f"❌ Session {session_id} not found.")
        sys.exit(1)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running analysis...", total=None)
            
            # Run weighted scoring analysis
            analyzer = WeightedScoringAnalyzer()
            scoring_results = analyzer.analyze(session.options, session.constraints)
            
            # Run trade-off analysis
            progress.update(task, description="Analyzing trade-offs...")
            tradeoff_analyzer = TradeoffAnalyzer()
            tradeoffs = tradeoff_analyzer.analyze_tradeoffs(session.options, session.constraints)
            
            # Generate executive summary
            progress.update(task, description="Generating summary...")
            summary_generator = ExecutiveSummaryGenerator()
            summary = summary_generator.generate_summary(scoring_results, tradeoffs, session.constraints)
            
            # Format results
            progress.update(task, description="Formatting results...")
            formatter = ResultsFormatter()
            formatted_results = formatter.format_results(
                scoring_results, tradeoffs, session.constraints, OutputFormat.TABLE
            )
        
        # Display results
        _display_analysis_results(formatted_results, summary)
        
        # Export if requested
        if export:
            _export_results(cli_ctx, session_id, formatted_results, summary, list(export))
        
    except Exception as e:
        console.print(f"❌ Error running analysis: [bold red]{str(e)}[/bold red]")
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.pass_context
def show(ctx, session_id: Optional[str]):
    """Show details of a comparison session."""
    cli_ctx = ctx.obj['cli_context']
    
    # Use current session if no session_id provided
    if not session_id:
        session_id = cli_ctx.current_session_id
    
    if not session_id:
        console.print("❌ No session ID provided and no current session active.")
        sys.exit(1)
    
    session = cli_ctx.comparison_manager.get_session(session_id)
    if not session:
        console.print(f"❌ Session {session_id} not found.")
        sys.exit(1)
    
    _display_session_details(session)


@cli.command()
@click.pass_context
def list_sessions(ctx):
    """List all comparison sessions."""
    cli_ctx = ctx.obj['cli_context']
    
    session_ids = cli_ctx.comparison_manager.list_sessions()
    
    if not session_ids:
        console.print("No comparison sessions found.")
        return
    
    table = Table(title="Comparison Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Options", justify="center", style="green")
    table.add_column("Constraints", justify="center", style="blue")
    table.add_column("Template", style="yellow")
    table.add_column("Created", style="white")
    
    for session_id in session_ids:
        session = cli_ctx.comparison_manager.get_session(session_id)
        if session:
            table.add_row(
                session_id[:8] + "...",  # Truncate for display
                str(len(session.options)),
                str(len(session.constraints)),
                session.template or "None",
                session.created_at.strftime("%Y-%m-%d %H:%M")
            )
    
    console.print(table)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--constraint', help='Name of constraint to adjust')
@click.option('--weight', type=float, help='New weight value (0.0-1.0)')
@click.pass_context
def adjust(ctx, session_id: Optional[str], constraint: Optional[str], weight: Optional[float]):
    """Adjust constraint weights and see impact analysis."""
    cli_ctx = ctx.obj['cli_context']
    
    # Use current session if no session_id provided
    if not session_id:
        session_id = cli_ctx.current_session_id
    
    if not session_id:
        console.print("❌ No session ID provided and no current session active.")
        sys.exit(1)
    
    session = cli_ctx.comparison_manager.get_session(session_id)
    if not session:
        console.print(f"❌ Session {session_id} not found.")
        sys.exit(1)
    
    try:
        if constraint and weight is not None:
            # Direct adjustment
            weight_adjustments = {constraint: weight}
        else:
            # Interactive adjustment
            weight_adjustments = _interactive_weight_adjustment(session)
        
        if not weight_adjustments:
            console.print("No adjustments made.")
            return
        
        # Apply adjustments and get impact analysis
        updated_session, impact_analysis = cli_ctx.comparison_manager.adjust_constraint_weights(
            session_id, weight_adjustments
        )
        
        # Display impact analysis
        _display_impact_analysis(impact_analysis)
        
    except Exception as e:
        console.print(f"❌ Error adjusting weights: [bold red]{str(e)}[/bold red]")
        sys.exit(1)


@cli.command()
@click.argument('session_id', required=False)
@click.option('--name', help='Name for the what-if scenario')
@click.pass_context
def whatif(ctx, session_id: Optional[str], name: Optional[str]):
    """Create a what-if scenario analysis."""
    cli_ctx = ctx.obj['cli_context']
    
    # Use current session if no session_id provided
    if not session_id:
        session_id = cli_ctx.current_session_id
    
    if not session_id:
        console.print("❌ No session ID provided and no current session active.")
        sys.exit(1)
    
    session = cli_ctx.comparison_manager.get_session(session_id)
    if not session:
        console.print(f"❌ Session {session_id} not found.")
        sys.exit(1)
    
    try:
        scenario_name = name or Prompt.ask("Enter scenario name")
        weight_adjustments = _interactive_weight_adjustment(session)
        
        if not weight_adjustments:
            console.print("No adjustments made.")
            return
        
        # Create what-if scenario
        scenario = cli_ctx.comparison_manager.create_what_if_scenario(
            session_id, scenario_name, weight_adjustments
        )
        
        # Display scenario results
        _display_whatif_scenario(scenario)
        
    except Exception as e:
        console.print(f"❌ Error creating what-if scenario: [bold red]{str(e)}[/bold red]")
        sys.exit(1)


def _create_interactive_comparison(cli_ctx: CLIContext, template: Optional[str]) -> Any:
    """Create a comparison interactively."""
    console.print("\n🚀 [bold blue]Interactive Comparison Creation[/bold blue]")
    
    # Template selection
    if not template:
        template = _select_template_interactive(cli_ctx)
    
    # Apply template if selected
    constraints = []
    options = []
    
    if template:
        try:
            constraints, options = cli_ctx.template_engine.apply_template(template)
            console.print(f"✅ Applied template: [bold green]{template}[/bold green]")
            console.print(f"📋 Loaded {len(constraints)} constraints and {len(options)} suggested options")
        except Exception as e:
            console.print(f"⚠️  Warning: Could not apply template: {e}")
    
    # Option management
    options = _manage_options_interactive(options)
    
    # Constraint management
    constraints = _manage_constraints_interactive(cli_ctx, constraints)
    
    # Create the session
    return cli_ctx.comparison_manager.create_comparison(options, constraints, template)


def _create_basic_comparison(cli_ctx: CLIContext, template: Optional[str], name: Optional[str]) -> Any:
    """Create a basic comparison with minimal interaction."""
    if not template:
        console.print("❌ Template required for non-interactive mode.")
        console.print("Use --interactive flag or specify --template")
        sys.exit(1)
    
    try:
        constraints, options = cli_ctx.template_engine.apply_template(template)
        return cli_ctx.comparison_manager.create_comparison(options, constraints, template)
    except Exception as e:
        console.print(f"❌ Error applying template: {e}")
        sys.exit(1)


def _select_template_interactive(cli_ctx: CLIContext) -> Optional[str]:
    """Interactive template selection."""
    templates = cli_ctx.template_engine.list_templates()
    
    if not templates:
        console.print("No templates available.")
        return None
    
    console.print("\n📋 [bold]Available Templates:[/bold]")
    for i, template in enumerate(templates, 1):
        console.print(f"  {i}. [cyan]{template.name}[/cyan] - {template.description}")
    
    console.print("  0. Skip template (create custom comparison)")
    
    while True:
        try:
            choice = IntPrompt.ask("Select template", default=0)
            if choice == 0:
                return None
            elif 1 <= choice <= len(templates):
                return templates[choice - 1].id
            else:
                console.print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            console.print("\nOperation cancelled.")
            sys.exit(0)


def _manage_options_interactive(initial_options: List[Option]) -> List[Option]:
    """Interactive option management."""
    options = initial_options.copy()
    
    console.print(f"\n🎯 [bold]Option Management[/bold] (Current: {len(options)} options)")
    
    while True:
        if options:
            console.print("\n[bold]Current Options:[/bold]")
            for i, option in enumerate(options, 1):
                console.print(f"  {i}. [green]{option.name}[/green] - {option.description}")
        
        console.print("\nActions:")
        console.print("  1. Add option")
        console.print("  2. Remove option")
        console.print("  3. Edit option")
        console.print("  4. Continue with current options")
        
        try:
            action = IntPrompt.ask("Choose action", default=4)
            
            if action == 1:
                option = _create_option_interactive()
                if option:
                    options.append(option)
            elif action == 2 and options:
                _remove_option_interactive(options)
            elif action == 3 and options:
                _edit_option_interactive(options)
            elif action == 4:
                break
            else:
                console.print("Invalid choice or no options available.")
                
        except KeyboardInterrupt:
            console.print("\nOperation cancelled.")
            sys.exit(0)
    
    if len(options) < 2:
        console.print("❌ At least 2 options are required for comparison.")
        sys.exit(1)
    
    return options


def _create_option_interactive() -> Optional[Option]:
    """Create an option interactively."""
    try:
        name = Prompt.ask("Option name")
        description = Prompt.ask("Option description", default="")
        
        # Simple attributes collection
        attributes = {}
        if Confirm.ask("Add custom attributes?", default=False):
            while True:
                attr_name = Prompt.ask("Attribute name (or press Enter to finish)", default="")
                if not attr_name:
                    break
                attr_value = Prompt.ask(f"Value for {attr_name}")
                attributes[attr_name] = attr_value
        
        return Option(name=name, description=description, attributes=attributes)
        
    except KeyboardInterrupt:
        return None


def _remove_option_interactive(options: List[Option]) -> None:
    """Remove an option interactively."""
    console.print("Select option to remove:")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option.name}")
    
    try:
        choice = IntPrompt.ask("Option to remove", default=0)
        if 1 <= choice <= len(options):
            removed = options.pop(choice - 1)
            console.print(f"Removed: [red]{removed.name}[/red]")
    except (ValueError, KeyboardInterrupt):
        pass


def _edit_option_interactive(options: List[Option]) -> None:
    """Edit an option interactively."""
    console.print("Select option to edit:")
    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option.name}")
    
    try:
        choice = IntPrompt.ask("Option to edit", default=0)
        if 1 <= choice <= len(options):
            option = options[choice - 1]
            
            new_name = Prompt.ask("New name", default=option.name)
            new_description = Prompt.ask("New description", default=option.description)
            
            option.name = new_name
            option.description = new_description
            
            console.print(f"Updated: [green]{option.name}[/green]")
    except (ValueError, KeyboardInterrupt):
        pass


def _manage_constraints_interactive(cli_ctx: CLIContext, initial_constraints: List[Constraint]) -> List[Constraint]:
    """Interactive constraint management."""
    constraints = initial_constraints.copy()
    
    console.print(f"\n⚖️  [bold]Constraint Management[/bold] (Current: {len(constraints)} constraints)")
    
    while True:
        if constraints:
            console.print("\n[bold]Current Constraints:[/bold]")
            for i, constraint in enumerate(constraints, 1):
                console.print(f"  {i}. [blue]{constraint.name}[/blue] (weight: {constraint.weight:.2f}, {constraint.priority.value})")
        
        console.print("\nActions:")
        console.print("  1. Add constraint")
        console.print("  2. Remove constraint")
        console.print("  3. Edit constraint weight")
        console.print("  4. Continue with current constraints")
        
        try:
            action = IntPrompt.ask("Choose action", default=4)
            
            if action == 1:
                constraint = _create_constraint_interactive(cli_ctx)
                if constraint:
                    constraints.append(constraint)
            elif action == 2 and constraints:
                _remove_constraint_interactive(constraints)
            elif action == 3 and constraints:
                _edit_constraint_weight_interactive(constraints)
            elif action == 4:
                break
            else:
                console.print("Invalid choice or no constraints available.")
                
        except KeyboardInterrupt:
            console.print("\nOperation cancelled.")
            sys.exit(0)
    
    return constraints


def _create_constraint_interactive(cli_ctx: CLIContext) -> Optional[Constraint]:
    """Create a constraint interactively."""
    try:
        name = Prompt.ask("Constraint name")
        description = Prompt.ask("Constraint description", default="")
        
        # Constraint type selection
        console.print("Constraint types:")
        console.print("  1. Numeric (e.g., cost, performance)")
        console.print("  2. Categorical (e.g., quality levels)")
        console.print("  3. Boolean (yes/no)")
        
        type_choice = IntPrompt.ask("Select type", default=1)
        constraint_type = {
            1: ConstraintType.NUMERIC,
            2: ConstraintType.CATEGORICAL,
            3: ConstraintType.BOOLEAN
        }.get(type_choice, ConstraintType.NUMERIC)
        
        weight = FloatPrompt.ask("Weight (0.0-1.0)", default=1.0)
        
        # Priority selection
        console.print("Priority levels:")
        console.print("  1. Required")
        console.print("  2. Preferred")
        console.print("  3. Nice-to-have")
        
        priority_choice = IntPrompt.ask("Select priority", default=2)
        priority = {
            1: Priority.REQUIRED,
            2: Priority.PREFERRED,
            3: Priority.NICE_TO_HAVE
        }.get(priority_choice, Priority.PREFERRED)
        
        # Create constraint using template engine for validation
        return cli_ctx.template_engine.create_custom_constraint(
            name, description, constraint_type, weight, priority
        )
        
    except KeyboardInterrupt:
        return None
    except Exception as e:
        console.print(f"Error creating constraint: {e}")
        return None


def _remove_constraint_interactive(constraints: List[Constraint]) -> None:
    """Remove a constraint interactively."""
    console.print("Select constraint to remove:")
    for i, constraint in enumerate(constraints, 1):
        console.print(f"  {i}. {constraint.name}")
    
    try:
        choice = IntPrompt.ask("Constraint to remove", default=0)
        if 1 <= choice <= len(constraints):
            removed = constraints.pop(choice - 1)
            console.print(f"Removed: [red]{removed.name}[/red]")
    except (ValueError, KeyboardInterrupt):
        pass


def _edit_constraint_weight_interactive(constraints: List[Constraint]) -> None:
    """Edit constraint weight interactively."""
    console.print("Select constraint to edit:")
    for i, constraint in enumerate(constraints, 1):
        console.print(f"  {i}. {constraint.name} (current weight: {constraint.weight:.2f})")
    
    try:
        choice = IntPrompt.ask("Constraint to edit", default=0)
        if 1 <= choice <= len(constraints):
            constraint = constraints[choice - 1]
            new_weight = FloatPrompt.ask(f"New weight for {constraint.name}", default=constraint.weight)
            
            if 0.0 <= new_weight <= 1.0:
                constraint.weight = new_weight
                console.print(f"Updated weight for [blue]{constraint.name}[/blue]: {new_weight:.2f}")
            else:
                console.print("Weight must be between 0.0 and 1.0")
    except (ValueError, KeyboardInterrupt):
        pass


def _interactive_weight_adjustment(session) -> Dict[str, float]:
    """Interactive constraint weight adjustment."""
    if not session.constraints:
        console.print("No constraints to adjust.")
        return {}
    
    console.print("\n⚖️  [bold]Constraint Weight Adjustment[/bold]")
    console.print("Current constraints:")
    
    for i, constraint in enumerate(session.constraints, 1):
        console.print(f"  {i}. [blue]{constraint.name}[/blue] (weight: {constraint.weight:.2f})")
    
    adjustments = {}
    
    while True:
        try:
            choice = IntPrompt.ask("Select constraint to adjust (0 to finish)", default=0)
            if choice == 0:
                break
            elif 1 <= choice <= len(session.constraints):
                constraint = session.constraints[choice - 1]
                new_weight = FloatPrompt.ask(
                    f"New weight for {constraint.name}", 
                    default=constraint.weight
                )
                
                if 0.0 <= new_weight <= 1.0:
                    adjustments[constraint.name] = new_weight
                    console.print(f"✅ Will adjust [blue]{constraint.name}[/blue] to {new_weight:.2f}")
                else:
                    console.print("Weight must be between 0.0 and 1.0")
            else:
                console.print("Invalid choice.")
        except (ValueError, KeyboardInterrupt):
            break
    
    return adjustments


def _display_session_details(session) -> None:
    """Display detailed session information."""
    console.print(f"\n📊 [bold]Session Details: {session.id}[/bold]")
    
    # Basic info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("Session ID", session.id)
    info_table.add_row("Template", session.template or "None")
    info_table.add_row("Created", session.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    info_table.add_row("Updated", session.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(info_table)
    
    # Options
    if session.options:
        console.print(f"\n🎯 [bold]Options ({len(session.options)}):[/bold]")
        options_table = Table()
        options_table.add_column("Name", style="green")
        options_table.add_column("Description", style="white")
        options_table.add_column("Attributes", style="yellow")
        
        for option in session.options:
            attr_count = len(option.attributes) if option.attributes else 0
            options_table.add_row(
                option.name,
                option.description[:50] + "..." if len(option.description) > 50 else option.description,
                f"{attr_count} attributes"
            )
        
        console.print(options_table)
    
    # Constraints
    if session.constraints:
        console.print(f"\n⚖️  [bold]Constraints ({len(session.constraints)}):[/bold]")
        constraints_table = Table()
        constraints_table.add_column("Name", style="blue")
        constraints_table.add_column("Type", style="cyan")
        constraints_table.add_column("Weight", justify="center", style="yellow")
        constraints_table.add_column("Priority", style="magenta")
        constraints_table.add_column("Description", style="white")
        
        for constraint in session.constraints:
            constraints_table.add_row(
                constraint.name,
                constraint.type.value,
                f"{constraint.weight:.2f}",
                constraint.priority.value,
                constraint.description[:40] + "..." if len(constraint.description) > 40 else constraint.description
            )
        
        console.print(constraints_table)


def _display_analysis_results(formatted_results: Any, summary: Any) -> None:
    """Display analysis results in a formatted way."""
    console.print("\n🎯 [bold green]Analysis Results[/bold green]")
    
    # Check if formatted_results has the expected structure
    if hasattr(formatted_results, 'content') and 'table_data' in formatted_results.content:
        # Rankings table from formatted results
        table_data = formatted_results.content['table_data']
        
        rankings_table = Table(title="Option Rankings")
        rankings_table.add_column("Rank", justify="center", style="cyan")
        rankings_table.add_column("Option", style="green")
        rankings_table.add_column("Score", justify="center", style="yellow")
        rankings_table.add_column("Key Differentiators", style="blue")
        
        for row in table_data:
            if hasattr(row, 'option_name'):
                differentiators = ", ".join(row.differentiators[:2]) if hasattr(row, 'differentiators') else ""
                rankings_table.add_row(
                    str(row.rank),
                    row.option_name,
                    f"{row.total_score:.3f}",
                    differentiators
                )
        
        console.print(rankings_table)
    
    # Executive summary
    if hasattr(summary, 'recommendations') and summary.recommendations:
        console.print(f"\n📋 [bold]Executive Summary[/bold]")
        
        # Show top recommendation
        top_recommendation = summary.recommendations[0]
        console.print(Panel(
            f"**{top_recommendation.option_name}** (Rank #{top_recommendation.rank})\n\n{top_recommendation.reasoning}",
            title="Top Recommendation",
            border_style="green"
        ))
        
        if hasattr(summary, 'summary_text'):
            console.print(Panel(
                summary.summary_text,
                title="Analysis Summary",
                border_style="blue"
            ))
    elif isinstance(summary, dict):
        # Fallback for dict-based summary
        if 'recommendation' in summary:
            console.print(Panel(
                summary['recommendation'],
                title="Recommendation",
                border_style="green"
            ))
        
        if 'reasoning' in summary:
            console.print(Panel(
                summary['reasoning'],
                title="Reasoning",
                border_style="blue"
            ))


def _display_impact_analysis(impact_analysis) -> None:
    """Display impact analysis results."""
    console.print("\n📈 [bold]Impact Analysis[/bold]")
    
    if hasattr(impact_analysis, 'ranking_changes') and impact_analysis.ranking_changes:
        console.print("\n🔄 [bold]Ranking Changes:[/bold]")
        for change in impact_analysis.ranking_changes:
            if change['old_rank'] != change['new_rank']:
                direction = "↑" if change['new_rank'] < change['old_rank'] else "↓"
                console.print(f"  {direction} [green]{change['option_name']}[/green]: "
                            f"#{change['old_rank']} → #{change['new_rank']}")
    
    if hasattr(impact_analysis, 'most_affected_options') and impact_analysis.most_affected_options:
        console.print("\n🎯 [bold]Most Affected Options:[/bold]")
        for option_name in impact_analysis.most_affected_options[:3]:  # Show top 3
            console.print(f"  • [yellow]{option_name}[/yellow]")


def _display_whatif_scenario(scenario) -> None:
    """Display what-if scenario results."""
    console.print(f"\n🔮 [bold]What-If Scenario: {scenario.scenario_name}[/bold]")
    
    # Show weight changes
    if hasattr(scenario, 'weight_adjustments') and scenario.weight_adjustments:
        console.print("\n⚖️  [bold]Weight Adjustments:[/bold]")
        for constraint_name, new_weight in scenario.weight_adjustments.items():
            console.print(f"  • [blue]{constraint_name}[/blue]: {new_weight:.2f}")
    
    # Show ranking comparison
    if hasattr(scenario, 'original_rankings') and hasattr(scenario, 'modified_rankings'):
        console.print("\n📊 [bold]Ranking Comparison:[/bold]")
        
        comparison_table = Table()
        comparison_table.add_column("Option", style="green")
        comparison_table.add_column("Original Rank", justify="center", style="cyan")
        comparison_table.add_column("New Rank", justify="center", style="yellow")
        comparison_table.add_column("Change", justify="center", style="white")
        
        # Create lookup for original rankings
        original_ranks = {r['option_name']: r['rank'] for r in scenario.original_rankings}
        
        for new_ranking in scenario.modified_rankings:
            option_name = new_ranking['option_name']
            original_rank = original_ranks.get(option_name, "N/A")
            new_rank = new_ranking['rank']
            
            if original_rank != "N/A":
                if new_rank < original_rank:
                    change = f"↑ +{original_rank - new_rank}"
                elif new_rank > original_rank:
                    change = f"↓ -{new_rank - original_rank}"
                else:
                    change = "="
            else:
                change = "N/A"
            
            comparison_table.add_row(
                option_name,
                str(original_rank),
                str(new_rank),
                change
            )
        
        console.print(comparison_table)


def _export_results(cli_ctx: CLIContext, session_id: str, results: Dict[str, Any], 
                   summary: Dict[str, Any], formats: List[str]) -> None:
    """Export results in specified formats."""
    try:
        console.print(f"\n📤 [bold]Exporting results in {len(formats)} format(s)...[/bold]")
        
        export_data = {
            'session_id': session_id,
            'analysis_results': results,
            'executive_summary': summary,
            'export_timestamp': datetime.now().isoformat()
        }
        
        exported_files = []
        
        for format_type in formats:
            if format_type == 'json':
                filename = f"comparison_{session_id[:8]}.json"
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                exported_files.append(filename)
            
            elif format_type == 'markdown':
                filename = f"comparison_{session_id[:8]}.md"
                _export_markdown(export_data, filename)
                exported_files.append(filename)
            
            elif format_type == 'pdf':
                console.print("⚠️  PDF export not yet implemented")
        
        if exported_files:
            console.print("✅ [bold green]Export completed:[/bold green]")
            for filename in exported_files:
                console.print(f"  📄 {filename}")
        
    except Exception as e:
        console.print(f"❌ Export error: [bold red]{str(e)}[/bold red]")


def _export_markdown(export_data: Dict[str, Any], filename: str) -> None:
    """Export results to markdown format."""
    with open(filename, 'w') as f:
        f.write(f"# Comparison Analysis Results\n\n")
        f.write(f"**Session ID:** {export_data['session_id']}\n")
        f.write(f"**Export Date:** {export_data['export_timestamp']}\n\n")
        
        # Rankings
        if 'rankings' in export_data['analysis_results']:
            f.write("## Option Rankings\n\n")
            f.write("| Rank | Option | Score | Strengths | Weaknesses |\n")
            f.write("|------|--------|-------|-----------|------------|\n")
            
            for ranking in export_data['analysis_results']['rankings']:
                strengths = ", ".join(ranking.get('strengths', []))
                weaknesses = ", ".join(ranking.get('weaknesses', []))
                f.write(f"| {ranking['rank']} | {ranking['option_name']} | "
                       f"{ranking['score']:.3f} | {strengths} | {weaknesses} |\n")
        
        # Executive Summary
        if export_data['executive_summary']:
            f.write("\n## Executive Summary\n\n")
            if 'recommendation' in export_data['executive_summary']:
                f.write(f"**Recommendation:** {export_data['executive_summary']['recommendation']}\n\n")
            if 'reasoning' in export_data['executive_summary']:
                f.write(f"**Reasoning:** {export_data['executive_summary']['reasoning']}\n\n")


if __name__ == '__main__':
    cli()