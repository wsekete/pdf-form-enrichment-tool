"""Logging utilities."""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Set up logging configuration."""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "pdf_form_editor.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger("pdf_form_editor")
    logger.info(f"Logging initialized at {level} level")

    return logger
