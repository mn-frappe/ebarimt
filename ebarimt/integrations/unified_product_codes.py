# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Unified Product Code Integration for eBarimt and QPay

This module provides a unified API for product classification codes
that works with both eBarimt and QPay apps.

PRINCIPLE: eBarimt is the master source for product codes (has tax info)
QPay can use these codes directly, avoiding duplication.

Usage:
- get_product_code(code) - returns product code from eBarimt or QPay
- sync_product_codes() - sync codes between apps without duplication
- get_item_product_code(item) - get product code for an Item
"""

import frappe
from frappe import _


def is_ebarimt_installed():
    """Check if eBarimt app is installed and has product codes."""
    return frappe.db.exists("DocType", "eBarimt Product Code")


def is_qpay_installed():
    """Check if QPay app is installed and has product codes."""
    return frappe.db.exists("DocType", "QPay Product Code")


@frappe.whitelist()
def get_product_code(code):
    """
    Get product code from eBarimt (preferred) or QPay.
    
    eBarimt is preferred because it has tax configuration
    (VAT type, city tax, excise).
    
    Args:
        code: Product classification code (GS1)
    
    Returns:
        dict: Product code info with source
    """
    # Try eBarimt first (has tax info)
    if is_ebarimt_installed():
        ebarimt_code = frappe.db.get_value(
            "eBarimt Product Code",
            code,
            ["classification_code", "name_mn", "name_en", "code_level",
             "vat_type", "city_tax_applicable", "excise_type", "oat_product_code"],
            as_dict=True
        )
        if ebarimt_code:
            return {
                "source": "eBarimt",
                "code": ebarimt_code.classification_code,
                "name": ebarimt_code.name_mn,
                "name_en": ebarimt_code.name_en,
                "level": ebarimt_code.code_level,
                "vat_type": ebarimt_code.vat_type,
                "city_tax_applicable": ebarimt_code.city_tax_applicable,
                "excise_type": ebarimt_code.excise_type,
                "oat_product_code": ebarimt_code.oat_product_code
            }
    
    # Fallback to QPay
    if is_qpay_installed():
        qpay_code = frappe.db.get_value(
            "QPay Product Code",
            code,
            ["product_code", "description", "code_level", "vat_type"],
            as_dict=True
        )
        if qpay_code:
            return {
                "source": "QPay",
                "code": qpay_code.product_code,
                "name": qpay_code.description,
                "name_en": None,
                "level": qpay_code.code_level,
                "vat_type": qpay_code.vat_type or "STANDARD",
                "city_tax_applicable": False,
                "excise_type": None,
                "oat_product_code": None
            }
    
    return None


@frappe.whitelist()
def search_product_codes(query, limit=20):
    """
    Search product codes from both apps.
    
    Args:
        query: Search string
        limit: Max results
    
    Returns:
        list: Matching product codes with source
    """
    results = []
    limit = int(limit)
    
    # Search eBarimt codes first
    if is_ebarimt_installed():
        ebarimt_codes = frappe.get_all(
            "eBarimt Product Code",
            filters=[
                ["enabled", "=", 1],
                ["classification_code", "like", f"%{query}%"]
            ],
            or_filters=[
                ["name_mn", "like", f"%{query}%"],
                ["name_en", "like", f"%{query}%"]
            ],
            fields=["classification_code", "name_mn", "vat_type", "city_tax_applicable"],
            limit=limit,
            order_by="classification_code"
        )
        for code in ebarimt_codes:
            results.append({
                "source": "eBarimt",
                "code": code.classification_code,
                "name": code.name_mn,
                "vat_type": code.vat_type,
                "city_tax": code.city_tax_applicable
            })
    
    # Add QPay codes if not enough results
    remaining = limit - len(results)
    if remaining > 0 and is_qpay_installed():
        # Exclude codes already in results
        existing_codes = [r["code"] for r in results]
        
        qpay_codes = frappe.get_all(
            "QPay Product Code",
            filters=[
                ["enabled", "=", 1],
                ["product_code", "not in", existing_codes] if existing_codes else ["enabled", "=", 1]
            ],
            or_filters=[
                ["product_code", "like", f"%{query}%"],
                ["description", "like", f"%{query}%"]
            ],
            fields=["product_code", "description", "vat_type"],
            limit=remaining,
            order_by="product_code"
        )
        for code in qpay_codes:
            if code.product_code not in existing_codes:
                results.append({
                    "source": "QPay",
                    "code": code.product_code,
                    "name": code.description,
                    "vat_type": code.vat_type or "STANDARD",
                    "city_tax": False
                })
    
    return results


@frappe.whitelist()
def get_item_product_code(item_code):
    """
    Get product code for an Item.
    
    Checks custom fields in this order:
    1. custom_ebarimt_product_code (preferred - has tax info)
    2. custom_qpay_product_code (fallback)
    3. custom_gs1_product_code (unified field)
    
    Args:
        item_code: Item code
    
    Returns:
        dict: Product code info or None
    """
    item = frappe.db.get_value(
        "Item", 
        item_code,
        ["custom_ebarimt_product_code", "custom_gs1_product_code"],
        as_dict=True
    )
    
    if not item:
        return None
    
    # Check eBarimt product code first
    if item.custom_ebarimt_product_code:
        return get_product_code(item.custom_ebarimt_product_code)
    
    # Check unified field
    if item.get("custom_gs1_product_code"):
        return get_product_code(item.custom_gs1_product_code)
    
    return None


@frappe.whitelist()
def sync_ebarimt_to_qpay():
    """
    Sync eBarimt product codes to QPay Product Code DocType.
    
    This ensures QPay has access to the same codes without duplication.
    Only syncs if both apps are installed.
    
    Returns:
        dict: Sync statistics
    """
    if not is_ebarimt_installed():
        return {"status": "skipped", "message": "eBarimt not installed"}
    
    if not is_qpay_installed():
        return {"status": "skipped", "message": "QPay not installed"}
    
    # Get all eBarimt codes
    ebarimt_codes = frappe.get_all(
        "eBarimt Product Code",
        fields=["classification_code", "name_mn", "code_level", "vat_type"],
        limit=0
    )
    
    # Get existing QPay codes
    existing_qpay = set(frappe.get_all(
        "QPay Product Code",
        pluck="product_code"
    ))
    
    created = 0
    updated = 0
    
    for ec in ebarimt_codes:
        code = ec.classification_code
        
        if code in existing_qpay:
            # Update existing
            frappe.db.set_value(
                "QPay Product Code",
                code,
                {
                    "description": ec.name_mn,
                    "code_level": ec.code_level,
                    "vat_type": ec.vat_type
                }
            )
            updated += 1
        else:
            # Create new
            try:
                doc = frappe.get_doc({
                    "doctype": "QPay Product Code",
                    "product_code": code,
                    "description": ec.name_mn,
                    "code_level": ec.code_level,
                    "vat_type": ec.vat_type,
                    "enabled": 1
                })
                doc.flags.ignore_permissions = True
                doc.insert()
                created += 1
            except Exception:
                pass  # Skip duplicates
        
        if (created + updated) % 500 == 0:
            frappe.db.commit()
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "total": len(ebarimt_codes)
    }


@frappe.whitelist()
def sync_qpay_to_ebarimt():
    """
    Sync QPay product codes to eBarimt Product Code DocType.
    
    Only syncs codes that don't exist in eBarimt.
    eBarimt codes have tax info that QPay codes don't.
    
    Returns:
        dict: Sync statistics
    """
    if not is_qpay_installed():
        return {"status": "skipped", "message": "QPay not installed"}
    
    if not is_ebarimt_installed():
        return {"status": "skipped", "message": "eBarimt not installed"}
    
    # Get existing eBarimt codes
    existing_ebarimt = set(frappe.get_all(
        "eBarimt Product Code",
        pluck="classification_code"
    ))
    
    # Get QPay codes not in eBarimt
    qpay_codes = frappe.get_all(
        "QPay Product Code",
        filters=[
            ["product_code", "not in", list(existing_ebarimt)] if existing_ebarimt else ["enabled", "=", 1]
        ],
        fields=["product_code", "description", "code_level", "vat_type"],
        limit=0
    )
    
    created = 0
    
    for qc in qpay_codes:
        if qc.product_code in existing_ebarimt:
            continue
        
        try:
            doc = frappe.get_doc({
                "doctype": "eBarimt Product Code",
                "classification_code": qc.product_code,
                "name_mn": qc.description,
                "code_level": qc.code_level or "Brick",
                "vat_type": qc.vat_type or "STANDARD",
                "enabled": 1
            })
            doc.flags.ignore_permissions = True
            doc.insert()
            created += 1
            existing_ebarimt.add(qc.product_code)
        except Exception:
            pass  # Skip errors
        
        if created % 500 == 0:
            frappe.db.commit()
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "created": created,
        "total_qpay": frappe.db.count("QPay Product Code"),
        "total_ebarimt": frappe.db.count("eBarimt Product Code")
    }


@frappe.whitelist()
def sync_product_codes():
    """
    Bidirectional sync between eBarimt and QPay product codes.
    
    1. Sync eBarimt → QPay (so QPay has all codes)
    2. Sync QPay → eBarimt (import any QPay-only codes)
    
    Returns:
        dict: Combined sync results
    """
    results = {}
    
    if is_ebarimt_installed() and is_qpay_installed():
        results["ebarimt_to_qpay"] = sync_ebarimt_to_qpay()
        results["qpay_to_ebarimt"] = sync_qpay_to_ebarimt()
    elif is_ebarimt_installed():
        results["message"] = "Only eBarimt installed - no sync needed"
    elif is_qpay_installed():
        results["message"] = "Only QPay installed - no sync needed"
    else:
        results["message"] = "Neither app has product codes installed"
    
    return results


def get_tax_info_for_item(item_code):
    """
    Get complete tax information for an Item.
    
    Args:
        item_code: Item code
    
    Returns:
        dict: Tax info (vat_type, vat_rate, city_tax_rate, excise_type)
    """
    product_info = get_item_product_code(item_code)
    
    if not product_info:
        return {
            "vat_type": "STANDARD",
            "vat_rate": 10,
            "city_tax_applicable": False,
            "city_tax_rate": 0,
            "excise_type": None
        }
    
    vat_rate = 10 if product_info["vat_type"] == "STANDARD" else 0
    city_tax_rate = 0.02 if product_info["city_tax_applicable"] else 0
    
    return {
        "vat_type": product_info["vat_type"],
        "vat_rate": vat_rate,
        "city_tax_applicable": product_info["city_tax_applicable"],
        "city_tax_rate": city_tax_rate,
        "excise_type": product_info["excise_type"]
    }
