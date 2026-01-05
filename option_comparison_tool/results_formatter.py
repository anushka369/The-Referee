"""
ResultsFormatter - Formats comparison results in multiple output formats.

This module provides structured presentation of comparison results including
table format, pros/cons lists, summary cards, and differentiator highlighting.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import Option, Constraint, ConstraintType, Priority
from .weighted_scoring import OptionScore, ScoringResult
from .tradeoff_analyzer import TradeoffResult, OptionTradeoff

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats for results presentation."""
    TABLE = "table"
    PROS_CONS = "pros_cons"
    SUMMARY_CARDS = "summary_cards"
    DETAILED_REPORT = "detailed_report"


@dataclass
class FormattedResult:
    """Container for formatted comparison results."""
    format_type: OutputFormat
    content: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class TableRow:
    """Represents a row in the comparison table."""
    option_name: str
    rank: int
    total_score: float
    constraint_values: Dict[str, Any]
    differentiators: List[str]


@dataclass
class ProsCons:
    """Represents pros and cons for an option organized by categories."""
    option_name: str
    rank: int
    pros_by_category: Dict[str, List[str]]
    cons_by_category: Dict[str, List[str]]
    overall_summary: str


@dataclass
class SummaryCard:
    """Represents a summary card for an option."""
    option_name: str
    rank: int
    total_score: float
    key_strengths: List[str]
    key_weaknesses: List[str]
    best_for: str
    tradeoff_summary: str


