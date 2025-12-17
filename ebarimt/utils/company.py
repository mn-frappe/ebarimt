# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Company Integration Utilities for eBarimt

For multi-company support, use:

    from ebarimt.mn_entity import get_entity_for_doc, get_ebarimt_entity

    # From a document (preferred - ensures all apps use same entity)
    entity = get_entity_for_doc(sales_invoice)
    merchant_tin = entity.merchant_tin
    pos_no = entity.pos_no

    # From company name
    entity = get_ebarimt_entity("ABC LLC")
"""

import frappe
from typing import Optional

# Import from local mn_entity module (each app has its own copy)
from ebarimt.mn_entity import (
    get_entity_for_doc,
    get_entity_for_company,
    get_etax_entity,
    get_ebarimt_entity,
    get_default_company,
    is_ebarimt_enabled,
    MNEntity,
)

__all__ = [
    "get_entity_for_doc",
    "get_entity_for_company",
    "get_etax_entity", 
    "get_ebarimt_entity",
    "get_default_company",
    "is_ebarimt_enabled",
    "MNEntity",
    # Legacy functions
    "get_merchant_info",
    "get_merchant_tin",
    "get_operator_tin",
    "get_pos_no",
    "get_district_code",
    "should_skip_ebarimt_for_qpay",
]


# =============================================================================
# Legacy functions (for backward compatibility)
# =============================================================================

def get_merchant_info(settings=None, company: Optional[str] = None, doc=None) -> dict:
    """
    DEPRECATED: Use get_entity_for_doc() or get_ebarimt_entity() instead.
    
    Get merchant info. Priority:
    1. doc (if provided) - uses doc.company
    2. company (if provided) - uses directly
    3. settings.company (if settings has company link)
    4. Fall back to settings fields
    """
    if settings is None:
        settings = frappe.get_single("eBarimt Settings")
    
    # Determine company
    company_name = None
    
    if doc and hasattr(doc, "company"):
        company_name = doc.company
    elif company:
        company_name = company
    elif settings and hasattr(settings, "company"):
        company_name = settings.company  # type: ignore
    
    # If we have a company, use the new method
    if company_name:
        try:
            entity = get_entity_for_company(company_name)
            return {
                "merchant_tin": entity.merchant_tin,
                "operator_tin": entity.operator_tin,
                "pos_no": entity.pos_no,
                "district_code": entity.district_code,
                "company": entity.company,
                "source": "company"
            }
        except Exception:
            pass
    
    # Fall back to settings fields
    result = {
        "merchant_tin": None,
        "operator_tin": None,
        "pos_no": None,
        "district_code": None,
        "company": None,
        "source": "settings"
    }
    
    if settings:
        result["merchant_tin"] = getattr(settings, "merchant_tin", None)
        result["operator_tin"] = getattr(settings, "operator_tin", None)
        result["pos_no"] = getattr(settings, "pos_no", None)
        result["district_code"] = getattr(settings, "district_code", None)
    
    return result


def get_merchant_tin(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get merchant TIN from Company or Settings."""
    return get_merchant_info(settings, company, doc).get("merchant_tin")


def get_operator_tin(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get operator TIN from Company or Settings."""
    return get_merchant_info(settings, company, doc).get("operator_tin")


def get_pos_no(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get POS number from Company or Settings."""
    return get_merchant_info(settings, company, doc).get("pos_no")


def get_district_code(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get default district code from Company or Settings."""
    return get_merchant_info(settings, company, doc).get("district_code")


def should_skip_ebarimt_for_qpay(doc=None) -> bool:
    """
    Check if eBarimt should be skipped because QPay already handled it.
    
    This reads the skip_if_qpay_ebarimt setting from eBarimt Settings.
    When enabled, eBarimt app will not create duplicate receipts for
    transactions that QPay already sent to eBarimt.
    
    Args:
        doc: Optional document to check for QPay receipt
        
    Returns:
        True if should skip, False otherwise
    """
    try:
        settings = frappe.get_single("eBarimt Settings")
        if not getattr(settings, "skip_if_qpay_ebarimt", False):
            return False
        
        # If doc provided, check if it has QPay receipt
        if doc:
            # Check if there's a QPay Invoice with eBarimt for this doc
            qpay_invoice = frappe.db.get_value(
                "QPay Invoice",
                {
                    "reference_doctype": doc.doctype,
                    "reference_name": doc.name,
                    "ebarimt_sent": 1
                },
                "name"
            )
            if qpay_invoice:
                return True
        
        return False
    except Exception:
        return False


def validate_merchant_info(settings=None, company: Optional[str] = None, doc=None) -> dict:
    """
    Validate that merchant info is properly configured.
    
    Returns:
        dict with validation status and missing fields
    """
    merchant = get_merchant_info(settings, company, doc)
    
    required_fields = ["merchant_tin", "pos_no"]
    
    result = {
        "valid": True,
        "missing": [],
        "source": merchant.get("source"),
        "company": merchant.get("company")
    }
    
    for field in required_fields:
        if not merchant.get(field):
            result["missing"].append(field)
            result["valid"] = False
    
    return result
