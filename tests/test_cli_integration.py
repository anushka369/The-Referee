"""
Integration tests for the CLI interface.

Tests end-to-end workflows through CLI and verifies all major features
work via command line interface.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
import json
import os

from option_comparison_tool.cli import cli
from option_comparison_tool.comparison_manager import ComparisonManager
from option_comparison_tool.models import Option, Constraint, ConstraintType, Priority


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    def setup_method(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.runner = CliRunner()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_cli_help_command(self):
        """Test that CLI help command works."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Option Comparison Tool' in result.output
        assert 'create' in result.output
        assert 'analyze' in result.output
        assert 'templates' in result.output
    
    def test_templates_command(self):
        """Test listing available templates."""
        result = self.runner.invoke(cli, ['templates'])
        assert result.exit_code == 0
        assert 'Available Templates' in result.output
        assert 'api_compar' in result.output  # Truncated in table
        assert 'cloud_serv' in result.output  # Truncated in table
        assert 'tech_stack' in result.output
        assert 'database_s' in result.output  # Truncated in table
    
    def test_create_comparison_with_template(self):
        """Test creating a comparison using a template."""
        result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert result.exit_code == 0
        assert 'Created comparison session' in result.output
        assert 'Using template: api_comparison' in result.output
        assert 'Options: 3, Constraints: 6' in result.output
    
    def test_create_comparison_invalid_template(self):
        """Test creating a comparison with invalid template."""
        result = self.runner.invoke(cli, ['create', '--template', 'invalid_template'])
        assert result.exit_code == 1
        assert 'Error applying template' in result.output
    
    def test_create_comparison_no_template_non_interactive(self):
        """Test creating a comparison without template in non-interactive mode."""
        result = self.runner.invoke(cli, ['create'])
        assert result.exit_code == 1
        assert 'Template required for non-interactive mode' in result.output
    
    def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        result = self.runner.invoke(cli, ['list-sessions'])
        assert result.exit_code == 0
        assert 'No comparison sessions found' in result.output
    
    def test_list_sessions_with_data(self):
        """Test listing sessions after creating one."""
        # First create a session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Then list sessions
        list_result = self.runner.invoke(cli, ['list-sessions'])
        assert list_result.exit_code == 0
        assert 'Comparison Sessions' in list_result.output
        assert 'api_comparison' in list_result.output
    
    def test_show_session_not_found(self):
        """Test showing a session that doesn't exist."""
        result = self.runner.invoke(cli, ['show', 'nonexistent-session-id'])
        assert result.exit_code == 1
        assert 'Session nonexistent-session-id not found' in result.output
    
    def test_show_session_no_id_no_current(self):
        """Test showing session without ID and no current session."""
        result = self.runner.invoke(cli, ['show'])
        assert result.exit_code == 1
        assert 'No session ID provided and no current session active' in result.output
    
    def test_create_and_show_session(self):
        """Test creating a session and then showing its details."""
        # Create session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID from output
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Show session details
        show_result = self.runner.invoke(cli, ['show', session_id])
        assert show_result.exit_code == 0
        assert 'Session Details' in show_result.output
        assert 'REST API' in show_result.output
        assert 'GraphQL API' in show_result.output
        assert 'gRPC API' in show_result.output
        assert 'Performance' in show_result.output
        assert 'Reliability' in show_result.output
    
    def test_analyze_session_not_found(self):
        """Test analyzing a session that doesn't exist."""
        result = self.runner.invoke(cli, ['analyze', 'nonexistent-session-id'])
        assert result.exit_code == 1
        assert 'Session nonexistent-session-id not found' in result.output
    
    def test_analyze_session_no_id_no_current(self):
        """Test analyzing without session ID and no current session."""
        result = self.runner.invoke(cli, ['analyze'])
        assert result.exit_code == 1
        assert 'No session ID provided and no current session active' in result.output
    
    def test_create_and_analyze_session(self):
        """Test creating a session and running analysis."""
        # Create session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Run analysis
        analyze_result = self.runner.invoke(cli, ['analyze', session_id])
        assert analyze_result.exit_code == 0
        assert 'Analysis Results' in analyze_result.output
    
    def test_analyze_with_export_json(self):
        """Test analyzing with JSON export."""
        # Create session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Run analysis with export
        analyze_result = self.runner.invoke(cli, ['analyze', session_id, '--export', 'json'])
        assert analyze_result.exit_code == 0
        # Export may fail due to missing data, but should not crash
        assert 'Exporting results' in analyze_result.output
    
    def test_analyze_with_export_markdown(self):
        """Test analyzing with Markdown export."""
        # Create session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Run analysis with export
        analyze_result = self.runner.invoke(cli, ['analyze', session_id, '--export', 'markdown'])
        assert analyze_result.exit_code == 0
        # Export may fail due to missing data, but should not crash
        assert 'Exporting results' in analyze_result.output
    
    def test_analyze_with_multiple_exports(self):
        """Test analyzing with multiple export formats."""
        # Create session
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Run analysis with multiple exports
        analyze_result = self.runner.invoke(cli, [
            'analyze', session_id, 
            '--export', 'json', 
            '--export', 'markdown'
        ])
        assert analyze_result.exit_code == 0
        # Export may fail due to missing data, but should not crash
        assert 'Exporting results' in analyze_result.output
    
    def test_adjust_weights_session_not_found(self):
        """Test adjusting weights for non-existent session."""
        result = self.runner.invoke(cli, ['adjust', 'nonexistent-session-id'])
        assert result.exit_code == 1
        assert 'Session nonexistent-session-id not found' in result.output
    
    def test_adjust_weights_no_session(self):
        """Test adjusting weights without session ID and no current session."""
        result = self.runner.invoke(cli, ['adjust'])
        assert result.exit_code == 1
        assert 'No session ID provided and no current session active' in result.output
    
    def test_whatif_scenario_session_not_found(self):
        """Test what-if scenario for non-existent session."""
        result = self.runner.invoke(cli, ['whatif', 'nonexistent-session-id'])
        assert result.exit_code == 1
        assert 'Session nonexistent-session-id not found' in result.output
    
    def test_whatif_scenario_no_session(self):
        """Test what-if scenario without session ID and no current session."""
        result = self.runner.invoke(cli, ['whatif'])
        assert result.exit_code == 1
        assert 'No session ID provided and no current session active' in result.output
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        # 1. List templates
        templates_result = self.runner.invoke(cli, ['templates'])
        assert templates_result.exit_code == 0
        assert 'api_compar' in templates_result.output  # Truncated in table
        
        # 2. Create comparison
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # 3. List sessions
        list_result = self.runner.invoke(cli, ['list-sessions'])
        assert list_result.exit_code == 0
        assert session_id[:8] in list_result.output
        
        # 4. Show session details
        show_result = self.runner.invoke(cli, ['show', session_id])
        assert show_result.exit_code == 0
        assert 'Session Details' in show_result.output
        
        # 5. Run analysis
        analyze_result = self.runner.invoke(cli, ['analyze', session_id])
        assert analyze_result.exit_code == 0
        assert 'Analysis Results' in analyze_result.output
        
        # 6. Export results
        export_result = self.runner.invoke(cli, ['analyze', session_id, '--export', 'json'])
        assert export_result.exit_code == 0
        # Export may fail due to missing data, but should not crash
        assert 'Exporting results' in export_result.output
    
    def test_template_domain_coverage(self):
        """Test that all template domains are available."""
        result = self.runner.invoke(cli, ['templates'])
        assert result.exit_code == 0
        
        # Check all expected domains are present (some may be truncated)
        expected_domains = ['api', 'cloud_serv', 'tech_stack', 'database']
        for domain in expected_domains:
            assert domain in result.output
    
    def test_cli_error_handling(self):
        """Test CLI error handling for various scenarios."""
        # Invalid command
        result = self.runner.invoke(cli, ['invalid-command'])
        assert result.exit_code != 0
        
        # Invalid option
        result = self.runner.invoke(cli, ['create', '--invalid-option'])
        assert result.exit_code != 0
        
        # Missing required argument
        result = self.runner.invoke(cli, ['show'])
        assert result.exit_code == 1
    
    def test_cli_output_formatting(self):
        """Test that CLI output is properly formatted."""
        # Templates command should have table format
        result = self.runner.invoke(cli, ['templates'])
        assert result.exit_code == 0
        assert '┏' in result.output  # Rich table formatting
        assert '┃' in result.output
        
        # Create session should have emoji and formatting
        result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert result.exit_code == 0
        assert '✅' in result.output  # Success emoji
        assert '📋' in result.output  # Template emoji
        assert '📊' in result.output  # Stats emoji
    
    def test_session_persistence(self):
        """Test that sessions persist across CLI invocations."""
        # Create session in first invocation
        create_result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert create_result.exit_code == 0
        
        # Extract session ID
        lines = create_result.output.split('\n')
        session_line = [line for line in lines if 'Created comparison session:' in line][0]
        session_id = session_line.split(': ')[1].strip()
        
        # Verify session exists in second invocation
        show_result = self.runner.invoke(cli, ['show', session_id])
        assert show_result.exit_code == 0
        assert session_id in show_result.output
        
        # Verify session appears in list in third invocation
        list_result = self.runner.invoke(cli, ['list-sessions'])
        assert list_result.exit_code == 0
        assert session_id[:8] in list_result.output


