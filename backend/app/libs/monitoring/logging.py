"""
Advanced logging system for the simulation preprocessing platform.
Implements structured logging, log aggregation, and observability features.
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading
from dataclasses import dataclass, asdict
from enum import Enum

class LogLevel(Enum):
    """Log levels with numeric values"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

@dataclass
class LogContext:
    """Structured log context"""
    workflow_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_type: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add context if available
        if self.include_context and hasattr(record, 'context'):
            log_entry["context"] = record.context.to_dict()
        
        # Add performance metrics if available
        if hasattr(record, 'performance'):
            log_entry["performance"] = record.performance
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)

class ContextualLogger:
    """Logger with contextual information"""
    
    def __init__(self, name: str, context: LogContext = None):
        self.logger = logging.getLogger(name)
        self.context = context or LogContext()
        self._local = threading.local()
    
    def with_context(self, **kwargs) -> 'ContextualLogger':
        """Create a new logger with additional context"""
        new_context = LogContext(**{**self.context.to_dict(), **kwargs})
        return ContextualLogger(self.logger.name, new_context)
    
    def _log(self, level: int, message: str, extra_fields: Dict[str, Any] = None, 
             performance: Dict[str, Any] = None, exc_info: bool = False):
        """Internal logging method with context"""
        if not self.logger.isEnabledFor(level):
            return
        
        # Create log record
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), exc_info
        )
        
        # Add context
        record.context = self.context
        
        # Add extra fields
        if extra_fields:
            record.extra_fields = extra_fields
        
        # Add performance metrics
        if performance:
            record.performance = performance
        
        # Handle the record
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, exc_info=True, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)

