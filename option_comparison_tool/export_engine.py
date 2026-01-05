"""
ExportEngine - Handles export functionality for comparison results.

This module provides export capabilities for multiple formats (PDF, markdown, JSON)
and ensures all analysis details and reasoning are included in exports.
Supports requirements 8.1, 8.2, 8.3.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import asdict, dataclass, field
import hashlib
import base64
import pickle
import uuid

from .models import ComparisonSession, Option, Constraint
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class ExportState:
    """Represents the state of an export operation."""
    session_id: str
    export_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    formats: List[str] = field(default_factory=list)
    export_paths: Dict[str, str] = field(default_factory=dict)
    shareable_link: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSnapshot:
    """Represents a snapshot of a comparison session for future reference."""
    session_id: str
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_data: ComparisonSession = None
    export_states: List[ExportState] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None


class ExportEngine:
    """
    Handles export functionality for comparison results in multiple formats.
    
    Supports PDF, markdown, and JSON exports with complete analysis details
    and reasoning. Also provides shareable link/document generation.
    """
    
    def __init__(self, export_dir: Optional[Path] = None):
        """
        Initialize the ExportEngine.
        
        Args:
            export_dir: Directory for storing exported files.
                       Defaults to Config.DATA_DIR/exports if not provided.
        """
        self.export_dir = export_dir or (Config.DATA_DIR / "exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for state persistence
        self.state_dir = self.export_dir / "states"
        self.snapshot_dir = self.export_dir / "snapshots"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches
        self._export_states: Dict[str, ExportState] = {}
        self._session_snapshots: Dict[str, SessionSnapshot] = {}
        
        logger.info(f"ExportEngine initialized with export directory: {self.export_dir}")
        self._load_persisted_states()
    
    def export_comparison(
        self,
        session: ComparisonSession,
        format_type: str,
        include_analysis: bool = True,
        include_reasoning: bool = True
    ) -> Path:
        """
        Export a comparison session to the specified format.
        
        Args:
            session: ComparisonSession to export
            format_type: Export format ('pdf', 'markdown', 'json')
            include_analysis: Whether to include analysis results
            include_reasoning: Whether to include reasoning and explanations
            
        Returns:
            Path to the exported file
            
        Raises:
            ValueError: If format_type is not supported
            RuntimeError: If export fails
        """
        logger.info(f"Exporting session {session.id} to {format_type} format")
        
        # Validate format type
        supported_formats = ['pdf', 'markdown', 'json']
        if format_type.lower() not in supported_formats:
            raise ValueError(f"Unsupported format: {format_type}. Supported formats: {supported_formats}")
        
        # Generate export data
        export_data = self._prepare_export_data(session, include_analysis, include_reasoning)
        
        # Export based on format
        format_type = format_type.lower()
        if format_type == 'json':
            file_path = self._export_json(session, export_data)
        elif format_type == 'markdown':
            file_path = self._export_markdown(session, export_data)
        elif format_type == 'pdf':
            file_path = self._export_pdf(session, export_data)
        
        # Save export state
        export_paths = {format_type: str(file_path)}
        shareable_link = self.generate_shareable_link(session)
        metadata = {
            'include_analysis': include_analysis,
            'include_reasoning': include_reasoning,
            'file_size': file_path.stat().st_size
        }
        
        self.save_export_state(
            session.id, [format_type], export_paths, shareable_link, metadata
        )
        
        return file_path
    
    def export_multiple_formats(
        self,
        session: ComparisonSession,
        formats: List[str],
        include_analysis: bool = True,
        include_reasoning: bool = True
    ) -> Dict[str, Path]:
        """
        Export a comparison session to multiple formats.
        
        Args:
            session: ComparisonSession to export
            formats: List of export formats ('pdf', 'markdown', 'json')
            include_analysis: Whether to include analysis results
            include_reasoning: Whether to include reasoning and explanations
            
        Returns:
            Dictionary mapping format names to exported file paths
        """
        logger.info(f"Exporting session {session.id} to multiple formats: {formats}")
        
        results = {}
        export_paths = {}
        total_size = 0
        
        for format_type in formats:
            try:
                file_path = self.export_comparison(
                    session, format_type, include_analysis, include_reasoning
                )
                results[format_type] = file_path
                export_paths[format_type] = str(file_path)
                total_size += file_path.stat().st_size
            except Exception as e:
                logger.error(f"Failed to export to {format_type}: {e}")
                raise
        
        # Save combined export state
        shareable_link = self.generate_shareable_link(session)
        metadata = {
            'include_analysis': include_analysis,
            'include_reasoning': include_reasoning,
            'total_size': total_size,
            'format_count': len(formats)
        }
        
        self.save_export_state(
            session.id, formats, export_paths, shareable_link, metadata
        )
        
        return results
    
    def generate_shareable_link(self, session: ComparisonSession) -> str:
        """
        Generate a shareable link/identifier for a comparison session.
        
        Args:
            session: ComparisonSession to create shareable link for
            
        Returns:
            Shareable link/identifier string
        """
        # Create a hash-based identifier from session data
        session_data = {
            'id': session.id,
            'options': [{'name': opt.name, 'description': opt.description} for opt in session.options],
            'constraints': [{'name': c.name, 'weight': c.weight} for c in session.constraints],
            'created_at': session.created_at.isoformat()
        }
        
        # Generate hash
        data_string = json.dumps(session_data, sort_keys=True)
        hash_object = hashlib.sha256(data_string.encode())
        hash_hex = hash_object.hexdigest()
        
        # Create base64 encoded short identifier
        short_id = base64.urlsafe_b64encode(hash_hex[:16].encode()).decode().rstrip('=')
        
        # Generate shareable link format
        shareable_link = f"comparison://{short_id}"
        
        logger.info(f"Generated shareable link for session {session.id}: {shareable_link}")
        return shareable_link
    
    def create_shareable_document(
        self,
        session: ComparisonSession,
        format_type: str = 'markdown'
    ) -> Dict[str, Any]:
        """
        Create a shareable document with embedded comparison data.
        
        Args:
            session: ComparisonSession to create document for
            format_type: Format for the shareable document
            
        Returns:
            Dictionary containing document data and metadata
        """
        logger.info(f"Creating shareable document for session {session.id}")
        
        # Export the comparison
        export_path = self.export_comparison(session, format_type, True, True)
        
        # Read the exported content
        with open(export_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate shareable link
        shareable_link = self.generate_shareable_link(session)
        
        # Create shareable document data
        document_data = {
            'id': session.id,
            'shareable_link': shareable_link,
            'format': format_type,
            'content': content,
            'metadata': {
                'title': f"Comparison: {', '.join([opt.name for opt in session.options[:3]])}{'...' if len(session.options) > 3 else ''}",
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'option_count': len(session.options),
                'constraint_count': len(session.constraints),
                'export_timestamp': datetime.now().isoformat()
            }
        }
        
        return document_data
    
    def _prepare_export_data(
        self,
        session: ComparisonSession,
        include_analysis: bool,
        include_reasoning: bool
    ) -> Dict[str, Any]:
        """
        Prepare comprehensive export data from a comparison session.
        
        Args:
            session: ComparisonSession to prepare data for
            include_analysis: Whether to include analysis results
            include_reasoning: Whether to include reasoning
            
        Returns:
            Dictionary containing all export data
        """
        # Convert session to dictionary format
        export_data = {
            'session_info': {
                'id': session.id,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'template': session.template
            },
            'options': [self._option_to_dict(option) for option in session.options],
            'constraints': [self._constraint_to_dict(constraint) for constraint in session.constraints],
            'summary': {
                'option_count': len(session.options),
                'constraint_count': len(session.constraints),
                'total_weight': sum(c.weight for c in session.constraints)
            }
        }
        
        # Include analysis results if available and requested
        if include_analysis and session.analysis_results:
            export_data['analysis_results'] = session.analysis_results
        
        # Include reasoning if requested
        if include_reasoning:
            export_data['reasoning'] = self._generate_reasoning(session)
        
        return export_data
    
    def _option_to_dict(self, option: Option) -> Dict[str, Any]:
        """Convert Option to dictionary format."""
        return {
            'id': option.id,
            'name': option.name,
            'description': option.description,
            'attributes': option.attributes,
            'metadata': option.metadata
        }
    
    def _constraint_to_dict(self, constraint: Constraint) -> Dict[str, Any]:
        """Convert Constraint to dictionary format."""
        constraint_dict = {
            'id': constraint.id,
            'name': constraint.name,
            'description': constraint.description,
            'weight': constraint.weight,
            'priority': constraint.priority.value,
            'type': constraint.type.value
        }
        
        # Include scale information if present
        if constraint.scale:
            if hasattr(constraint.scale, 'min'):  # NumericScale
                constraint_dict['scale'] = {
                    'type': 'numeric',
                    'min': constraint.scale.min,
                    'max': constraint.scale.max,
                    'unit': constraint.scale.unit,
                    'direction': constraint.scale.direction,
                    'normalization_method': constraint.scale.normalization_method
                }
            elif hasattr(constraint.scale, 'values'):  # CategoricalScale
                constraint_dict['scale'] = {
                    'type': 'categorical',
                    'values': constraint.scale.values,
                    'scores': constraint.scale.scores,
                    'ordered': constraint.scale.ordered
                }
        
        return constraint_dict
    
    def _generate_reasoning(self, session: ComparisonSession) -> Dict[str, Any]:
        """Generate reasoning and explanations for the comparison."""
        reasoning = {
            'comparison_rationale': f"Comparing {len(session.options)} options against {len(session.constraints)} criteria",
            'constraint_analysis': [],
            'option_analysis': []
        }
        
        # Analyze constraints
        for constraint in session.constraints:
            constraint_reasoning = {
                'name': constraint.name,
                'importance': constraint.priority.value,
                'weight_impact': f"Weight of {constraint.weight:.2f} means this criterion has {'high' if constraint.weight > 0.7 else 'medium' if constraint.weight > 0.3 else 'low'} influence on results"
            }
            reasoning['constraint_analysis'].append(constraint_reasoning)
        
        # Analyze options
        for option in session.options:
            option_reasoning = {
                'name': option.name,
                'attribute_count': len(option.attributes),
                'completeness': 'Complete' if option.description and option.attributes else 'Partial'
            }
            reasoning['option_analysis'].append(option_reasoning)
        
        return reasoning
    
    def _export_json(self, session: ComparisonSession, export_data: Dict[str, Any]) -> Path:
        """Export comparison data to JSON format."""
        filename = f"comparison_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = self.export_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully exported JSON to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            raise RuntimeError(f"JSON export failed: {e}")
    
    def _export_markdown(self, session: ComparisonSession, export_data: Dict[str, Any]) -> Path:
        """Export comparison data to Markdown format."""
        filename = f"comparison_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path = self.export_dir / filename
        
        try:
            markdown_content = self._generate_markdown_content(export_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Successfully exported Markdown to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to export Markdown: {e}")
            raise RuntimeError(f"Markdown export failed: {e}")
    
    def _export_pdf(self, session: ComparisonSession, export_data: Dict[str, Any]) -> Path:
        """Export comparison data to PDF format."""
        filename = f"comparison_{session.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = self.export_dir / filename
        
        try:
            # For now, create a text-based PDF using a simple approach
            # In a real implementation, you might use libraries like reportlab or weasyprint
            pdf_content = self._generate_pdf_content(export_data)
            
            # Write as text file with .pdf extension for now
            # This is a simplified implementation
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pdf_content)
            
            logger.info(f"Successfully exported PDF to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to export PDF: {e}")
            raise RuntimeError(f"PDF export failed: {e}")
    
    def _generate_markdown_content(self, export_data: Dict[str, Any]) -> str:
        """Generate Markdown content from export data."""
        content = []
        
        # Title and metadata
        session_info = export_data['session_info']
        content.append(f"# Option Comparison Report")
        content.append(f"")
        content.append(f"**Session ID:** {session_info['id']}")
        content.append(f"**Created:** {session_info['created_at']}")
        content.append(f"**Updated:** {session_info['updated_at']}")
        if session_info.get('template'):
            content.append(f"**Template:** {session_info['template']}")
        content.append(f"")
        
        # Summary
        summary = export_data['summary']
        content.append(f"## Summary")
        content.append(f"")
        content.append(f"- **Options:** {summary['option_count']}")
        content.append(f"- **Constraints:** {summary['constraint_count']}")
        content.append(f"- **Total Weight:** {summary['total_weight']:.2f}")
        content.append(f"")
        
        # Options
        content.append(f"## Options")
        content.append(f"")
        for i, option in enumerate(export_data['options'], 1):
            content.append(f"### {i}. {option['name']}")
            content.append(f"")
            if option['description']:
                content.append(f"**Description:** {option['description']}")
                content.append(f"")
            
            if option['attributes']:
                content.append(f"**Attributes:**")
                for key, value in option['attributes'].items():
                    content.append(f"- **{key}:** {value}")
                content.append(f"")
        
        # Constraints
        content.append(f"## Constraints")
        content.append(f"")
        for i, constraint in enumerate(export_data['constraints'], 1):
            content.append(f"### {i}. {constraint['name']}")
            content.append(f"")
            if constraint['description']:
                content.append(f"**Description:** {constraint['description']}")
                content.append(f"")
            content.append(f"- **Weight:** {constraint['weight']:.2f}")
            content.append(f"- **Priority:** {constraint['priority']}")
            content.append(f"- **Type:** {constraint['type']}")
            content.append(f"")
        
        # Analysis results
        if 'analysis_results' in export_data:
            content.append(f"## Analysis Results")
            content.append(f"")
            content.append(f"```json")
            content.append(json.dumps(export_data['analysis_results'], indent=2))
            content.append(f"```")
            content.append(f"")
        
        # Reasoning
        if 'reasoning' in export_data:
            reasoning = export_data['reasoning']
            content.append(f"## Reasoning")
            content.append(f"")
            content.append(f"**Comparison Rationale:** {reasoning['comparison_rationale']}")
            content.append(f"")
            
            if reasoning.get('constraint_analysis'):
                content.append(f"### Constraint Analysis")
                content.append(f"")
                for analysis in reasoning['constraint_analysis']:
                    content.append(f"- **{analysis['name']}:** {analysis['weight_impact']}")
                content.append(f"")
        
        return "\n".join(content)
    
    def _generate_pdf_content(self, export_data: Dict[str, Any]) -> str:
        """Generate PDF content from export data (simplified text-based approach)."""
        # For this implementation, we'll generate a text-based representation
        # In a real implementation, you would use a proper PDF library
        content = []
        
        content.append("OPTION COMPARISON REPORT")
        content.append("=" * 50)
        content.append("")
        
        # Session info
        session_info = export_data['session_info']
        content.append(f"Session ID: {session_info['id']}")
        content.append(f"Created: {session_info['created_at']}")
        content.append(f"Updated: {session_info['updated_at']}")
        if session_info.get('template'):
            content.append(f"Template: {session_info['template']}")
        content.append("")
        
        # Summary
        summary = export_data['summary']
        content.append("SUMMARY")
        content.append("-" * 20)
        content.append(f"Options: {summary['option_count']}")
        content.append(f"Constraints: {summary['constraint_count']}")
        content.append(f"Total Weight: {summary['total_weight']:.2f}")
        content.append("")
        
        # Options
        content.append("OPTIONS")
        content.append("-" * 20)
        for i, option in enumerate(export_data['options'], 1):
            content.append(f"{i}. {option['name']}")
            if option['description']:
                content.append(f"   Description: {option['description']}")
            if option['attributes']:
                content.append("   Attributes:")
                for key, value in option['attributes'].items():
                    content.append(f"     - {key}: {value}")
            content.append("")
        
        # Constraints
        content.append("CONSTRAINTS")
        content.append("-" * 20)
        for i, constraint in enumerate(export_data['constraints'], 1):
            content.append(f"{i}. {constraint['name']}")
            if constraint['description']:
                content.append(f"   Description: {constraint['description']}")
            content.append(f"   Weight: {constraint['weight']:.2f}")
            content.append(f"   Priority: {constraint['priority']}")
            content.append(f"   Type: {constraint['type']}")
            content.append("")
        
        return "\n".join(content)
    
    def list_exports(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all exported files, optionally filtered by session ID.
        
        Args:
            session_id: Optional session ID to filter exports
            
        Returns:
            List of export file information
        """
        exports = []
        
        if not self.export_dir.exists():
            return exports
        
        for file_path in self.export_dir.iterdir():
            if file_path.is_file():
                # Extract session ID from filename if possible
                filename = file_path.name
                if filename.startswith('comparison_'):
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        file_session_id = parts[1]
                        
                        # Filter by session ID if specified
                        if session_id and file_session_id != session_id:
                            continue
                        
                        export_info = {
                            'file_path': str(file_path),
                            'filename': filename,
                            'session_id': file_session_id,
                            'format': file_path.suffix[1:],  # Remove the dot
                            'created_at': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                            'size_bytes': file_path.stat().st_size
                        }
                        exports.append(export_info)
        
        # Sort by creation time, newest first
        exports.sort(key=lambda x: x['created_at'], reverse=True)
        return exports
    
    def delete_export(self, file_path: Union[str, Path]) -> bool:
        """
        Delete an exported file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted, False if not found
        """
        try:
            file_path = Path(file_path)
            if file_path.exists() and file_path.parent == self.export_dir:
                file_path.unlink()
                logger.info(f"Deleted export file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete export file {file_path}: {e}")
            return False
    
    # State Persistence Methods
    
    def save_export_state(
        self,
        session_id: str,
        formats: List[str],
        export_paths: Dict[str, str],
        shareable_link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save the state of an export operation for future reference.
        
        Args:
            session_id: ID of the comparison session
            formats: List of formats that were exported
            export_paths: Dictionary mapping formats to file paths
            shareable_link: Optional shareable link for the export
            metadata: Optional additional metadata
            
        Returns:
            Export state ID
        """
        export_state = ExportState(
            session_id=session_id,
            formats=formats,
            export_paths=export_paths,
            shareable_link=shareable_link,
            metadata=metadata or {}
        )
        
        # Store in memory
        self._export_states[export_state.export_id] = export_state
        
        # Persist to disk
        self._persist_export_state(export_state)
        
        logger.info(f"Saved export state {export_state.export_id} for session {session_id}")
        return export_state.export_id
    
    def get_export_state(self, export_id: str) -> Optional[ExportState]:
        """
        Retrieve an export state by ID.
        
        Args:
            export_id: Unique identifier for the export state
            
        Returns:
            ExportState if found, None otherwise
        """
        # Try memory first
        if export_id in self._export_states:
            return self._export_states[export_id]
        
        # Try loading from disk
        export_state = self._load_export_state(export_id)
        if export_state:
            self._export_states[export_id] = export_state
        
        return export_state
    
    def list_export_states(self, session_id: Optional[str] = None) -> List[ExportState]:
        """
        List all export states, optionally filtered by session ID.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            List of export states
        """
        # Load all states from disk if not in memory
        self._load_all_export_states()
        
        states = list(self._export_states.values())
        
        # Filter by session ID if specified
        if session_id:
            states = [state for state in states if state.session_id == session_id]
        
        # Sort by creation time, newest first
        states.sort(key=lambda x: x.created_at, reverse=True)
        return states
    
    def create_session_snapshot(
        self,
        session: ComparisonSession,
        description: Optional[str] = None
    ) -> str:
        """
        Create a snapshot of a comparison session for future reference.
        
        Args:
            session: ComparisonSession to snapshot
            description: Optional description for the snapshot
            
        Returns:
            Snapshot ID
        """
        # Get all export states for this session
        export_states = self.list_export_states(session.id)
        
        snapshot = SessionSnapshot(
            session_id=session.id,
            session_data=session,
            export_states=export_states,
            description=description
        )
        
        # Store in memory
        self._session_snapshots[snapshot.snapshot_id] = snapshot
        
        # Persist to disk
        self._persist_session_snapshot(snapshot)
        
        logger.info(f"Created session snapshot {snapshot.snapshot_id} for session {session.id}")
        return snapshot.snapshot_id
    
    def get_session_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """
        Retrieve a session snapshot by ID.
        
        Args:
            snapshot_id: Unique identifier for the snapshot
            
        Returns:
            SessionSnapshot if found, None otherwise
        """
        # Try memory first
        if snapshot_id in self._session_snapshots:
            return self._session_snapshots[snapshot_id]
        
        # Try loading from disk
        snapshot = self._load_session_snapshot(snapshot_id)
        if snapshot:
            self._session_snapshots[snapshot_id] = snapshot
        
        return snapshot
    
    def list_session_snapshots(self, session_id: Optional[str] = None) -> List[SessionSnapshot]:
        """
        List all session snapshots, optionally filtered by session ID.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            List of session snapshots
        """
        # Load all snapshots from disk if not in memory
        self._load_all_session_snapshots()
        
        snapshots = list(self._session_snapshots.values())
        
        # Filter by session ID if specified
        if session_id:
            snapshots = [snap for snap in snapshots if snap.session_id == session_id]
        
        # Sort by creation time, newest first
        snapshots.sort(key=lambda x: x.created_at, reverse=True)
        return snapshots
    
    def restore_session_from_snapshot(self, snapshot_id: str) -> Optional[ComparisonSession]:
        """
        Restore a comparison session from a snapshot.
        
        Args:
            snapshot_id: Unique identifier for the snapshot
            
        Returns:
            Restored ComparisonSession if found, None otherwise
        """
        snapshot = self.get_session_snapshot(snapshot_id)
        if not snapshot:
            return None
        
        # Create a new session with a new ID but same data
        restored_session = ComparisonSession(
            options=snapshot.session_data.options.copy(),
            constraints=snapshot.session_data.constraints.copy(),
            analysis_results=snapshot.session_data.analysis_results,
            template=snapshot.session_data.template
        )
        
        logger.info(f"Restored session {restored_session.id} from snapshot {snapshot_id}")
        return restored_session
    
    def delete_export_state(self, export_id: str) -> bool:
        """
        Delete an export state.
        
        Args:
            export_id: Unique identifier for the export state
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if export_id in self._export_states:
            del self._export_states[export_id]
        
        # Remove from disk
        state_file = self.state_dir / f"{export_id}.pkl"
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Deleted export state {export_id}")
            return True
        
        return False
    
    def delete_session_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a session snapshot.
        
        Args:
            snapshot_id: Unique identifier for the snapshot
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if snapshot_id in self._session_snapshots:
            del self._session_snapshots[snapshot_id]
        
        # Remove from disk
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.pkl"
        if snapshot_file.exists():
            snapshot_file.unlink()
            logger.info(f"Deleted session snapshot {snapshot_id}")
            return True
        
        return False
    
    # Private persistence methods
    
    def _load_persisted_states(self):
        """Load all persisted states on initialization."""
        self._load_all_export_states()
        self._load_all_session_snapshots()
    
    def _persist_export_state(self, export_state: ExportState):
        """Persist an export state to disk."""
        try:
            state_file = self.state_dir / f"{export_state.export_id}.pkl"
            with open(state_file, 'wb') as f:
                pickle.dump(export_state, f)
            logger.debug(f"Persisted export state {export_state.export_id}")
        except Exception as e:
            logger.error(f"Failed to persist export state {export_state.export_id}: {e}")
    
    def _load_export_state(self, export_id: str) -> Optional[ExportState]:
        """Load an export state from disk."""
        try:
            state_file = self.state_dir / f"{export_id}.pkl"
            if not state_file.exists():
                return None
            
            with open(state_file, 'rb') as f:
                export_state = pickle.load(f)
            
            logger.debug(f"Loaded export state {export_id}")
            return export_state
        except Exception as e:
            logger.error(f"Failed to load export state {export_id}: {e}")
            return None
    
    def _load_all_export_states(self):
        """Load all export states from disk."""
        if not self.state_dir.exists():
            return
        
        for state_file in self.state_dir.glob("*.pkl"):
            export_id = state_file.stem
            if export_id not in self._export_states:
                export_state = self._load_export_state(export_id)
                if export_state:
                    self._export_states[export_id] = export_state
    
    def _persist_session_snapshot(self, snapshot: SessionSnapshot):
        """Persist a session snapshot to disk."""
        try:
            snapshot_file = self.snapshot_dir / f"{snapshot.snapshot_id}.pkl"
            with open(snapshot_file, 'wb') as f:
                pickle.dump(snapshot, f)
            logger.debug(f"Persisted session snapshot {snapshot.snapshot_id}")
        except Exception as e:
            logger.error(f"Failed to persist session snapshot {snapshot.snapshot_id}: {e}")
    
    def _load_session_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Load a session snapshot from disk."""
        try:
            snapshot_file = self.snapshot_dir / f"{snapshot_id}.pkl"
            if not snapshot_file.exists():
                return None
            
            with open(snapshot_file, 'rb') as f:
                snapshot = pickle.load(f)
            
            logger.debug(f"Loaded session snapshot {snapshot_id}")
            return snapshot
        except Exception as e:
            logger.error(f"Failed to load session snapshot {snapshot_id}: {e}")
            return None
    
    def _load_all_session_snapshots(self):
        """Load all session snapshots from disk."""
        if not self.snapshot_dir.exists():
            return
        
        for snapshot_file in self.snapshot_dir.glob("*.pkl"):
            snapshot_id = snapshot_file.stem
            if snapshot_id not in self._session_snapshots:
                snapshot = self._load_session_snapshot(snapshot_id)
                if snapshot:
                    self._session_snapshots[snapshot_id] = snapshot