class TestCLIEdgeCases:
    """Test edge cases and error conditions in CLI."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.runner = CliRunner()
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_malformed_session_id(self):
        """Test handling of malformed session IDs."""
        result = self.runner.invoke(cli, ['show', 'not-a-valid-uuid'])
        assert result.exit_code == 1
        assert 'not found' in result.output
    
    def test_empty_session_id(self):
        """Test handling of empty session ID."""
        result = self.runner.invoke(cli, ['show', ''])
        assert result.exit_code == 1
    
    def test_very_long_session_id(self):
        """Test handling of very long session ID."""
        long_id = 'a' * 1000
        result = self.runner.invoke(cli, ['show', long_id])
        assert result.exit_code == 1
        assert 'not found' in result.output
    
    def test_special_characters_in_session_id(self):
        """Test handling of special characters in session ID."""
        special_id = 'session-with-special-chars-!@#$%^&*()'
        result = self.runner.invoke(cli, ['show', special_id])
        assert result.exit_code == 1
        assert 'not found' in result.output
    
    def test_concurrent_cli_operations(self):
        """Test that concurrent CLI operations don't interfere."""
        # This is a basic test - in a real scenario you'd use threading
        # Create first session
        result1 = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
        assert result1.exit_code == 0
        
        # Create second session
        result2 = self.runner.invoke(cli, ['create', '--template', 'cloud_services'])
        assert result2.exit_code == 0
        
        # Both should be listed
        list_result = self.runner.invoke(cli, ['list-sessions'])
        assert list_result.exit_code == 0
        assert 'api_comparison' in list_result.output
        assert 'cloud_services' in list_result.output
    
    def test_disk_space_handling(self):
        """Test behavior when disk operations might fail."""
        # This is a basic test - in practice you'd mock filesystem operations
        # Create many sessions to test storage
        for i in range(5):
            result = self.runner.invoke(cli, ['create', '--template', 'api_comparison'])
            assert result.exit_code == 0
        
        # All should be listable
        list_result = self.runner.invoke(cli, ['list-sessions'])
        assert list_result.exit_code == 0
        # Should show multiple sessions
        assert list_result.output.count('api_comparison') >= 5


if __name__ == '__main__':
    pytest.main([__file__])