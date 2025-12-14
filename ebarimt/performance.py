# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false
"""
eBarimt Performance Optimization Module

High-performance utilities for:
- Database index management
- Batch item data loading (N+1 fix)
- Connection pooling
- Query optimization
- Metrics collection
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache, wraps
from typing import Any, Callable, TypeVar

import frappe
from frappe.utils import cint, flt, now_datetime

T = TypeVar("T")


# =============================================================================
# DATABASE INDEX MANAGEMENT
# =============================================================================

REQUIRED_INDEXES = [
    # eBarimt Receipt Log - Most queried table
    {"table": "tabeBarimt Receipt Log", "columns": ["receipt_id"], "name": "idx_receipt_id"},
    {"table": "tabeBarimt Receipt Log", "columns": ["sales_invoice"], "name": "idx_sales_invoice"},
    {"table": "tabeBarimt Receipt Log", "columns": ["pos_invoice"], "name": "idx_pos_invoice"},
    {"table": "tabeBarimt Receipt Log", "columns": ["status", "creation"], "name": "idx_status_creation"},
    {"table": "tabeBarimt Receipt Log", "columns": ["bill_id"], "name": "idx_bill_id"},
    
    # eBarimt District - Lookup by code
    {"table": "tabeBarimt District", "columns": ["district_code"], "name": "idx_district_code"},
    
    # eBarimt Tax Code - Lookup by code
    {"table": "tabeBarimt Tax Code", "columns": ["tax_code"], "name": "idx_tax_code"},
    
    # eBarimt Product Code - GS1 lookups
    {"table": "tabeBarimt Product Code", "columns": ["code"], "name": "idx_code"},
    {"table": "tabeBarimt Product Code", "columns": ["vat_type"], "name": "idx_vat_type"},
    {"table": "tabeBarimt Product Code", "columns": ["hierarchy_level"], "name": "idx_hierarchy_level"},
]


def ensure_indexes() -> dict:
    """
    Ensure all required indexes exist for optimal performance.
    
    Call this during site setup or maintenance.
    
    Returns:
        dict: {created, total, errors}
    """
    created = 0
    errors = []
    
    for idx in REQUIRED_INDEXES:
        try:
            if not _index_exists(idx["table"], idx["name"]):
                _create_index(idx["table"], idx["columns"], idx["name"])
                created += 1
        except Exception as e:
            errors.append(f"{idx['name']}: {e}")
            frappe.log_error(
                f"Index creation failed for {idx['name']}: {e}",
                "eBarimt Index Error"
            )
    
    if created:
        frappe.logger("ebarimt").info(f"eBarimt: Created {created} database indexes")
    
    return {"created": created, "total": len(REQUIRED_INDEXES), "errors": errors}


def _index_exists(table: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    try:
        result = frappe.db.sql(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s", index_name)
        return bool(result)
    except Exception:
        return False


def _create_index(table: str, columns: list[str], index_name: str):
    """Create an index on a table."""
    cols = ", ".join([f"`{c}`" for c in columns])
    frappe.db.sql_ddl(f"CREATE INDEX `{index_name}` ON `{table}` ({cols})")


def analyze_tables():
    """Run ANALYZE on eBarimt tables to update statistics."""
    tables = [
        "tabeBarimt Receipt Log",
        "tabeBarimt Product Code",
        "tabeBarimt District",
        "tabeBarimt Tax Code",
    ]
    for table in tables:
        try:
            frappe.db.sql(f"ANALYZE TABLE `{table}`")
        except Exception:
            pass


# =============================================================================
# BATCH ITEM DATA LOADING (N+1 FIX)
# =============================================================================

def batch_load_item_data(item_codes: list[str], settings=None) -> dict[str, dict]:
    """
    Batch load all item data needed for eBarimt receipt in 3-4 queries.
    
    This replaces N*4 queries with just 3-4 queries regardless of item count.
    
    Args:
        item_codes: List of item codes to load
        settings: Optional eBarimt Settings doc (cached if not provided)
    
    Returns:
        dict: {item_code: {tax_code, barcode, vat_type, city_tax_applicable, excise_type, product_info}}
    
    Example:
        item_codes = [item.item_code for item in pos_doc.items]
        item_data = batch_load_item_data(item_codes)
        for item in pos_doc.items:
            info = item_data.get(item.item_code, {})
            tax_code = info.get("tax_code", "VAT_ABLE")
    """
    if not item_codes:
        return {}
    
    if settings is None:
        settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Query 1: Get all items with their eBarimt fields
    items_data = frappe.get_all(
        "Item",
        filters={"name": ["in", item_codes]},
        fields=[
            "name", "custom_ebarimt_tax_code", "custom_ebarimt_barcode",
            "custom_ebarimt_product_code", "custom_city_tax_applicable"
        ]
    )
    
    # Query 2: Get all barcodes for items that don't have custom barcode
    items_without_barcode = [
        i.name for i in items_data 
        if not i.custom_ebarimt_barcode
    ]
    barcode_map = {}
    if items_without_barcode:
        barcodes = frappe.get_all(
            "Item Barcode",
            filters={"parent": ["in", items_without_barcode]},
            fields=["parent", "barcode"],
            order_by="idx"
        )
        # First barcode for each item
        for b in barcodes:
            if b.parent not in barcode_map:
                barcode_map[b.parent] = b.barcode
    
    # Query 3: Get all product codes with tax info
    product_codes = list(set(
        i.custom_ebarimt_product_code for i in items_data 
        if i.custom_ebarimt_product_code
    ))
    product_info = {}
    if product_codes:
        products = frappe.get_all(
            "eBarimt Product Code",
            filters={"name": ["in", product_codes]},
            fields=["name", "vat_type", "city_tax_applicable", "excise_type"]
        )
        product_info = {p.name: p for p in products}
    
    # Query 4: Get tax codes
    tax_code_names = list(set(
        i.custom_ebarimt_tax_code for i in items_data 
        if i.custom_ebarimt_tax_code
    ))
    tax_code_map = {}
    if tax_code_names:
        taxes = frappe.get_all(
            "eBarimt Tax Code",
            filters={"name": ["in", tax_code_names]},
            fields=["name", "tax_code"]
        )
        tax_code_map = {t.name: t.tax_code for t in taxes}
    
    # Get default tax code
    default_tax_code = "VAT_ABLE"
    if settings.get("default_tax_code"):
        default_tax_code = frappe.db.get_value(
            "eBarimt Tax Code", settings.default_tax_code, "tax_code"
        ) or "VAT_ABLE"
    
    # Build result
    result = {}
    for item in items_data:
        product = product_info.get(item.custom_ebarimt_product_code, {})
        
        result[item.name] = {
            "tax_code": tax_code_map.get(item.custom_ebarimt_tax_code, default_tax_code),
            "barcode": item.custom_ebarimt_barcode or barcode_map.get(item.name) or item.name,
            "vat_type": product.get("vat_type", "STANDARD") if product else "STANDARD",
            "city_tax_applicable": bool(
                product.get("city_tax_applicable") if product 
                else item.custom_city_tax_applicable
            ),
            "excise_type": product.get("excise_type") if product else None,
            "product_code": item.custom_ebarimt_product_code,
        }
    
    return result


def get_item_tax_info_batch(item_codes: list[str]) -> dict[str, dict]:
    """
    Get complete tax information for multiple items in batch.
    
    Returns dict with vat_type, vat_applicable, city_tax_applicable for each item.
    """
    if not item_codes:
        return {}
    
    # Get items with product codes
    items = frappe.get_all(
        "Item",
        filters={"name": ["in", item_codes]},
        fields=["name", "custom_ebarimt_product_code", "custom_city_tax_applicable"]
    )
    
    # Get product code details in batch
    product_codes = [i.custom_ebarimt_product_code for i in items if i.custom_ebarimt_product_code]
    product_info = {}
    if product_codes:
        products = frappe.get_all(
            "eBarimt Product Code",
            filters={"name": ["in", product_codes]},
            fields=["name", "vat_type", "city_tax_applicable", "excise_type"]
        )
        product_info = {p.name: p for p in products}
    
    result = {}
    for item in items:
        product = product_info.get(item.custom_ebarimt_product_code, {})
        
        vat_type = product.get("vat_type", "STANDARD") if product else "STANDARD"
        
        result[item.name] = {
            "vat_type": vat_type,
            "vat_applicable": vat_type == "STANDARD",
            "city_tax_applicable": bool(
                product.get("city_tax_applicable") if product 
                else item.custom_city_tax_applicable
            ),
            "excise_type": product.get("excise_type") if product else None,
        }
    
    return result


# =============================================================================
# CACHING UTILITIES
# =============================================================================

def cached(ttl: int = 300, key_prefix: str = "ebarimt"):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Cache time-to-live in seconds
        key_prefix: Prefix for cache keys
    
    Example:
        @cached(ttl=60, key_prefix="district")
        def get_district_code(district_name):
            return frappe.db.get_value(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            key_data = json.dumps({
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
            }, sort_keys=True)
            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
            cache_key = f"{key_prefix}:{func.__name__}:{key_hash}"
            
            # Try cache
            cached_value = frappe.cache().get_value(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                frappe.cache().set_value(cache_key, result, expires_in_sec=ttl)
            
            return result
        
        return wrapper
    return decorator


def request_cache(func: Callable[..., T]) -> Callable[..., T]:
    """
    Cache function result for the duration of a single HTTP request.
    
    Uses frappe.local storage which is cleared after each request.
    
    Example:
        @request_cache
        def get_ebarimt_client():
            return EBarimtClient()  # Expensive initialization
    """
    cache_attr = f"_ebarimt_request_cache_{func.__name__}"
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(frappe.local, cache_attr):
            setattr(frappe.local, cache_attr, {})
        
        cache = getattr(frappe.local, cache_attr)
        
        # Generate key
        key_data = json.dumps({
            "args": [str(a) for a in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
        }, sort_keys=True)
        key = hashlib.md5(key_data.encode()).hexdigest()[:12]
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        
        return cache[key]
    
    return wrapper


# =============================================================================
# METRICS AND MONITORING
# =============================================================================

@contextmanager
def track_time(operation: str):
    """
    Context manager to track operation time.
    
    Example:
        with track_time("receipt_submission"):
            client.create_receipt(data)
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = (time.time() - start) * 1000
        frappe.logger("ebarimt.perf").info(
            f"{operation}: {elapsed:.2f}ms"
        )


