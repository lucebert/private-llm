import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Union, Optional
import json
from datetime import datetime
import traceback

class LogSetupError(Exception):
    """Raised when log setup fails"""
    pass

def format_error_context(error: Exception, request_id: Optional[str] = None, **kwargs) -> str:
    """Format error context as JSON for structured logging.
    
    Args:
        error: The exception to format
        request_id: Optional request identifier for tracing
        **kwargs: Additional context to include in the output
    
    Returns:
        JSON string containing error details and context
    """
    context = {
        'error_type': error.__class__.__name__,
        'error_message': str(error),
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': request_id,
        'traceback': getattr(error, '__traceback__', None) and ''.join(traceback.format_tb(error.__traceback__)),
        **kwargs
    }
    return json.dumps({k: v for k, v in context.items() if v is not None})

def setup_logging(config: Dict[str, Union[str, bool, "development" | "production"]]) -> None:
    """Configure logging based on environment settings.
    
    Args:
        config: Dictionary containing logging configuration with keys:
            - log_level: Logging level (default: "INFO")
            - debug: Enable debug mode (default: False)
            - env: Environment name (default: "development")
    
    Raises:
        LogSetupError: If log directory creation or setup fails
    """
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
        try:
            log_path = Path("logs")
            log_path.mkdir(exist_ok=True)
        except Exception as e:
            raise LogSetupError(f"Failed to create log directory: {e}")
        
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
        try:
            # Add enhanced error logging with structured format
            error_format = (
                "<red>{time:YYYY-MM-DD HH:mm:ss}</red> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level> | "
                "Context: {extra}" | 
            )
            
            logger.add(
                log_path / "error.log",
                format=error_format,
                level="ERROR",
                rotation="100 MB",
                retention="30 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                catch=True,  # Catch any exceptions during logging
            )
        except Exception as e:
            raise LogSetupError(f"Failed to setup error logging: {e}")
        
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