# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Structured Logging Utilities for eBarimt

Provides correlation IDs and structured logging for tracing requests
across the application and API calls.
"""

import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable

import frappe


class CorrelationContext:
    """Manages correlation ID for request tracing"""
    
    HEADER_NAME = "X-Correlation-ID"
    LOCAL_KEY = "mn_correlation_id"
    
    @classmethod
    def get_id(cls) -> str:
        """Get or create correlation ID for current request"""
        if not hasattr(frappe.local, cls.LOCAL_KEY):
            correlation_id = None
            if hasattr(frappe.local, "request") and frappe.local.request:
                correlation_id = frappe.local.request.headers.get(cls.HEADER_NAME)
            
            if not correlation_id:
                correlation_id = cls._generate_id()
            
            setattr(frappe.local, cls.LOCAL_KEY, correlation_id)
        
        return getattr(frappe.local, cls.LOCAL_KEY)
    
    @classmethod
    def set_id(cls, correlation_id: str):
        """Set correlation ID (useful for background jobs)"""
        setattr(frappe.local, cls.LOCAL_KEY, correlation_id)
    
    @classmethod
    def _generate_id(cls) -> str:
        """Generate a short, unique correlation ID"""
        return uuid.uuid4().hex[:12]
    
    @classmethod
    def clear(cls):
        """Clear correlation ID"""
        if hasattr(frappe.local, cls.LOCAL_KEY):
            delattr(frappe.local, cls.LOCAL_KEY)


class StructuredLogger:
    """
    Structured logger for eBarimt.
    
    Usage:
        logger = StructuredLogger("ebarimt.api")
        logger.info("Receipt created", receipt_id="123", lottery="ABC")
    """
    
    def __init__(self, name: str = "ebarimt"):
        self.name = name
        self._logger = frappe.logger(name)
    
    def _format_message(self, level: str, message: str, **kwargs) -> dict[str, Any]:
        """Format log entry as structured data"""
        entry: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "app": "ebarimt",
            "logger": self.name,
            "correlation_id": CorrelationContext.get_id(),
            "message": message,
        }
        
        if frappe.session and frappe.session.user:
            entry["user"] = frappe.session.user
        
        if kwargs:
            entry["data"] = kwargs
        
        return entry
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method"""
        entry = self._format_message(level, message, **kwargs)
        log_line = json.dumps(entry, default=str, ensure_ascii=False)
        getattr(self._logger, level.lower())(log_line)
    
    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("critical", message, **kwargs)
    
    def api_call(
        self,
        method: str,
        url: str,
        status_code: int | None = None,
        duration_ms: float | None = None,
        request_body: Any = None,
        response_body: Any = None,
        error: str | None = None
    ):
        """Log API call with standard fields"""
        data: dict[str, Any] = {
            "http_method": method,
            "url": url,
        }
        
        if status_code is not None:
            data["status_code"] = status_code
        if duration_ms is not None:
            data["duration_ms"] = round(duration_ms, 2)
        if error:
            data["error"] = error
        
        settings = frappe.get_cached_doc("eBarimt Settings")
        if getattr(settings, "enable_debug_log", False):
            if request_body:
                data["request"] = request_body
            if response_body:
                data["response"] = response_body
        
        level = "info" if not error else "error"
        self._log(level, f"API {method} {url}", **data)
    
    def receipt_event(
        self,
        event: str,
        invoice_name: str,
        receipt_id: str | None = None,
        lottery: str | None = None,
        amount: float | None = None,
        bill_type: str | None = None,
        error: str | None = None
    ):
        """Log receipt-specific event"""
        data: dict[str, Any] = {
            "event": event,
            "invoice": invoice_name,
        }
        if receipt_id:
            data["receipt_id"] = receipt_id
        if lottery:
            data["lottery"] = lottery
        if amount:
            data["amount"] = amount
        if bill_type:
            data["bill_type"] = bill_type
        if error:
            data["error"] = error
        
        level = "info" if not error else "error"
        self._log(level, f"Receipt {event}", **data)


# Singleton logger instance
logger = StructuredLogger("ebarimt")


def get_logger(name: str | None = None) -> StructuredLogger:
    """Get a logger instance"""
    if name is None:
        return logger
    return StructuredLogger(name)


def log_function_call(func: Callable) -> Callable:
    """Decorator to log function entry and exit"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        
        logger.debug(f"Entering {func_name}", args_count=len(args), kwargs_keys=list(kwargs.keys()))
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func_name}", success=True)
            return result
        except Exception as e:
            logger.error(f"Exception in {func_name}", error=str(e), error_type=type(e).__name__)
            raise
    
    return wrapper


@contextmanager
def log_context(**kwargs):
    """Context manager for adding extra context to all logs within block"""
    if not hasattr(frappe.local, "log_context"):
        frappe.local.log_context = {}
    
    old_context = frappe.local.log_context.copy()
    frappe.local.log_context.update(kwargs)
    
    try:
        yield
    finally:
        frappe.local.log_context = old_context


def get_log_context() -> dict:
    """Get current log context"""
    if hasattr(frappe.local, "log_context"):
        return frappe.local.log_context.copy()
    return {}


def log_api_request(response, duration_ms: float | None = None):
    """Log API request/response from requests.Response object"""
    logger.api_call(
        method=response.request.method,
        url=response.url,
        status_code=response.status_code,
        duration_ms=duration_ms or (response.elapsed.total_seconds() * 1000 if response.elapsed else None),
        error=None if response.ok else response.text[:500]
    )
