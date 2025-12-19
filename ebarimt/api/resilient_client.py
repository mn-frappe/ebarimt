# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Resilient HTTP Client Wrapper for eBarimt

Wraps the existing HTTP client with:
- Circuit breaker integration
- Structured logging with correlation IDs  
- Metrics collection
- Offline queue fallback for receipt operations
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe

from ebarimt.api.http_client import HTTPClient, get_client, make_request


class ResilientEBarimtClient:
    """
    Resilient wrapper for eBarimt HTTP client.
    
    Adds:
    - Circuit breaker for fault tolerance
    - Structured logging with correlation IDs
    - Metrics collection for monitoring
    - Offline queue fallback for receipts
    
    Usage:
        client = ResilientEBarimtClient()
        
        # Simple usage
        response = client.post("/api/v1/receipts", json=receipt_data)
        
        # With correlation ID for tracing
        with client.traced("create_receipt") as ctx:
            response = ctx.post("/api/v1/receipts", json=receipt_data)
    """
    
    def __init__(self, base_url: str = "https://api.frappe.mn", fallback_urls: list[str] | None = None, timeout: int = 30):
        self._inner_client = get_client(base_url, fallback_urls, timeout=timeout)
        self._base_url = base_url
        self._circuit_breaker = None
        self._logger = None
        self._metrics = None
        self._offline_queue = None
    
    @property
    def circuit_breaker(self):
        """Lazy load circuit breaker"""
        if self._circuit_breaker is None:
            try:
                from ebarimt.utils.resilience import ebarimt_pos_circuit_breaker
                self._circuit_breaker = ebarimt_pos_circuit_breaker
            except ImportError:
                self._circuit_breaker = None
        return self._circuit_breaker
    
    @property
    def logger(self):
        """Lazy load structured logger"""
        if self._logger is None:
            try:
                from ebarimt.utils.logging import get_logger
                self._logger = get_logger()
            except ImportError:
                self._logger = None
        return self._logger
    
    @property
    def metrics(self):
        """Lazy load metrics collector"""
        if self._metrics is None:
            try:
                from ebarimt.utils.metrics import metrics
                self._metrics = metrics
            except ImportError:
                self._metrics = None
        return self._metrics
    
    @property
    def offline_queue(self):
        """Lazy load offline queue"""
        if self._offline_queue is None:
            try:
                from ebarimt.utils.offline_queue import offline_queue
                self._offline_queue = offline_queue
            except ImportError:
                self._offline_queue = None
        return self._offline_queue
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for metrics"""
        error_str = str(error).lower()
        if "timeout" in error_str:
            return "timeout"
        elif "connection" in error_str:
            return "connection_error"
        elif "429" in error_str or "rate" in error_str:
            return "rate_limited"
        elif "503" in error_str or "unavailable" in error_str:
            return "service_unavailable"
        elif "500" in error_str or "502" in error_str or "504" in error_str:
            return "server_error"
        return "unknown"
    
    def _execute_with_resilience(
        self, 
        operation: str, 
        method: str, 
        path: str, 
        enable_offline_fallback: bool = False,
        receipt_data: dict | None = None,
        **kwargs
    ) -> Any:
        """Execute request with circuit breaker and metrics"""
        
        # Log request
        if self.logger:
            self.logger.info(
                f"eBarimt API call: {operation}",
                extra={"operation": operation, "method": method, "path": path}
            )
        
        error_type = None
        
        try:
            # Execute with circuit breaker if available
            if self.circuit_breaker:
                response = self.circuit_breaker.call(
                    self._inner_client.request,
                    method,
                    path,
                    **kwargs
                )
            else:
                response = self._inner_client.request(method, path, **kwargs)
            
            # Record success metrics
            if self.metrics:
                self.metrics.increment("ebarimt_api_requests", tags={"operation": operation, "status": "success"})
            
            return response
            
        except Exception as e:
            error_type = self._categorize_error(e)
            
            # Log error
            if self.logger:
                self.logger.error(
                    f"eBarimt API error: {operation}",
                    extra={"operation": operation, "error_type": error_type, "error": str(e)}
                )
            
            # Record error metrics
            if self.metrics:
                self.metrics.increment("ebarimt_api_requests", tags={"operation": operation, "status": "error"})
                self.metrics.increment("ebarimt_api_errors", tags={"operation": operation, "error_type": error_type})
            
            # Offline fallback for receipt operations
            if enable_offline_fallback and receipt_data and self.offline_queue:
                try:
                    queue_id = self.offline_queue.enqueue(
                        invoice_doctype=receipt_data.get("reference_doctype", "Sales Invoice"),
                        invoice_name=receipt_data.get("reference_doc", ""),
                        receipt_data=receipt_data
                    )
                    
                    if self.logger:
                        self.logger.warning(
                            f"Receipt queued for offline processing",
                            extra={"queue_id": queue_id, "original_error": str(e)}
                        )
                    
                    return {
                        "queued": True,
                        "queue_id": queue_id,
                        "message": "Receipt queued for processing when API is available"
                    }
                except Exception as queue_error:
                    if self.logger:
                        self.logger.error(f"Failed to queue receipt: {queue_error}")
            
            raise
    
    @contextmanager
    def traced(self, operation: str):
        """
        Context manager for traced API calls.
        
        Usage:
            with client.traced("create_receipt") as ctx:
                response = ctx.post("/api/v1/receipts", json=data)
        """
        import time
        import uuid
        
        # Set correlation ID
        correlation_id = str(uuid.uuid4())[:8]
        if hasattr(frappe, "local"):
            frappe.local.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            yield self
        finally:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.timing(f"ebarimt_api_duration_{operation}", duration)
            
            if hasattr(frappe, "local") and hasattr(frappe.local, "correlation_id"):
                delattr(frappe.local, "correlation_id")
    
    def get(self, path: str, **kwargs):
        """Make GET request with resilience"""
        return self._execute_with_resilience("get", "GET", path, **kwargs)
    
    def post(self, path: str, enable_offline_fallback: bool = False, receipt_data: dict | None = None, **kwargs):
        """Make POST request with resilience and optional offline fallback"""
        return self._execute_with_resilience(
            "post", 
            "POST", 
            path, 
            enable_offline_fallback=enable_offline_fallback,
            receipt_data=receipt_data,
            **kwargs
        )
    
    def delete(self, path: str, **kwargs):
        """Make DELETE request with resilience"""
        return self._execute_with_resilience("delete", "DELETE", path, **kwargs)


def get_resilient_client(
    base_url: str = "https://api.frappe.mn",
    fallback_urls: list[str] | None = None,
    timeout: int = 30
) -> ResilientEBarimtClient:
    """Get resilient eBarimt HTTP client"""
    return ResilientEBarimtClient(base_url, fallback_urls, timeout)


def create_receipt_with_fallback(receipt_data: dict, **kwargs) -> dict:
    """
    Create receipt with automatic offline fallback.
    
    If API is unavailable, queues the receipt for later processing.
    
    Args:
        receipt_data: Receipt data to submit
        **kwargs: Additional request parameters
        
    Returns:
        dict: API response or queue confirmation
    """
    client = get_resilient_client()
    return client.post(
        "/ebarimt/api/v1/receipt",
        json=receipt_data,
        enable_offline_fallback=True,
        receipt_data=receipt_data,
        **kwargs
    )
