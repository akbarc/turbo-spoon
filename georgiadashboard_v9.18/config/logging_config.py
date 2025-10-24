"""
Centralized logging configuration for Georgia Dashboard v9.18
Replaces scattered print statements with proper logging
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup centralized logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)-20s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Create application logger
    app_logger = logging.getLogger('georgia_dashboard')
    
    # Log startup message
    app_logger.info("🚀 Georgia Dashboard v9.18 - Logging system initialized")
    app_logger.info(f"📊 Log level: {log_level}")
    if log_file:
        app_logger.info(f"📁 Log file: {log_file}")
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(f'georgia_dashboard.{name}')


# Pre-configured loggers for common modules
database_logger = get_logger('database')
analytics_logger = get_logger('analytics')
api_logger = get_logger('api')
ar_logger = get_logger('ar')
customer_logger = get_logger('customer')
ai_logger = get_logger('ai')


# Logging utility functions
def log_performance(logger: logging.Logger, operation: str, duration: float, details: str = ""):
    """Log performance metrics"""
    if duration > 1.0:
        logger.warning(f"⚠️ SLOW OPERATION: {operation} took {duration:.2f}s {details}")
    elif duration > 0.5:
        logger.info(f"🐌 {operation} took {duration:.2f}s {details}")
    else:
        logger.debug(f"✅ {operation} completed in {duration:.2f}s {details}")


def log_database_operation(operation: str, table: str, duration: float, row_count: int = 0):
    """Log database operations with consistent format"""
    details = f"table={table}, rows={row_count}" if row_count else f"table={table}"
    log_performance(database_logger, f"DB {operation}", duration, details)


def log_api_request(method: str, endpoint: str, duration: float, status_code: int):
    """Log API requests with consistent format"""
    if status_code >= 500:
        api_logger.error(f"❌ {method} {endpoint} -> {status_code} ({duration:.2f}s)")
    elif status_code >= 400:
        api_logger.warning(f"⚠️ {method} {endpoint} -> {status_code} ({duration:.2f}s)")
    else:
        api_logger.info(f"✅ {method} {endpoint} -> {status_code} ({duration:.2f}s)")


# Context manager for performance logging
class PerformanceLogger:
    """Context manager for logging operation performance"""
    
    def __init__(self, logger: logging.Logger, operation: str, details: str = ""):
        self.logger = logger
        self.operation = operation
        self.details = details
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"🔄 Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(f"❌ {self.operation} failed after {duration:.2f}s: {exc_val}")
        else:
            log_performance(self.logger, self.operation, duration, self.details)