class PerformanceMetrics:
    """Collect and report performance metrics."""
    
    _metrics: dict[str, list[float]] = defaultdict(list)
    
    @classmethod
    def record(cls, operation: str, duration_ms: float):
        """Record a metric."""
        cls._metrics[operation].append(duration_ms)
    
    @classmethod
    def get_stats(cls, operation: str | None = None) -> dict:
        """Get statistics for operations."""
        if operation:
            times = cls._metrics.get(operation, [])
            if not times:
                return {}
            return {
                "count": len(times),
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
            }
        
        return {
            op: cls.get_stats(op) 
            for op in cls._metrics
        }
    
    @classmethod
    def reset(cls):
        """Reset all metrics."""
        cls._metrics.clear()


# =============================================================================
# BULK OPERATIONS
# =============================================================================

def bulk_update_receipt_status(updates: dict[str, str]) -> int:
    """
    Bulk update receipt log statuses using SQL CASE statement.
    
    Much faster than individual updates.
    
    Args:
        updates: {receipt_log_name: new_status}
    
    Returns:
        int: Number updated
    """
    if not updates:
        return 0
    
    cases = []
    names = []
    for name, status in updates.items():
        cases.append(
            f"WHEN name = '{frappe.db.escape(name)}' THEN '{frappe.db.escape(status)}'"
        )
        names.append(f"'{frappe.db.escape(name)}'")
    
    sql = f"""
        UPDATE `tabeBarimt Receipt Log`
        SET status = CASE {" ".join(cases)} END,
            modified = NOW()
        WHERE name IN ({",".join(names)})
    """
    frappe.db.sql(sql)
    frappe.db.commit()
    
    return len(updates)