class ResultsFormatter:
    """
    Formats comparison results in multiple output formats with differentiator highlighting.
    
    This formatter supports table format, pros/cons lists, summary cards, and provides
    categorical organization for pros/cons according to requirements 4.1, 4.2, 4.3.
    """
    
    def __init__(self):
        """Initialize the results formatter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def format_results(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint],
        format_type: OutputFormat
    ) -> FormattedResult:
        """
        Format comparison results in the specified format.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints used in comparison
            format_type: Desired output format
            
        Returns:
            FormattedResult containing formatted output
            
        Raises:
            ValueError: If inputs are invalid or formatting fails
        """
        self.logger.info(f"Formatting results in {format_type.value} format")
        
        # Validate inputs
        self._validate_inputs(scoring_result, tradeoff_result, constraints)
        
        # Format based on requested type
        if format_type == OutputFormat.TABLE:
            content = self._format_table(scoring_result, tradeoff_result, constraints)
        elif format_type == OutputFormat.PROS_CONS:
            content = self._format_pros_cons(scoring_result, tradeoff_result, constraints)
        elif format_type == OutputFormat.SUMMARY_CARDS:
            content = self._format_summary_cards(scoring_result, tradeoff_result, constraints)
        elif format_type == OutputFormat.DETAILED_REPORT:
            content = self._format_detailed_report(scoring_result, tradeoff_result, constraints)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
        
        # Create metadata
        metadata = self._create_format_metadata(scoring_result, tradeoff_result, constraints, format_type)
        
        result = FormattedResult(
            format_type=format_type,
            content=content,
            metadata=metadata
        )
        
        self.logger.info(f"Successfully formatted results in {format_type.value} format")
        return result
    
    def identify_differentiators(
        self,
        scoring_result: ScoringResult,
        constraints: List[Constraint],
        threshold: float = 0.3
    ) -> Dict[str, List[str]]:
        """
        Identify key differentiators between options.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            constraints: List of constraints used in comparison
            threshold: Minimum score difference to be considered a differentiator
            
        Returns:
            Dictionary mapping option names to their key differentiators
        """
        differentiators = {}
        
        if len(scoring_result.option_scores) < 2:
            return differentiators
        
        # Calculate average scores for each constraint across all options
        constraint_averages = {}
        for constraint in constraints:
            scores = [
                option_score.normalized_scores.get(constraint.name, 0.0)
                for option_score in scoring_result.option_scores
            ]
            constraint_averages[constraint.name] = sum(scores) / len(scores) if scores else 0.0
        
        # Identify differentiators for each option
        for option_score in scoring_result.option_scores:
            option_differentiators = []
            
            for constraint in constraints:
                option_constraint_score = option_score.normalized_scores.get(constraint.name, 0.0)
                average_score = constraint_averages[constraint.name]
                
                # Check if this constraint is a significant differentiator
                if abs(option_constraint_score - average_score) >= threshold:
                    direction = "strength" if option_constraint_score > average_score else "weakness"
                    differentiator = f"{constraint.name} ({direction})"
                    option_differentiators.append(differentiator)
            
            differentiators[option_score.option_name] = option_differentiators
        
        return differentiators
    
    def organize_by_categories(
        self,
        items: List[str],
        constraints: List[Constraint]
    ) -> Dict[str, List[str]]:
        """
        Organize pros/cons items by constraint categories.
        
        Args:
            items: List of constraint names or items to categorize
            constraints: List of constraints with priority information
            
        Returns:
            Dictionary mapping categories to lists of items
        """
        categories = {
            "Required": [],
            "Preferred": [],
            "Nice-to-Have": [],
            "Other": []
        }
        
        # Create constraint lookup by name
        constraint_lookup = {c.name: c for c in constraints}
        
        for item in items:
            # Extract constraint name from item (remove direction indicators)
            constraint_name = item.replace(" (strength)", "").replace(" (weakness)", "")
            
            constraint = constraint_lookup.get(constraint_name)
            if constraint:
                if constraint.priority == Priority.REQUIRED:
                    categories["Required"].append(item)
                elif constraint.priority == Priority.PREFERRED:
                    categories["Preferred"].append(item)
                elif constraint.priority == Priority.NICE_TO_HAVE:
                    categories["Nice-to-Have"].append(item)
                else:
                    categories["Other"].append(item)
            else:
                categories["Other"].append(item)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _validate_inputs(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> None:
        """
        Validate inputs for results formatting.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Raises:
            ValueError: If validation fails
        """
        if not scoring_result or not scoring_result.option_scores:
            raise ValueError("Scoring result is required and must contain option scores")
        
        if not tradeoff_result:
            raise ValueError("Trade-off result is required")
        
        # Constraints can be empty, but if provided should be valid
        for constraint in constraints:
            if not constraint.name:
                raise ValueError("All constraints must have names")
    
    def _format_table(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        Format results as a comparison table.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            Dictionary containing table data
        """
        # Identify differentiators for highlighting
        differentiators = self.identify_differentiators(scoring_result, constraints)
        
        # Create table rows
        table_rows = []
        for option_score in scoring_result.option_scores:
            # Get constraint values for this option
            constraint_values = {}
            for constraint in constraints:
                raw_score = option_score.normalized_scores.get(constraint.name, 0.0)
                weighted_score = option_score.constraint_scores.get(constraint.name, 0.0)
                constraint_values[constraint.name] = {
                    "raw_score": round(raw_score, 3),
                    "weighted_score": round(weighted_score, 3),
                    "weight": constraint.weight
                }
            
            row = TableRow(
                option_name=option_score.option_name,
                rank=option_score.rank,
                total_score=round(option_score.total_score, 3),
                constraint_values=constraint_values,
                differentiators=differentiators.get(option_score.option_name, [])
            )
            table_rows.append(row)
        
        # Create table headers
        headers = ["Rank", "Option", "Total Score"]
        headers.extend([c.name for c in constraints])
        headers.append("Key Differentiators")
        
        return {
            "headers": headers,
            "rows": [self._table_row_to_dict(row) for row in table_rows],
            "total_weight": scoring_result.total_weight,
            "constraint_info": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "priority": c.priority.value,
                    "type": c.type.value
                }
                for c in constraints
            ]
        }
    
    def _format_pros_cons(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        Format results as pros/cons lists organized by categories.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            Dictionary containing pros/cons data
        """
        pros_cons_list = []
        
        # Get differentiators for all options
        differentiators = self.identify_differentiators(scoring_result, constraints)
        
        # Create pros/cons for each option
        for option_score in scoring_result.option_scores:
            # Find corresponding trade-off analysis
            option_tradeoff = next(
                (ot for ot in tradeoff_result.option_tradeoffs if ot.option_id == option_score.option_id),
                None
            )
            
            # Identify pros (strengths) and cons (weaknesses)
            pros = []
            cons = []
            
            if option_tradeoff:
                pros.extend(option_tradeoff.strengths)
                cons.extend(option_tradeoff.weaknesses)
            
            # Add differentiators as pros/cons
            option_differentiators = differentiators.get(option_score.option_name, [])
            for diff in option_differentiators:
                if "(strength)" in diff:
                    pros.append(diff.replace(" (strength)", ""))
                elif "(weakness)" in diff:
                    cons.append(diff.replace(" (weakness)", ""))
            
            # Organize by categories
            pros_by_category = self.organize_by_categories(pros, constraints)
            cons_by_category = self.organize_by_categories(cons, constraints)
            
            # Create overall summary
            summary = self._create_option_summary(option_score, option_tradeoff, pros, cons)
            
            pros_cons = ProsCons(
                option_name=option_score.option_name,
                rank=option_score.rank,
                pros_by_category=pros_by_category,
                cons_by_category=cons_by_category,
                overall_summary=summary
            )
            pros_cons_list.append(pros_cons)
        
        return {
            "options": [self._pros_cons_to_dict(pc) for pc in pros_cons_list],
            "category_legend": {
                "Required": "Must-have criteria that are essential",
                "Preferred": "Important criteria that significantly impact the decision",
                "Nice-to-Have": "Desirable criteria that provide additional value",
                "Other": "Additional factors not categorized above"
            }
        }
    
    def _format_summary_cards(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        Format results as summary cards for each option.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            Dictionary containing summary card data
        """
        summary_cards = []
        
        for option_score in scoring_result.option_scores:
            # Find corresponding trade-off analysis
            option_tradeoff = next(
                (ot for ot in tradeoff_result.option_tradeoffs if ot.option_id == option_score.option_id),
                None
            )
            
            # Get top strengths and weaknesses (limit to 3 each)
            key_strengths = (option_tradeoff.strengths[:3] if option_tradeoff else [])
            key_weaknesses = (option_tradeoff.weaknesses[:3] if option_tradeoff else [])
            
            # Determine what this option is best for
            best_for = self._determine_best_for(option_score, constraints)
            
            # Get trade-off summary
            tradeoff_summary = (option_tradeoff.tradeoff_summary if option_tradeoff 
                              else "No significant trade-offs identified")
            
            card = SummaryCard(
                option_name=option_score.option_name,
                rank=option_score.rank,
                total_score=round(option_score.total_score, 3),
                key_strengths=key_strengths,
                key_weaknesses=key_weaknesses,
                best_for=best_for,
                tradeoff_summary=tradeoff_summary
            )
            summary_cards.append(card)
        
        return {
            "cards": [self._summary_card_to_dict(card) for card in summary_cards],
            "ranking_explanation": "Options are ranked by weighted total score across all criteria"
        }
    
    def _format_detailed_report(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint]
    ) -> Dict[str, Any]:
        """
        Format results as a comprehensive detailed report.
        
        Args:
            scoring_result: Results from weighted scoring analysis
            tradeoff_result: Results from trade-off analysis
            constraints: List of constraints
            
        Returns:
            Dictionary containing detailed report data
        """
        # Get all other formats
        table_data = self._format_table(scoring_result, tradeoff_result, constraints)
        pros_cons_data = self._format_pros_cons(scoring_result, tradeoff_result, constraints)
        cards_data = self._format_summary_cards(scoring_result, tradeoff_result, constraints)
        
        return {
            "executive_summary": {
                "top_option": scoring_result.option_scores[0].option_name,
                "total_options": len(scoring_result.option_scores),
                "total_constraints": len(constraints),
                "pareto_frontier_size": len(tradeoff_result.pareto_frontier),
                "global_tradeoffs": len(tradeoff_result.global_tradeoffs)
            },
            "table_view": table_data,
            "pros_cons_view": pros_cons_data,
            "summary_cards": cards_data,
            "trade_off_analysis": {
                "global_tradeoffs": [
                    {
                        "constraint_a": gt.constraint_a,
                        "constraint_b": gt.constraint_b,
                        "correlation": round(gt.correlation, 3),
                        "description": gt.description,
                        "affected_options": gt.affected_options
                    }
                    for gt in tradeoff_result.global_tradeoffs
                ],
                "pareto_frontier": tradeoff_result.pareto_frontier
            }
        }
    
    def _create_option_summary(
        self,
        option_score: OptionScore,
        option_tradeoff: Optional[OptionTradeoff],
        pros: List[str],
        cons: List[str]
    ) -> str:
        """Create an overall summary for an option."""
        summary_parts = []
        
        # Rank and score
        summary_parts.append(f"Ranked #{option_score.rank} with a total score of {option_score.total_score:.2f}")
        
        # Strengths
        if pros:
            summary_parts.append(f"Strong in: {', '.join(pros[:3])}")
        
        # Weaknesses
        if cons:
            summary_parts.append(f"Weak in: {', '.join(cons[:3])}")
        
        # Trade-off insight
        if option_tradeoff and option_tradeoff.competing_factors:
            summary_parts.append(f"Affected by {len(option_tradeoff.competing_factors)} trade-off(s)")
        
        return ". ".join(summary_parts) + "."
    
    def _determine_best_for(self, option_score: OptionScore, constraints: List[Constraint]) -> str:
        """Determine what scenario this option is best suited for."""
        if not constraints:
            return "General use cases"
        
        # Find the constraint where this option scores highest
        best_constraint = None
        best_score = -1
        
        for constraint in constraints:
            score = option_score.normalized_scores.get(constraint.name, 0.0)
            if score > best_score:
                best_score = score
                best_constraint = constraint
        
        if best_constraint and best_score > 0.7:
            return f"Scenarios prioritizing {best_constraint.name.lower()}"
        else:
            return "Balanced requirements"
    
    def _table_row_to_dict(self, row: TableRow) -> Dict[str, Any]:
        """Convert TableRow to dictionary."""
        return {
            "option_name": row.option_name,
            "rank": row.rank,
            "total_score": row.total_score,
            "constraint_values": row.constraint_values,
            "differentiators": row.differentiators
        }
    
    def _pros_cons_to_dict(self, pros_cons: ProsCons) -> Dict[str, Any]:
        """Convert ProsCons to dictionary."""
        return {
            "option_name": pros_cons.option_name,
            "rank": pros_cons.rank,
            "pros_by_category": pros_cons.pros_by_category,
            "cons_by_category": pros_cons.cons_by_category,
            "overall_summary": pros_cons.overall_summary
        }
    
    def _summary_card_to_dict(self, card: SummaryCard) -> Dict[str, Any]:
        """Convert SummaryCard to dictionary."""
        return {
            "option_name": card.option_name,
            "rank": card.rank,
            "total_score": card.total_score,
            "key_strengths": card.key_strengths,
            "key_weaknesses": card.key_weaknesses,
            "best_for": card.best_for,
            "tradeoff_summary": card.tradeoff_summary
        }
    
    def _create_format_metadata(
        self,
        scoring_result: ScoringResult,
        tradeoff_result: TradeoffResult,
        constraints: List[Constraint],
        format_type: OutputFormat
    ) -> Dict[str, Any]:
        """Create metadata about the formatting operation."""
        return {
            "format_type": format_type.value,
            "option_count": len(scoring_result.option_scores),
            "constraint_count": len(constraints),
            "total_weight": scoring_result.total_weight,
            "has_tradeoffs": len(tradeoff_result.global_tradeoffs) > 0,
            "pareto_frontier_size": len(tradeoff_result.pareto_frontier),
            "differentiator_threshold": 0.3,
            "categories_used": ["Required", "Preferred", "Nice-to-Have", "Other"]
        }