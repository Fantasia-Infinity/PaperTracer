#!/usr/bin/env python3
"""
PaperTracer Configuration Management
Centralized configuration for the papertracer project
"""

import os
from datetime import datetime

class Config:
    """Project configuration class"""
    
    # Output directory configuration
    OUTPUT_DIR = "output"
    
    # Crawler default configuration
    DEFAULT_MAX_DEPTH = 10
    DEFAULT_MAX_PAPERS_PER_LEVEL = 30
    DEFAULT_DELAY_RANGE = (1, 2)
    
    # File naming configuration
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    DEFAULT_FILE_PREFIX = "demo"
    
    # Visualization configuration
    DEFAULT_FIGURE_SIZE = (12, 8)
    DEFAULT_DPI = 300
    
    # Supported output formats
    SUPPORTED_IMAGE_FORMATS = ['.png', '.jpg', '.svg', '.pdf']
    SUPPORTED_DATA_FORMATS = ['.json', '.csv', '.log']
    
    @classmethod
    def get_timestamped_filename(cls, prefix=None, suffix="", extension=""):
        """Generate timestamped filename"""
        if prefix is None:
            prefix = cls.DEFAULT_FILE_PREFIX
        
        timestamp = datetime.now().strftime(cls.TIMESTAMP_FORMAT)
        
        if suffix:
            return f"{prefix}_{timestamp}_{suffix}.{extension.lstrip('.')}"
        else:
            return f"{prefix}_{timestamp}.{extension.lstrip('.')}"
    
    @classmethod
    def get_output_path(cls, filename):
        """Get full path for output file"""
        return os.path.join(cls.OUTPUT_DIR, filename)
    
    @classmethod
    def ensure_output_directory(cls):
        """Ensure output directory exists"""
        if not os.path.exists(cls.OUTPUT_DIR):
            os.makedirs(cls.OUTPUT_DIR)
            return True
        return False
    
    @classmethod
    def get_all_output_patterns(cls):
        """Get all output file patterns"""
        patterns = []
        for fmt in cls.SUPPORTED_IMAGE_FORMATS + cls.SUPPORTED_DATA_FORMATS:
            patterns.append(f"*{fmt}")
        return patterns

# Preset configurations
DEMO_CONFIG = {
    'max_depth': Config.DEFAULT_MAX_DEPTH,
    'max_papers_per_level': Config.DEFAULT_MAX_PAPERS_PER_LEVEL,
    'delay_range': Config.DEFAULT_DELAY_RANGE,
    'figsize': Config.DEFAULT_FIGURE_SIZE
}

PRODUCTION_CONFIG = {
    'max_depth': 30,
    'max_papers_per_level': 50,
    'delay_range': (2, 4),
    'figsize': (16, 12)
}

QUICK_TEST_CONFIG = {
    'max_depth': 10,
    'max_papers_per_level': 20,
    'delay_range': (0.5, 1),
    'figsize': (8, 6)
}
