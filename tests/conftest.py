"""Test configuration for the option comparison tool."""

from hypothesis import settings

# Configure Hypothesis to use fewer examples for faster test runs
settings.register_profile("fast", max_examples=20, deadline=5000)
settings.load_profile("fast")