# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Idempotency Utilities for eBarimt

Prevents duplicate receipt submissions. Critical for eBarimt where
duplicate receipts can cause tax compliance issues.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, TypeVar, cast

import frappe
from frappe import _

T = TypeVar("T")


@dataclass
class IdempotencyResult:
    """Result of an idempotent operation"""
    is_duplicate: bool
    cached_result: Any | None = None
    idempotency_key: str | None = None
    original_timestamp: datetime | None = None


class IdempotencyManager:
    """
    Manages idempotency for eBarimt operations.
    
    Prevents duplicate receipt submissions by tracking processed invoices.
    """
    
    def __init__(self, app_name: str = "ebarimt"):
        self.app_name = app_name
        self.cache_prefix = f"idempotency:{app_name}"
    
    def generate_key(self, operation: str, **params) -> str:
        """Generate idempotency key from operation and parameters"""
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_source = f"{operation}:{sorted_params}"
        key_hash = hashlib.sha256(key_source.encode()).hexdigest()[:16]
        return f"{self.cache_prefix}:{operation}:{key_hash}"
    
    def check(self, key: str) -> IdempotencyResult:
        """Check if operation was already processed"""
        cached = frappe.cache().get_value(key)
        
        if cached:
            return IdempotencyResult(
                is_duplicate=True,
                cached_result=cached.get("result"),
                idempotency_key=key,
                original_timestamp=datetime.fromisoformat(cached["timestamp"]) if cached.get("timestamp") else None
            )
        
        return IdempotencyResult(
            is_duplicate=False,
            idempotency_key=key
        )
    
    def store(self, key: str, result: Any, ttl_hours: int = 24):
        """Store operation result for idempotency checking"""
        data = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "app": self.app_name
        }
        
        frappe.cache().set_value(
            key,
            data,
            expires_in_sec=ttl_hours * 3600
        )
    
    def invalidate(self, key: str):
        """Remove idempotency key"""
        frappe.cache().delete_value(key)
    
    def get_or_execute(
        self,
        operation: str,
        func: Callable[..., T],
        ttl_hours: int = 24,
        **params
    ) -> tuple[T, bool]:
        """Execute function only if not already processed"""
        key = self.generate_key(operation, **params)
        check_result = self.check(key)
        
        if check_result.is_duplicate:
            frappe.logger(self.app_name).info(
                f"Idempotency hit for {operation}"
            )
            return cast(T, check_result.cached_result), True
        
        result = func(**params)
        self.store(key, result, ttl_hours)
        
        return result, False


# Singleton instance
idempotency = IdempotencyManager("ebarimt")


def idempotent(operation: str, ttl_hours: int = 24, key_params: list[str] | None = None):
    """Decorator to make a function idempotent"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            if key_params:
                params = {k: v for k, v in bound.arguments.items() if k in key_params}
            else:
                params = dict(bound.arguments)
            
            key = idempotency.generate_key(operation, **params)
            check_result = idempotency.check(key)
            
            if check_result.is_duplicate:
                frappe.logger("ebarimt").info(
                    f"Idempotent operation '{operation}' already processed"
                )
                return cast(T, check_result.cached_result)
            
            result = func(*args, **kwargs)
            idempotency.store(key, result, ttl_hours)
            
            return result
        
        return wrapper
    return decorator


# eBarimt-specific idempotency helpers

def get_receipt_idempotency_key(invoice_doctype: str, invoice_name: str, modified: str | None = None) -> str:
    """
    Generate idempotency key for receipt creation.
    
    Uses invoice modified timestamp to allow re-submission after invoice changes.
    """
    if not modified:
        modified = str(frappe.db.get_value(invoice_doctype, invoice_name, "modified"))
    
    return idempotency.generate_key(
        "create_receipt",
        doctype=invoice_doctype,
        docname=invoice_name,
        modified=modified
    )


def check_receipt_submission(invoice_doctype: str, invoice_name: str) -> IdempotencyResult:
    """Check if receipt was already created for this invoice version"""
    key = get_receipt_idempotency_key(invoice_doctype, invoice_name)
    return idempotency.check(key)


def store_receipt_result(invoice_doctype: str, invoice_name: str, result: dict):
    """Store successful receipt creation result"""
    modified = str(frappe.db.get_value(invoice_doctype, invoice_name, "modified"))
    key = get_receipt_idempotency_key(invoice_doctype, invoice_name, modified)
    
    # Store for 30 days (receipts are permanent)
    idempotency.store(key, result, ttl_hours=720)


def invalidate_receipt_idempotency(invoice_doctype: str, invoice_name: str):
    """
    Invalidate idempotency for an invoice.
    
    Call this when invoice is amended and needs new receipt.
    """
    key = get_receipt_idempotency_key(invoice_doctype, invoice_name)
    idempotency.invalidate(key)


# Lottery number tracking (prevent claiming same lottery twice)

def check_lottery_claimed(lottery_number: str) -> bool:
    """Check if lottery number was already claimed"""
    key = f"ebarimt:lottery:{lottery_number}"
    return frappe.cache().get_value(key) is not None


def mark_lottery_claimed(lottery_number: str, invoice_name: str):
    """Mark lottery number as claimed"""
    key = f"ebarimt:lottery:{lottery_number}"
    frappe.cache().set_value(
        key,
        {"invoice": invoice_name, "timestamp": datetime.utcnow().isoformat()},
        expires_in_sec=86400 * 365  # 1 year
    )
