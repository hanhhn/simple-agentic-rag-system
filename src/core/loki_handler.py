"""
Loki logging handler for sending logs to Grafana Loki.

This module provides a custom logging handler that sends log records
to Grafana Loki via HTTP API.
"""
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import queue

import httpx


class LokiHandler(logging.Handler):
    """
    Custom logging handler for sending logs to Grafana Loki.
    
    This handler batches log records and sends them to Loki via HTTP API.
    It supports structured logging with additional context and metadata.
    """
    
    def __init__(
        self,
        url: str = "http://localhost:3100",
        labels: Optional[Dict[str, str]] = None,
        batch_size: int = 10,
        batch_interval: float = 5.0,
        timeout: float = 10.0
    ):
        """
        Initialize the Loki handler.
        
        Args:
            url: Loki API URL
            labels: Static labels to attach to all logs
            batch_size: Maximum number of logs to batch before sending
            batch_interval: Maximum time to wait before sending a batch (seconds)
            timeout: HTTP request timeout (seconds)
        """
        super().__init__()
        self.url = url.rstrip('/') + "/loki/api/v1/push"
        self.static_labels = labels or {}
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.timeout = timeout
        
        self._batch: List[Dict[str, Any]] = []
        self._batch_lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._shutdown = False
        
        # Start the batch timer
        self._start_timer()
    
    def _start_timer(self) -> None:
        """Start the batch flush timer."""
        if self._timer:
            self._timer.cancel()
        
        self._timer = threading.Timer(self.batch_interval, self.flush)
        self._timer.daemon = True
        self._timer.start()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to Loki.
        
        Args:
            record: Log record to emit
        """
        try:
            # Format the log message
            message = self.format(record)
            
            # Extract additional context from record
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in {
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'message', 'pathname', 'process', 'processName',
                    'relativeCreated', 'thread', 'threadName', 'exc_info',
                    'exc_text', 'stack_info', 'stack_trace'
                } and not key.startswith('_'):
                    extra_data[key] = value
            
            # Create the log entry
            log_entry = {
                "stream": {
                    **self.static_labels,
                    "level": record.levelname.lower(),
                    "logger": record.name,
                    "service": getattr(record, 'service', 'unknown'),
                    "host": os.getenv('HOSTNAME', 'localhost'),
                    **{k: str(v) for k, v in extra_data.items()}
                },
                "values": [
                    [str(int(record.created * 1e9)), message]
                ]
            }
            
            # Add structured data if available
            if hasattr(record, 'structured_data'):
                log_entry["stream"].update(
                    {k: str(v) for k, v in record.structured_data.items()}
                )
            
            # Add to batch
            with self._batch_lock:
                self._batch.append(log_entry)
                
                # Flush if batch is full
                if len(self._batch) >= self.batch_size:
                    self.flush()
                    
        except Exception:
            # Don't raise exceptions in logging handler
            self.handleError(record)
    
    def flush(self) -> None:
        """Flush the current batch of logs to Loki."""
        if self._shutdown:
            return
            
        with self._batch_lock:
            if not self._batch:
                return
                
            # Get the current batch
            batch = self._batch.copy()
            self._batch.clear()
        
        # Send the batch to Loki
        try:
            self._send_batch(batch)
        except Exception as e:
            # Log the error but don't raise
            print(f"Error sending logs to Loki: {e}")
    
    def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Send a batch of logs to Loki.
        
        Args:
            batch: Batch of log entries to send
        """
        if not batch:
            return
            
        payload = {"streams": batch}
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error sending logs to Loki: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request error sending logs to Loki: {e}")
        except Exception as e:
            print(f"Unexpected error sending logs to Loki: {e}")
    
    def close(self) -> None:
        """Close the handler and flush remaining logs."""
        self._shutdown = True
        
        # Cancel the timer
        if self._timer:
            self._timer.cancel()
            self._timer = None
        
        # Flush remaining logs
        self.flush()
        
        # Close parent handler
        super().close()


class StructuredLogger(logging.Logger):
    """
    Custom logger that supports structured logging.
    
    This logger allows adding structured data to log records
    for better searching and filtering in Loki.
    """
    
    def structlog(self, msg: str, **kwargs: Any) -> None:
        """
        Log a structured message with additional context.
        
        Args:
            msg: Log message
            **kwargs: Additional structured data to include
        """
        extra = {"structured_data": kwargs}
        self.info(msg, extra=extra)


def setup_loki_logging(
    loki_url: Optional[str] = None,
    service_name: str = "rag-backend",
    log_level: str = "INFO",
    batch_size: int = 10,
    batch_interval: float = 5.0
) -> logging.Logger:
    """
    Set up logging with Loki handler.
    
    Args:
        loki_url: Loki API URL (default from environment variable)
        service_name: Service name for labeling logs
        log_level: Logging level
        batch_size: Maximum batch size
        batch_interval: Batch interval in seconds
        
    Returns:
        Configured logger instance
    """
    # Get Loki URL from environment if not provided
    if not loki_url:
        loki_url = os.getenv("LOKI_URL", "http://loki:3100")
    
    # Create logger
    logger = StructuredLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create Loki handler (only if not in test mode)
    if os.getenv("APP_ENV") != "test":
        loki_handler = LokiHandler(
            url=loki_url,
            labels={
                "job": "rag-system",
                "service": service_name,
                "environment": os.getenv("APP_ENV", "development")
            },
            batch_size=batch_size,
            batch_interval=batch_interval
        )
        loki_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use JSON formatter for Loki
        loki_formatter = logging.Formatter('%(message)s')
        loki_handler.setFormatter(loki_formatter)
        logger.addHandler(loki_handler)
    
    return logger


# Monkey patch logging module to support structured logging
def _patch_logging() -> None:
    """Patch logging module to use StructuredLogger."""
    logging.setLoggerClass(StructuredLogger)


# Auto-patch on import
_patch_logging()