def bulk_insert_products(products: list[dict], batch_size: int = 500) -> dict:
    """
    High-performance bulk insert for eBarimt Product Codes.
    
    Uses raw SQL INSERT IGNORE for maximum speed.
    
    Args:
        products: List of product dicts with code, description, vat_type, etc.
        batch_size: Records per batch
    
    Returns:
        dict: {inserted, skipped, time_ms}
    """
    start = time.time()
    inserted = 0
    skipped = 0
    
    # Get existing codes in one query
    existing = set(frappe.get_all("eBarimt Product Code", pluck="name"))
    
    # Filter new products
    new_products = [p for p in products if p.get("name") not in existing]
    skipped = len(products) - len(new_products)
    
    if not new_products:
        return {"inserted": 0, "skipped": skipped, "time_ms": 0}
    
    # Batch insert
    for i in range(0, len(new_products), batch_size):
        batch = new_products[i:i + batch_size]
        values = []
        
        for p in batch:
            name = frappe.db.escape(str(p.get("name", "")))
            code = frappe.db.escape(str(p.get("code", "")))
            desc = frappe.db.escape(str(p.get("description", ""))[:500])
            vat_type = frappe.db.escape(str(p.get("vat_type", "STANDARD")))
            hierarchy = frappe.db.escape(str(p.get("hierarchy_level", "")))
            
            values.append(
                f"('{name}', '{code}', '{desc}', '{vat_type}', '{hierarchy}', "
                f"NOW(), NOW(), 'Administrator', 'Administrator')"
            )
        
        if values:
            sql = f"""
                INSERT IGNORE INTO `tabeBarimt Product Code`
                (name, code, description, vat_type, hierarchy_level,
                 creation, modified, owner, modified_by)
                VALUES {",".join(values)}
            """
            frappe.db.sql(sql)
            inserted += len(batch)
        
        frappe.db.commit()
    
    elapsed = (time.time() - start) * 1000
    return {"inserted": inserted, "skipped": skipped, "time_ms": round(elapsed, 2)}


