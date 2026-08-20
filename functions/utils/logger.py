"""
Centralized Logging Configuration
==================================
Provides consistent logging setup across all modules.

All logs are automatically sent to Google Cloud Logging and viewable in:
- Firebase Console → Functions → Logs
- Google Cloud Console → Logging → Logs Explorer

Log Levels:
- DEBUG: Detailed information for debugging (development only)
- INFO: General informational messages (normal operations)
- WARNING: Warning messages (unusual but handled situations)
- ERROR: Error messages (failures that need attention)
- CRITICAL: Critical errors (system-threatening issues)

Usage:
    from utils.logger import setup_logger
    
    logger = setup_logger(__name__)
    logger.info("Server started successfully")
    logger.warning("High memory usage detected")
    logger.error("Failed to connect to database")
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Setup and return a configured logger.
    
    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom format string (uses default if None)
        
    Returns:
        Configured Logger instance
        
    Examples:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
        
        >>> logger = setup_logger(__name__, level=logging.DEBUG)
        >>> logger.debug("Detailed debug information")
        
        >>> logger = setup_logger('custom_logger', level=logging.WARNING)
        >>> logger.warning("This is a warning")
    """
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Default format if none provided
    if log_format is None:
        log_format = (
            '%(asctime)s - '
            '%(name)s - '
            '%(levelname)s - '
            '%(funcName)s:%(lineno)d - '
            '%(message)s'
        )
    
    # Create formatter
    formatter = logging.Formatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def setup_logger_simple(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup logger with simplified format (no function/line numbers).
    
    Useful for general application logging where you don't need debug details.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured Logger instance
        
    Example:
        >>> logger = setup_logger_simple(__name__)
        >>> logger.info("Simple log message")
    """
    simple_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    return setup_logger(name, level, simple_format)


def setup_logger_json(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Setup logger with JSON-structured output.
    
    Useful for log aggregation systems that parse JSON logs.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Configured Logger instance
        
    Note:
        Requires 'python-json-logger' package for production use.
        This is a simplified version for basic JSON output.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Simple JSON-like format
    json_format = (
        '{"time": "%(asctime)s", '
        '"name": "%(name)s", '
        '"level": "%(levelname)s", '
        '"message": "%(message)s"}'
    )
    
    formatter = logging.Formatter(json_format, datefmt='%Y-%m-%dT%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def log_function_call(logger: logging.Logger):
    """
    Decorator to log function calls with arguments.
    
    Useful for debugging and tracking function execution.
    
    Args:
        logger: Logger instance to use
        
    Usage:
        logger = setup_logger(__name__)
        
        @log_function_call(logger)
        def process_data(data, mode='default'):
            return f"Processed {data}"
        
        # Logs: "Calling process_data with args=(data,) kwargs={'mode': 'default'}"
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(
                f"Calling {func.__name__} with args={args} kwargs={kwargs}"
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"{func.__name__} failed with error: {str(e)}",
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger):
    """
    Decorator to log function execution time.
    
    Useful for performance monitoring.
    
    Args:
        logger: Logger instance to use
        
    Usage:
        logger = setup_logger(__name__)
        
        @log_execution_time(logger)
        def slow_function():
            time.sleep(2)
            return "Done"
        
        # Logs: "slow_function executed in 2.001 seconds"
    """
    def decorator(func):
        from functools import wraps
        import time
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            
            logger.info(
                f"{func.__name__} executed in {execution_time:.3f} seconds"
            )
            return result
        
        return wrapper
    return decorator


def get_logger_level_from_string(level_str: str) -> int:
    """
    Convert string log level to logging constant.
    
    Args:
        level_str: Log level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        
    Returns:
        Logging level constant
        
    Examples:
        >>> get_logger_level_from_string('DEBUG')
        10
        >>> get_logger_level_from_string('info')
        20
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    level_str = level_str.upper()
    return level_map.get(level_str, logging.INFO)


def configure_root_logger(level: int = logging.INFO):
    """
    Configure the root logger for the entire application.
    
    Call this once at application startup to set global logging level.
    
    Args:
        level: Logging level for root logger
        
    Usage:
        # In main.py at startup
        from utils.logger import configure_root_logger
        configure_root_logger(logging.INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )


class StructuredLogger:
    """
    Logger wrapper for structured logging with context.
    
    Adds consistent contextual information to all log messages.
    
    Usage:
        logger = StructuredLogger('api', {'service': 'cropverse', 'version': '1.0'})
        logger.info('Request received', {'user_id': '123', 'endpoint': '/api/data'})
        
        # Output: 2025-01-15 10:30:00 - api - INFO - Request received 
        #         Context: {'service': 'cropverse', 'version': '1.0', 'user_id': '123', 'endpoint': '/api/data'}
    """
    
    def __init__(self, name: str, context: dict = None):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
            context: Default context to include in all logs
        """
        self.logger = setup_logger(name)
        self.context = context or {}
    
    def _format_message(self, message: str, extra_context: dict = None) -> str:
        """Format message with context"""
        full_context = {**self.context, **(extra_context or {})}
        if full_context:
            return f"{message} | Context: {full_context}"
        return message
    
    def debug(self, message: str, context: dict = None):
        """Log debug message with context"""
        self.logger.debug(self._format_message(message, context))
    
    def info(self, message: str, context: dict = None):
        """Log info message with context"""
        self.logger.info(self._format_message(message, context))
    
    def warning(self, message: str, context: dict = None):
        """Log warning message with context"""
        self.logger.warning(self._format_message(message, context))
    
    def error(self, message: str, context: dict = None, exc_info: bool = False):
        """Log error message with context"""
        self.logger.error(self._format_message(message, context), exc_info=exc_info)
    
    def critical(self, message: str, context: dict = None, exc_info: bool = False):
        """Log critical message with context"""
        self.logger.critical(self._format_message(message, context), exc_info=exc_info)


# Convenience function to get common loggers
def get_api_logger() -> logging.Logger:
    """Get logger for API routes"""
    return setup_logger('api', logging.INFO)


def get_service_logger(service_name: str) -> logging.Logger:
    """Get logger for a specific service"""
    return setup_logger(f'service.{service_name}', logging.INFO)


def get_model_logger(model_name: str) -> logging.Logger:
    """Get logger for a specific model"""
    return setup_logger(f'model.{model_name}', logging.INFO)


# Example usage for testing
if __name__ == '__main__':
    # Test basic logger
    logger = setup_logger(__name__)
    logger.debug("Debug message (won't show at INFO level)")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    
    # Test simple logger
    simple_logger = setup_logger_simple('simple_test')
    simple_logger.info("Simple format message")
    
    # Test structured logger
    struct_logger = StructuredLogger('test', {'app': 'cropverse'})
    struct_logger.info("Structured log", {'action': 'test', 'status': 'success'})
    
    # Test decorators
    @log_execution_time(logger)
    def test_function():
        import time
        time.sleep(0.1)
        return "Done"
    
    result = test_function()