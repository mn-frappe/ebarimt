# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Background Job Utilities for eBarimt

Provides async job wrappers with retry logic for non-blocking receipt operations.
"""

from typing import Any, Callable

import frappe
from frappe import _
from frappe.utils import now_datetime


def enqueue_with_retry(
    method: str | Callable,
    queue: str = "default",
    timeout: int = 300,
    max_retries: int = 3,
    retry_delay: int = 60,
    job_name: str | None = None,
    **kwargs
) -> str | None:
    """
    Enqueue a job with automatic retry on failure.
    
    Args:
        method: Method to call (string path or callable)
        queue: Queue name (short, default, long)
        timeout: Job timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        job_name: Optional job name for tracking
        **kwargs: Arguments to pass to the method
    
    Returns:
        Job ID
    """
    kwargs["_retry_count"] = kwargs.get("_retry_count", 0)
    kwargs["_max_retries"] = max_retries
    kwargs["_retry_delay"] = retry_delay
    kwargs["_original_method"] = method if isinstance(method, str) else f"{method.__module__}.{method.__name__}"
    
    job = frappe.enqueue(
        "ebarimt.utils.background._execute_with_retry",
        queue=queue,
        timeout=timeout,
        job_name=job_name or f"ebarimt_{now_datetime().strftime('%Y%m%d_%H%M%S')}",
        method=method,
        **kwargs
    )
    
    return job.id if job else None


def _execute_with_retry(method: str | Callable, **kwargs):
    """Execute method with retry logic"""
    retry_count = kwargs.pop("_retry_count", 0)
    max_retries = kwargs.pop("_max_retries", 3)
    retry_delay = kwargs.pop("_retry_delay", 60)
    original_method = kwargs.pop("_original_method", None)
    
    try:
        if isinstance(method, str):
            module_path, method_name = method.rsplit(".", 1)
            module = frappe.get_module(module_path)
            func = getattr(module, method_name)
        else:
            func = method
        
        result = func(**kwargs)
        
        frappe.logger("ebarimt").info(
            f"Background job completed: {original_method or method}"
        )
        
        return result
        
    except Exception as e:
        frappe.logger("ebarimt").error(
            f"Background job failed: {original_method or method}, "
            f"attempt {retry_count + 1}/{max_retries + 1}, error: {e}"
        )
        
        if retry_count < max_retries:
            frappe.enqueue(
                "ebarimt.utils.background._execute_with_retry",
                queue="default",
                timeout=300,
                at_front=False,
                enqueue_after_commit=True,
                job_name=f"ebarimt_retry_{retry_count + 1}",
                method=method,
                _retry_count=retry_count + 1,
                _max_retries=max_retries,
                _retry_delay=retry_delay,
                _original_method=original_method,
                **kwargs
            )
            frappe.logger("ebarimt").info(
                f"Scheduled retry {retry_count + 2}/{max_retries + 1} "
                f"for {original_method or method}"
            )
        else:
            frappe.log_error(
                title=f"eBarimt Job Failed: {original_method or method}",
                message=f"Max retries ({max_retries}) exceeded.\n\nError: {e}\n\nKwargs: {kwargs}"
            )
            _notify_job_failure(original_method or str(method), str(e), kwargs)
        
        raise


def _notify_job_failure(method: str, error: str, kwargs: dict):
    """Send notification about job failure"""
    try:
        admins = frappe.get_all(
            "Has Role",
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent"
        )
        
        for admin in admins[:3]:
            frappe.publish_realtime(
                "msgprint",
                {
                    "message": _(
                        "eBarimt background job failed after max retries: {0}"
                    ).format(method),
                    "indicator": "red"
                },
                user=admin
            )
    except Exception:
        pass


# Convenience functions for eBarimt operations

def enqueue_receipt_creation(invoice_name: str, invoice_doctype: str = "Sales Invoice", **kwargs):
    """Enqueue eBarimt receipt creation (non-blocking)"""
    return enqueue_with_retry(
        "ebarimt.api.api.create_receipt_async",
        queue="short",
        timeout=120,
        max_retries=3,
        retry_delay=30,
        job_name=f"ebarimt_receipt_{invoice_name}",
        invoice_name=invoice_name,
        invoice_doctype=invoice_doctype,
        **kwargs
    )


def enqueue_receipt_void(receipt_id: str, **kwargs):
    """Enqueue receipt void operation"""
    return enqueue_with_retry(
        "ebarimt.api.api.void_receipt_async",
        queue="short",
        timeout=120,
        max_retries=2,
        retry_delay=30,
        job_name=f"ebarimt_void_{receipt_id}",
        receipt_id=receipt_id,
        **kwargs
    )


def enqueue_taxpayer_lookup(tin: str, **kwargs):
    """Enqueue taxpayer info lookup"""
    return enqueue_with_retry(
        "ebarimt.api.api.get_taxpayer_info_async",
        queue="short",
        timeout=60,
        max_retries=2,
        retry_delay=15,
        job_name=f"ebarimt_taxpayer_{tin}",
        tin=tin,
        **kwargs
    )


def enqueue_product_code_sync(**kwargs):
    """Enqueue GS1 product code sync"""
    return enqueue_with_retry(
        "ebarimt.utils.gs1_sync.sync_product_codes_async",
        queue="long",
        timeout=1800,
        max_retries=2,
        retry_delay=300,
        job_name="ebarimt_gs1_sync",
        **kwargs
    )


def enqueue_pending_receipts_processing(**kwargs):
    """Enqueue processing of pending receipts (offline queue)"""
    return enqueue_with_retry(
        "ebarimt.utils.offline_queue.process_pending_receipts",
        queue="default",
        timeout=600,
        max_retries=1,
        retry_delay=60,
        job_name="ebarimt_pending_receipts",
        **kwargs
    )


# Job status tracking

def get_job_status(job_id: str) -> dict:
    """Get status of a background job"""
    try:
        from frappe.utils.background_jobs import get_job
        job = get_job(job_id)
        if job:
            return {
                "id": job_id,
                "status": job.get_status(),
                "result": job.result if job.is_finished else None,
                "error": str(job.exc_info) if job.is_failed else None
            }
    except Exception:
        pass
    
    return {"id": job_id, "status": "unknown"}


def cancel_job(job_id: str) -> bool:
    """Cancel a pending background job"""
    try:
        from rq import cancel_job as rq_cancel
        rq_cancel(job_id, connection=frappe.cache())
        return True
    except Exception:
        return False
