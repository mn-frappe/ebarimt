# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Health Check API for eBarimt

Provides endpoints for monitoring eBarimt app health and connectivity to VAT system.
"""

from datetime import datetime
from typing import Any

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def health():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status with timestamp
    """
    return {
        "status": "healthy",
        "app": "ebarimt",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@frappe.whitelist()
def detailed_health():
    """
    Detailed health check with dependency status.
    
    Requires authentication. Checks:
    - Database connectivity
    - Redis/cache connectivity
    - eBarimt POS API settings
    - Pending receipts queue status
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    checks: dict[str, Any] = {
        "status": "healthy",
        "app": "ebarimt",
        "version": get_app_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    # Database check
    checks["checks"]["database"] = check_database()
    
    # Cache check
    checks["checks"]["cache"] = check_cache()
    
    # Settings check
    checks["checks"]["settings"] = check_settings()
    
    # POS terminal status
    checks["checks"]["pos_terminal"] = check_pos_terminal()
    
    # Pending receipts
    checks["checks"]["pending_queue"] = check_pending_queue()
    
    # Circuit breaker status
    checks["checks"]["circuit_breaker"] = check_circuit_breaker()
    
    # GS1 database
    checks["checks"]["gs1_database"] = check_gs1_database()
    
    # Overall status
    critical_checks = ["database", "settings"]
    critical_healthy = all(
        checks["checks"].get(c, {}).get("status") == "healthy" 
        for c in critical_checks
    )
    all_healthy = all(
        c.get("status") in ["healthy", "disabled"] 
        for c in checks["checks"].values()
    )
    
    if not critical_healthy:
        checks["status"] = "unhealthy"
    elif not all_healthy:
        checks["status"] = "degraded"
    
    return checks


@frappe.whitelist()
def check_api_connectivity():
    """
    Test connectivity to eBarimt POS API.
    
    Requires authentication.
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    result = {
        "status": "unknown",
        "response_time_ms": None,
        "api_endpoint": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        import time
        
        settings = frappe.get_single("eBarimt Settings")
        if not getattr(settings, "enabled", False):
            result["status"] = "disabled"
            result["error"] = "eBarimt integration is disabled"
            return result
        
        result["api_endpoint"] = getattr(settings, "api_url", None)
        
        start_time = time.time()
        
        # Test with info endpoint
        from ebarimt.api import EBarimtClient
        client = EBarimtClient()
        response = client.get_info()
        
        end_time = time.time()
        result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        result["status"] = "healthy"
        
        # Include some API info if available
        if isinstance(response, dict):
            result["api_version"] = response.get("version")
            result["pos_id"] = response.get("posId")
        
    except ImportError:
        result["status"] = "error"
        result["error"] = "eBarimt client not available"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def get_app_version() -> str:
    """Get eBarimt app version"""
    try:
        return frappe.get_attr("ebarimt.__version__")
    except AttributeError:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=frappe.get_app_path("ebarimt"),
                capture_output=True,
                text=True
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"


def check_database() -> dict:
    """Check database connectivity"""
    try:
        frappe.db.sql("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_cache() -> dict:
    """Check Redis/cache connectivity"""
    try:
        test_key = "ebarimt:health_check"
        frappe.cache().set_value(test_key, "ok", expires_in_sec=60)
        value = frappe.cache().get_value(test_key)
        if value == "ok":
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Cache read/write mismatch"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_settings() -> dict:
    """Check eBarimt settings configuration"""
    try:
        settings = frappe.get_single("eBarimt Settings")
        
        issues = []
        if not getattr(settings, "enabled", False):
            return {"status": "disabled"}
        
        if not getattr(settings, "api_url", None):
            issues.append("API URL not configured")
        if not getattr(settings, "pos_id", None):
            issues.append("POS ID not configured")
        
        if issues:
            return {"status": "warning", "issues": issues}
        
        return {"status": "healthy"}
    except frappe.DoesNotExistError:
        return {"status": "unhealthy", "error": "Settings not found"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_pos_terminal() -> dict:
    """Check POS terminal registration status"""
    try:
        settings = frappe.get_single("eBarimt Settings")
        
        if not getattr(settings, "enabled", False):
            return {"status": "disabled"}
        
        pos_id = getattr(settings, "pos_id", None)
        if not pos_id:
            return {"status": "warning", "error": "POS not registered"}
        
        # Check last sync time if tracked
        last_sync_val = getattr(settings, "last_sync", None)
        if last_sync_val:
            from frappe.utils import get_datetime
            last_sync = get_datetime(last_sync_val)
            if last_sync is None:
                return {"status": "warning", "error": "Invalid last_sync date"}
            hours_since_sync = (datetime.now() - last_sync).total_seconds() / 3600
            
            if hours_since_sync > 24:
                return {
                    "status": "warning",
                    "pos_id": pos_id,
                    "last_sync_hours_ago": round(hours_since_sync, 1)
                }
        
        return {
            "status": "healthy",
            "pos_id": pos_id
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_pending_queue() -> dict:
    """Check pending receipts queue"""
    try:
        # Count pending receipts if doctype exists
        if frappe.db.table_exists("eBarimt Pending Receipt"):
            pending_count = frappe.db.count(
                "eBarimt Pending Receipt",
                {"status": ["in", ["Pending", "Failed"]]}
            )
            
            if pending_count > 100:
                return {
                    "status": "warning",
                    "pending_count": pending_count,
                    "message": "High number of pending receipts"
                }
            
            return {
                "status": "healthy",
                "pending_count": pending_count
            }
        
        return {"status": "not_configured"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_circuit_breaker() -> dict:
    """Check circuit breaker status"""
    try:
        from ebarimt.utils.resilience import ebarimt_pos_circuit_breaker
        
        cb = ebarimt_pos_circuit_breaker
        return {
            "status": "healthy" if cb.state.value == "closed" else "degraded",
            "state": cb.state.value,
            "failure_count": getattr(cb, "failure_count", 0)
        }
    except ImportError:
        return {"status": "unknown", "error": "Resilience module not available"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_gs1_database() -> dict:
    """Check GS1 product codes database"""
    try:
        if frappe.db.table_exists("GS1 Product Code"):
            count = frappe.db.count("GS1 Product Code")
            return {
                "status": "healthy",
                "product_codes": count
            }
        return {"status": "not_configured"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@frappe.whitelist()
def readiness():
    """Kubernetes-style readiness probe"""
    try:
        frappe.db.sql("SELECT 1")
        
        settings = frappe.get_single("eBarimt Settings")
        if getattr(settings, "enabled", False) and not getattr(settings, "api_url", None):
            frappe.throw("Not ready: API URL not configured")
        
        return {"ready": True}
    except Exception as e:
        frappe.local.response.http_status_code = 503
        return {"ready": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def liveness():
    """Kubernetes-style liveness probe"""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat() + "Z"}
