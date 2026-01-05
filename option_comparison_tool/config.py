"""
Configuration settings for the Option Comparison Tool.
"""

import logging
import os
from pathlib import Path


class Config:
    """Application configuration settings."""
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Application settings
    MAX_OPTIONS_PER_COMPARISON = 10
    MIN_OPTIONS_PER_COMPARISON = 2
    DEFAULT_CONSTRAINT_WEIGHT = 1.0
    
    # Data persistence
    DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
    
    # Analysis settings
    DEFAULT_ANALYSIS_METHOD = "weighted_scoring"
    PROPERTY_TEST_ITERATIONS = 100


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("option_comparison_tool.log")
        ]
    )
    
    # Create logger for the application
    logger = logging.getLogger("option_comparison_tool")
    return logger


# Initialize logging when module is imported
logger = setup_logging()