class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self, logger: ContextualLogger):
        self.logger = logger
    
    @contextmanager
    def time_operation(self, operation: str, **context):
        """Context manager to time operations"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            yield
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory if end_memory and start_memory else None
            
            performance_data = {
                "operation": operation,
                "duration_seconds": duration,
                "success": success,
                "memory_delta_mb": memory_delta,
                **context
            }
            
            if error:
                performance_data["error"] = error
            
            self.logger.info(
                f"Operation '{operation}' completed in {duration:.3f}s",
                performance=performance_data
            )
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return None

class LoggingConfig:
    """Configuration for logging system"""
    
    def __init__(self):
        self.log_level = LogLevel.INFO
        self.log_format = "structured"  # "structured" or "simple"
        self.log_file = None
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.backup_count = 5
        self.console_output = True
        self.include_context = True
        self.performance_logging = True
        
        # Log aggregation settings
        self.enable_syslog = False
        self.syslog_address = ('localhost', 514)
        self.enable_json_file = True
        
        # Security settings
        self.mask_sensitive_data = True
        self.sensitive_fields = ['password', 'token', 'key', 'secret', 'auth']

class LoggingManager:
    """Central logging management"""
    
    def __init__(self, config: LoggingConfig = None):
        self.config = config or LoggingConfig()
        self.loggers: Dict[str, ContextualLogger] = {}
        self.handlers: List[logging.Handler] = []
        self.initialized = False
    
    def initialize(self, log_dir: str = "logs"):
        """Initialize logging system"""
        if self.initialized:
            return
        
        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.config.log_level.value)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.config.log_level.value)
            
            if self.config.log_format == "structured":
                console_handler.setFormatter(StructuredFormatter(self.config.include_context))
            else:
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            
            root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        
        # Add file handler
        if self.config.log_file or self.config.enable_json_file:
            log_file = self.config.log_file or str(log_path / "application.jsonl")
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.config.log_level.value)
            file_handler.setFormatter(StructuredFormatter(self.config.include_context))
            
            root_logger.addHandler(file_handler)
            self.handlers.append(file_handler)
        
        # Add syslog handler
        if self.config.enable_syslog:
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=self.config.syslog_address
                )
                syslog_handler.setLevel(self.config.log_level.value)
                syslog_handler.setFormatter(StructuredFormatter(self.config.include_context))
                
                root_logger.addHandler(syslog_handler)
                self.handlers.append(syslog_handler)
            except Exception as e:
                print(f"Failed to initialize syslog handler: {e}")
        
        self.initialized = True
        
        # Log initialization
        logger = self.get_logger("logging_manager")
        logger.info("Logging system initialized", extra_fields={
            "log_level": self.config.log_level.name,
            "log_format": self.config.log_format,
            "handlers": len(self.handlers)
        })
    
    def get_logger(self, name: str, context: LogContext = None) -> ContextualLogger:
        """Get or create a contextual logger"""
        if name not in self.loggers:
            self.loggers[name] = ContextualLogger(name, context)
        return self.loggers[name]
    
    def get_performance_logger(self, name: str, context: LogContext = None) -> PerformanceLogger:
        """Get performance logger"""
        contextual_logger = self.get_logger(name, context)
        return PerformanceLogger(contextual_logger)
    
    def set_log_level(self, level: LogLevel):
        """Set global log level"""
        self.config.log_level = level
        
        # Update all handlers
        for handler in self.handlers:
            handler.setLevel(level.value)
        
        # Update root logger
        logging.getLogger().setLevel(level.value)
    
    def shutdown(self):
        """Shutdown logging system"""
        for handler in self.handlers:
            handler.close()
        
        logging.shutdown()
        self.initialized = False

# Global logging manager
logging_manager = LoggingManager()

# Convenience functions
def get_logger(name: str, **context_kwargs) -> ContextualLogger:
    """Get a contextual logger"""
    context = LogContext(**context_kwargs) if context_kwargs else None
    return logging_manager.get_logger(name, context)

def get_performance_logger(name: str, **context_kwargs) -> PerformanceLogger:
    """Get a performance logger"""
    context = LogContext(**context_kwargs) if context_kwargs else None
    return logging_manager.get_performance_logger(name, context)

def initialize_logging(log_dir: str = "logs", log_level: LogLevel = LogLevel.INFO, 
                      structured: bool = True):
    """Initialize logging system with common settings"""
    config = LoggingConfig()
    config.log_level = log_level
    config.log_format = "structured" if structured else "simple"
    
    global logging_manager
    logging_manager = LoggingManager(config)
    logging_manager.initialize(log_dir)

# Decorators for automatic logging
def log_function_calls(logger_name: str = None, log_args: bool = False, log_result: bool = False):
    """Decorator to log function calls"""
    def decorator(func):
        nonlocal logger_name
        if logger_name is None:
            logger_name = f"{func.__module__}.{func.__qualname__}"
        
        logger = get_logger(logger_name)
        
        async def async_wrapper(*args, **kwargs):
            extra_fields = {"function": func.__name__}
            if log_args:
                extra_fields["args"] = str(args)
                extra_fields["kwargs"] = str(kwargs)
            
            logger.debug(f"Calling {func.__name__}", extra_fields=extra_fields)
            
            try:
                result = await func(*args, **kwargs)
                if log_result:
                    logger.debug(f"{func.__name__} completed", extra_fields={
                        "function": func.__name__,
                        "result": str(result)[:200]  # Limit result size
                    })
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed", extra_fields={
                    "function": func.__name__,
                    "error": str(e)
                })
                raise
        
        def sync_wrapper(*args, **kwargs):
            extra_fields = {"function": func.__name__}
            if log_args:
                extra_fields["args"] = str(args)
                extra_fields["kwargs"] = str(kwargs)
            
            logger.debug(f"Calling {func.__name__}", extra_fields=extra_fields)
            
            try:
                result = func(*args, **kwargs)
                if log_result:
                    logger.debug(f"{func.__name__} completed", extra_fields={
                        "function": func.__name__,
                        "result": str(result)[:200]  # Limit result size
                    })
                return result
            except Exception as e:
                logger.error(f"{func.__name__} failed", extra_fields={
                    "function": func.__name__,
                    "error": str(e)
                })
                raise
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Context manager for request logging
@contextmanager
def log_request(request_id: str, operation: str, **context_kwargs):
    """Context manager for request logging"""
    context = LogContext(request_id=request_id, operation=operation, **context_kwargs)
    logger = get_logger("request_logger", context)

    logger.info(f"Starting {operation}", extra_fields={"request_id": request_id})

    start_time = time.time()
    try:
        yield logger
        duration = time.time() - start_time
        logger.info(f"Completed {operation}", performance={
            "duration_seconds": duration,
            "success": True
        })
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed {operation}", extra_fields={
            "error": str(e)
        }, performance={
            "duration_seconds": duration,
            "success": False
        })
        raise
