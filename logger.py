import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Union

def setup_logging(config: Dict[str, Union[str, bool]]) -> None:
    """Configure logging based on environment settings"""
    log_level = config.get("log_level", "INFO")
    debug = config.get("debug", False)
    env = config.get("env", "development")
    
    # Remove default handler
    logger.remove()
    
    # Configure format based on environment
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    if env == "development":
        # Development: Log to console with debug info if enabled
        logger.add(
            sys.stderr,
            format=log_format,
            level="DEBUG" if debug else log_level,
            backtrace=True,
            diagnose=True,
        )
        
    else:
        # Production: Log to file with rotation
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        logger.add(
            log_path / "app.log",
            format=log_format,
            level=log_level,
            rotation="500 MB",
            retention="10 days",
            compression="zip",
            backtrace=False,
            diagnose=False,
        )
        
        # Add separate error log file
        logger.add(
            log_path / "error.log",
            format=log_format,
            level="ERROR",
            rotation="100 MB",
            retention="30 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )
        
        if debug:
            # Add debug log file if debug is enabled in production
            logger.add(
                log_path / "debug.log",
                format=log_format,
                level="DEBUG",
                rotation="1 GB",
                retention="3 days",
                compression="zip",
            )