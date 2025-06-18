"""
PDF Form Enrichment Tool

A Python tool for automatically parsing PDF forms, extracting form field
metadata, generating BEM-compliant API names using AI-powered contextual
analysis, and writing changes back to the PDF while preserving document
integrity.
"""

__version__ = "1.0.0"
__author__ = "Your Company"
__email__ = "dev@yourcompany.com"
__license__ = "MIT"
__description__ = "AI-powered PDF form field enrichment with BEM naming automation"

# Package-level configuration
import logging
import os
from pathlib import Path

# Set up basic logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Package directories
PACKAGE_DIR = Path(__file__).parent
CONFIG_DIR = PACKAGE_DIR / "config"

# Create necessary directories
TEMP_DIR = Path.cwd() / "temp"
LOGS_DIR = Path.cwd() / "logs"
OUTPUT_DIR = Path.cwd() / "output"

for directory in [TEMP_DIR, LOGS_DIR, OUTPUT_DIR]:
    directory.mkdir(exist_ok=True)

# Environment-based configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if DEBUG:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
