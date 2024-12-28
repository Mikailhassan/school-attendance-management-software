import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import json
from datetime import datetime
from functools import wraps
import traceback

class CustomJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def format(self, record):
        json_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        if hasattr(record, 'request_id'):
            json_record['request_id'] = record.request_id
        
        if record.exc_info:
            json_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        if hasattr(record, 'duration'):
            json_record['duration_ms'] = record.duration

        if self.kwargs.get('extra_fields'):
            for field in self.kwargs['extra_fields']:
                if hasattr(record, field):
                    json_record[field] = getattr(record, field)

        return json.dumps(json_record)

class LoggerFactory:
    """Factory class for creating and configuring loggers"""
    
    @staticmethod
    def create_logger(name: str, log_dir: str = None, level: str = "DEBUG"):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create different log files for different purposes
        log_files = {
            'app': os.path.join(log_dir, 'app.log'),
            'error': os.path.join(log_dir, 'error.log'),
            'access': os.path.join(log_dir, 'access.log'),
            'performance': os.path.join(log_dir, 'performance.log')
        }
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level))
        
        # Remove existing handlers if any
        if logger.handlers:
            logger.handlers.clear()
        
        # Add handlers for different log types
        handlers = {
            'app': RotatingFileHandler(
                log_files['app'],
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            ),
            'error': RotatingFileHandler(
                log_files['error'],
                maxBytes=10 * 1024 * 1024,
                backupCount=5
            ),
            'access': TimedRotatingFileHandler(
                log_files['access'],
                when='midnight',
                interval=1,
                backupCount=30
            ),
            'performance': RotatingFileHandler(
                log_files['performance'],
                maxBytes=10 * 1024 * 1024,
                backupCount=5
            ),
            'console': logging.StreamHandler()
        }
        
        # Configure handlers
        for handler_name, handler in handlers.items():
            if handler_name == 'error':
                handler.setLevel(logging.ERROR)
            else:
                handler.setLevel(getattr(logging, level))
            
            # Use JSON formatter for file handlers and simple formatter for console
            if isinstance(handler, (RotatingFileHandler, TimedRotatingFileHandler)):
                handler.setFormatter(CustomJsonFormatter(extra_fields=['request_id', 'user_id', 'ip_address']))
            else:
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            
            logger.addHandler(handler)
        
        return logger

def log_function_call(logger):
    """Decorator to log function entry, exit, and performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_name = func.__name__
            
            logger.info(f"Entering function: {func_name}")
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    f"Exiting function: {func_name}",
                    extra={
                        'duration': duration,
                        'function': func_name
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in function: {func_name}",
                    exc_info=True,
                    extra={'function': func_name}
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            func_name = func.__name__
            
            logger.info(f"Entering function: {func_name}")
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    f"Exiting function: {func_name}",
                    extra={
                        'duration': duration,
                        'function': func_name
                    }
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in function: {func_name}",
                    exc_info=True,
                    extra={'function': func_name}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Create default logger instance
logger = LoggerFactory.create_logger("SchoolAttendanceLogger")

