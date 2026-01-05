"""
Unit tests for export state persistence functionality.

Tests the state persistence system for export operations and session snapshots.
Validates: Requirements 8.4
"""

import tempfile
from pathlib import Path
from option_comparison_tool.export_engine import ExportEngine
from option_comparison_tool.models import ComparisonSession, Option, Constraint, ConstraintType, Priority


class TestExportStatePersistence:
    """Test export state persistence functionality."""

    def test_export_state_save_and_retrieve(self):
        """Test saving and retrieving export states."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create a test session
            session = ComparisonSession(
                options=[
                    Option(name="Option1", description="Test option 1"),
                    Option(name="Option2", description="Test option 2")
                ],
                constraints=[
                    Constraint(name="Cost", weight=0.5, priority=Priority.REQUIRED, type=ConstraintType.NUMERIC)
                ]
            )
            
            # Save export state
            export_paths = {"json": "/path/to/export.json"}
            formats = ["json"]
            shareable_link = "comparison://test123"
            metadata = {"test": "data"}
            
            export_id = export_engine.save_export_state(
                session.id, formats, export_paths, shareable_link, metadata
            )
            
            # Retrieve export state
            retrieved_state = export_engine.get_export_state(export_id)
            
            assert retrieved_state is not None
            assert retrieved_state.session_id == session.id
            assert retrieved_state.formats == formats
            assert retrieved_state.export_paths == export_paths
            assert retrieved_state.shareable_link == shareable_link
            assert retrieved_state.metadata == metadata

    def test_session_snapshot_creation_and_restoration(self):
        """Test creating and restoring session snapshots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create a test session
            session = ComparisonSession(
                options=[
                    Option(name="Option1", description="Test option 1", attributes={"cost": 100}),
                    Option(name="Option2", description="Test option 2", attributes={"cost": 200})
                ],
                constraints=[
                    Constraint(name="Cost", weight=0.7, priority=Priority.REQUIRED, type=ConstraintType.NUMERIC),
                    Constraint(name="Quality", weight=0.3, priority=Priority.PREFERRED, type=ConstraintType.NUMERIC)
                ]
            )
            
            # Create snapshot
            description = "Test snapshot for comparison"
            snapshot_id = export_engine.create_session_snapshot(session, description)
            
            # Retrieve snapshot
            retrieved_snapshot = export_engine.get_session_snapshot(snapshot_id)
            
            assert retrieved_snapshot is not None
            assert retrieved_snapshot.session_id == session.id
            assert retrieved_snapshot.description == description
            assert len(retrieved_snapshot.session_data.options) == len(session.options)
            assert len(retrieved_snapshot.session_data.constraints) == len(session.constraints)
            
            # Restore session from snapshot
            restored_session = export_engine.restore_session_from_snapshot(snapshot_id)
            
            assert restored_session is not None
            assert restored_session.id != session.id  # Should have new ID
            assert len(restored_session.options) == len(session.options)
            assert len(restored_session.constraints) == len(session.constraints)
            assert restored_session.options[0].name == session.options[0].name
            assert restored_session.constraints[0].name == session.constraints[0].name

    def test_export_state_listing_and_filtering(self):
        """Test listing and filtering export states."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create test sessions
            session1 = ComparisonSession(
                options=[Option(name="Opt1"), Option(name="Opt2")],
                constraints=[Constraint(name="Constraint1")]
            )
            session2 = ComparisonSession(
                options=[Option(name="Opt3"), Option(name="Opt4")],
                constraints=[Constraint(name="Constraint2")]
            )
            
            # Save export states for both sessions
            export_id1 = export_engine.save_export_state(
                session1.id, ["json"], {"json": "/path1.json"}
            )
            export_id2 = export_engine.save_export_state(
                session2.id, ["markdown"], {"markdown": "/path2.md"}
            )
            export_id3 = export_engine.save_export_state(
                session1.id, ["pdf"], {"pdf": "/path3.pdf"}
            )
            
            # List all export states
            all_states = export_engine.list_export_states()
            assert len(all_states) == 3
            
            # List export states for session1 only
            session1_states = export_engine.list_export_states(session1.id)
            assert len(session1_states) == 2
            assert all(state.session_id == session1.id for state in session1_states)
            
            # List export states for session2 only
            session2_states = export_engine.list_export_states(session2.id)
            assert len(session2_states) == 1
            assert session2_states[0].session_id == session2.id

    def test_export_state_deletion(self):
        """Test deleting export states."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create test session
            session = ComparisonSession(
                options=[Option(name="Opt1"), Option(name="Opt2")],
                constraints=[Constraint(name="Constraint1")]
            )
            
            # Save export state
            export_id = export_engine.save_export_state(
                session.id, ["json"], {"json": "/path.json"}
            )
            
            # Verify state exists
            assert export_engine.get_export_state(export_id) is not None
            
            # Delete state
            deletion_result = export_engine.delete_export_state(export_id)
            assert deletion_result is True
            
            # Verify state no longer exists
            assert export_engine.get_export_state(export_id) is None

    def test_session_snapshot_deletion(self):
        """Test deleting session snapshots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create test session
            session = ComparisonSession(
                options=[Option(name="Opt1"), Option(name="Opt2")],
                constraints=[Constraint(name="Constraint1")]
            )
            
            # Create snapshot
            snapshot_id = export_engine.create_session_snapshot(session, "Test snapshot")
            
            # Verify snapshot exists
            assert export_engine.get_session_snapshot(snapshot_id) is not None
            
            # Delete snapshot
            deletion_result = export_engine.delete_session_snapshot(snapshot_id)
            assert deletion_result is True
            
            # Verify snapshot no longer exists
            assert export_engine.get_session_snapshot(snapshot_id) is None

    def test_persistence_across_engine_instances(self):
        """Test that states persist across different ExportEngine instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first engine instance
            export_engine1 = ExportEngine(Path(temp_dir))
            
            # Create test session
            session = ComparisonSession(
                options=[Option(name="Opt1"), Option(name="Opt2")],
                constraints=[Constraint(name="Constraint1")]
            )
            
            # Save export state and snapshot
            export_id = export_engine1.save_export_state(
                session.id, ["json"], {"json": "/path.json"}
            )
            snapshot_id = export_engine1.create_session_snapshot(session, "Test snapshot")
            
            # Create second engine instance (should load persisted states)
            export_engine2 = ExportEngine(Path(temp_dir))
            
            # Verify states are available in second instance
            retrieved_state = export_engine2.get_export_state(export_id)
            retrieved_snapshot = export_engine2.get_session_snapshot(snapshot_id)
            
            assert retrieved_state is not None
            assert retrieved_state.session_id == session.id
            assert retrieved_snapshot is not None
            assert retrieved_snapshot.session_id == session.id

    def test_integrated_export_with_state_persistence(self):
        """Test that actual exports automatically save state."""
        with tempfile.TemporaryDirectory() as temp_dir:
            export_engine = ExportEngine(Path(temp_dir))
            
            # Create test session
            session = ComparisonSession(
                options=[
                    Option(name="Option1", description="Test option 1"),
                    Option(name="Option2", description="Test option 2")
                ],
                constraints=[
                    Constraint(name="Cost", weight=0.5, priority=Priority.REQUIRED, type=ConstraintType.NUMERIC)
                ]
            )
            
            # Export to JSON (should automatically save state)
            exported_file = export_engine.export_comparison(session, 'json')
            
            # Verify export state was automatically saved
            export_states = export_engine.list_export_states(session.id)
            assert len(export_states) >= 1
            
            # Find the state for this export
            json_state = None
            for state in export_states:
                if 'json' in state.formats:
                    json_state = state
                    break
            
            assert json_state is not None
            assert json_state.session_id == session.id
            assert 'json' in json_state.formats
            assert str(exported_file) in json_state.export_paths.values()
            assert json_state.shareable_link is not None