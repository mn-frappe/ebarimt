# pyright: reportMissingImports=false
"""
eBarimt Logging Utilities

Provides standardized logging for all eBarimt actions using Frappe's logging infrastructure.
Logs are stored in:
- Error Log DocType (for errors)
- eBarimt Log DocType (for API calls and receipts)
- frappe.log file (for debug/info logs)
"""

import frappe
from frappe import _
from typing import Optional, Dict, Any
import json
import traceback
from functools import wraps


# Logger instance for file logging
def get_logger():
    """Get eBarimt logger instance."""
    return frappe.logger("ebarimt", allow_site=True, file_count=10)


def log_info(message: str, data: Optional[Dict] = None):
    """
    Log info level message.
    
    Args:
        message: Log message
        data: Optional additional data to log
    """
    logger = get_logger()
    if data:
        logger.info(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.info(message)


def log_debug(message: str, data: Optional[Dict] = None):
    """Log debug level message."""
    logger = get_logger()
    if data:
        logger.debug(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.debug(message)


def log_warning(message: str, data: Optional[Dict] = None):
    """Log warning level message."""
    logger = get_logger()
    if data:
        logger.warning(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.warning(message)


def log_error(message: str, data: Optional[Dict] = None, exc: Optional[Exception] = None):
    """
    Log error to both file and Error Log DocType.
    
    Args:
        message: Error message
        data: Optional additional data
        exc: Optional exception object
    """
    logger = get_logger()
    
    error_details = {
        "message": message,
        "data": data,
        "traceback": traceback.format_exc() if exc else None
    }
    
    logger.error(f"{message} | Details: {json.dumps(error_details, default=str)}")
    
    # Also log to Error Log DocType for visibility in UI
    frappe.log_error(
        message=json.dumps(error_details, default=str, indent=2),
        title=f"eBarimt: {message[:100]}"
    )


def log_api_call(
    endpoint: str,
    method: str = "POST",
    request_data: Optional[Dict] = None,
    response_data: Optional[Dict] = None,
    status: str = "Success",
    error_message: Optional[str] = None,
    reference_doctype: Optional[str] = None,
    reference_name: Optional[str] = None,
    execution_time: Optional[float] = None
):
    """
    Log API call to eBarimt Log DocType.
    
    Args:
        endpoint: API endpoint called
        method: HTTP method (GET, POST, etc.)
        request_data: Request payload
        response_data: Response received
        status: Success/Failed/Error
        error_message: Error message if failed
        reference_doctype: Related DocType
        reference_name: Related document name
        execution_time: Time taken in seconds
    """
    try:
        # Check if eBarimt Log DocType exists
        if not frappe.db.exists("DocType", "eBarimt Log"):
            # Fall back to file logging
            log_info(f"API Call: {method} {endpoint}", {
                "status": status,
                "reference": f"{reference_doctype}/{reference_name}" if reference_doctype else None,
                "execution_time": execution_time,
                "error": error_message
            })
            return
        
        doc = frappe.get_doc({
            "doctype": "eBarimt Log",
            "endpoint": endpoint,
            "method": method,
            "request_data": json.dumps(request_data, default=str) if request_data else None,
            "response_data": json.dumps(response_data, default=str) if response_data else None,
            "status": status,
            "error_message": error_message,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "execution_time": execution_time
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        
    except Exception as e:
        # Don't let logging failures break the main flow
        log_warning(f"Failed to create eBarimt Log: {str(e)}")


def log_receipt(
    action: str,
    invoice: Optional[str] = None,
    receipt_id: Optional[str] = None,
    lottery: Optional[str] = None,
    qr_data: Optional[str] = None,
    amount: Optional[float] = None,
    vat_amount: Optional[float] = None,
    status: str = "Pending",
    receipt_type: str = "B2C",
    customer_tin: Optional[str] = None,
    details: Optional[Dict] = None
):
    """
    Log eBarimt receipt event.
    
    Args:
        action: Action performed (send_receipt, void_receipt, check_status, etc.)
        invoice: Sales Invoice name
        receipt_id: eBarimt receipt ID (DDTD)
        lottery: Lottery number
        qr_data: QR code data
        amount: Total amount
        vat_amount: VAT amount
        status: Receipt status
        receipt_type: B2C or B2B
        customer_tin: Customer TIN for B2B
        details: Additional details
    """
    log_info(f"Receipt: {action}", {
        "invoice": invoice,
        "receipt_id": receipt_id,
        "lottery": lottery,
        "amount": amount,
        "vat_amount": vat_amount,
        "status": status,
        "receipt_type": receipt_type,
        "customer_tin": customer_tin,
        "details": details
    })
    
    # Also log to Activity Log for audit trail
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"eBarimt {action}: {invoice or receipt_id}",
            "content": json.dumps({
                "action": action,
                "invoice": invoice,
                "receipt_id": receipt_id,
                "lottery": lottery,
                "amount": amount,
                "vat_amount": vat_amount,
                "status": status,
                "receipt_type": receipt_type,
                "customer_tin": customer_tin
            }, default=str),
            "reference_doctype": "Sales Invoice" if invoice else None,
            "reference_name": invoice,
            "status": "Success" if status in ["Sent", "Success", "Completed"] else "Open"
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Activity log is optional


def log_action(action_name: str):
    """
    Decorator to log function entry/exit and exceptions.
    
    Usage:
        @log_action("Send eBarimt Receipt")
        def send_receipt(invoice_name):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            func_name = func.__name__
            
            # Log entry
            logger.debug(f"[{action_name}] Starting {func_name}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"[{action_name}] Completed {func_name}")
                return result
            except Exception as e:
                log_error(f"[{action_name}] Failed in {func_name}: {str(e)}", exc=e)
                raise
        
        return wrapper
    return decorator


def log_scheduler_task(task_name: str):
    """
    Decorator for scheduler tasks with comprehensive logging.
    
    Usage:
        @log_scheduler_task("Auto Retry Failed Receipts")
        def auto_retry_failed():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            log_info(f"Scheduler Task Started: {task_name}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                log_info(f"Scheduler Task Completed: {task_name}", {
                    "execution_time_seconds": round(execution_time, 2),
                    "result": result if isinstance(result, (dict, list, str, int, float, bool)) else str(type(result))
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                log_error(f"Scheduler Task Failed: {task_name}", {
                    "execution_time_seconds": round(execution_time, 2)
                }, exc=e)
                raise
        
        return wrapper
    return decorator


# Convenience functions for common log patterns
def log_receipt_sent(invoice: str, receipt_id: str, lottery: str, amount: float, vat_amount: float):
    """Log successful receipt submission."""
    log_receipt("send_receipt", invoice=invoice, receipt_id=receipt_id, 
               lottery=lottery, amount=amount, vat_amount=vat_amount, status="Sent")


def log_receipt_voided(invoice: str, receipt_id: str):
    """Log receipt void."""
    log_receipt("void_receipt", invoice=invoice, receipt_id=receipt_id, status="Voided")


def log_receipt_failed(invoice: str, error_message: str):
    """Log failed receipt."""
    log_receipt("send_receipt_failed", invoice=invoice, status="Failed", 
               details={"error": error_message})


def log_tin_lookup(tin: str, result: Dict, cached: bool = False):
    """Log TIN lookup."""
    log_info(f"TIN Lookup: {tin}", {
        "found": bool(result),
        "cached": cached,
        "company_name": result.get("name") if result else None
    })


def log_pos_sync(pos_id: str, action: str, status: str, details: Optional[Dict] = None):
    """Log POS synchronization event."""
    log_info(f"POS Sync: {action}", {
        "pos_id": pos_id,
        "status": status,
        "details": details
    })