# =============================================================================
# QUERY OPTIMIZATION
# =============================================================================

def get_pending_receipts_fast(limit: int = 100, days: int = 7) -> list[dict]:
    """
    Ultra-fast pending receipt fetch using direct SQL.
    
    Bypasses ORM overhead for maximum speed.
    """
    sql = """
        SELECT
            name, receipt_id, sales_invoice, pos_invoice,
            status, creation, bill_type
        FROM `tabeBarimt Receipt Log`
        WHERE status IN ('Pending', 'Failed')
          AND creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY creation ASC
        LIMIT %s
    """
    return frappe.db.sql(sql, (days, limit), as_dict=True)  # type: ignore


def get_receipt_stats_fast(days: int = 30) -> dict:
    """
    Fast receipt statistics using single optimized query.
    """
    result = frappe.db.sql("""
        SELECT
            COUNT(*) as total_receipts,
            SUM(CASE WHEN status = 'Submitted' THEN 1 ELSE 0 END) as submitted_count,
            SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_count
        FROM `tabeBarimt Receipt Log`
        WHERE creation >= DATE_SUB(NOW(), INTERVAL %s DAY)
    """, (days,), as_dict=True)
    
    return result[0] if result else {}  # type: ignore


# =============================================================================
# INITIALIZATION
# =============================================================================

@frappe.whitelist()
def optimize_database():
    """
    Run all database optimizations.
    
    Call this after installation or during maintenance.
    """
    results = {
        "indexes": ensure_indexes(),
        "analyzed": False
    }
    
    try:
        analyze_tables()
        results["analyzed"] = True
    except Exception as e:
        results["analyze_error"] = str(e)
    
    return results
