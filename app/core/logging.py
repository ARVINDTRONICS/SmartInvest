import json
import logging
import sys
from datetime import datetime, UTC
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Custom formatter to output logs in JSON lines format.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Create standard log payload
        log_payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception traceback if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Include custom 'extra' parameters if passed
        standard_attributes = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message"
        }
        for key, value in record.__dict__.items():
            if key not in standard_attributes and not key.startswith("_"):
                log_payload[key] = value

        return json.dumps(log_payload)


class HealthCheckFilter(logging.Filter):
    """
    Suppresses standard uvicorn access logs for the health check endpoint to prevent log pollution.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger with the JSONFormatter and attach to stdout.
    """
    root_logger = logging.getLogger()
    
    # Filter out health check logs
    root_logger.addFilter(HealthCheckFilter())

    
    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Set logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Clean up and redirect uvicorn loggers so they pass through root logger
    for uvicorn_logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(uvicorn_logger_name)
        logger.handlers = []
        logger.propagate = True
