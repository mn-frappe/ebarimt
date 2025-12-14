# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false

"""
eBarimt Mode of Payment Integration
Mapping ERPNext payment modes to eBarimt payment types
"""

import frappe
from frappe import _


def validate_mode_of_payment(doc, method=None):
    """
    Validate Mode of Payment eBarimt mapping
    """
    if not doc.get("custom_ebarimt_payment_type"):
        return
    
    # Verify payment type exists
    if not frappe.db.exists("eBarimt Payment Type", doc.custom_ebarimt_payment_type):
        frappe.throw(_("Invalid eBarimt Payment Type: {0}").format(
            doc.custom_ebarimt_payment_type
        ))


@frappe.whitelist()
def get_ebarimt_payment_code(mode_of_payment):
    """
    Get eBarimt payment code for a mode of payment
    """
    if not mode_of_payment:
        return None
    
    payment_type = frappe.db.get_value(
        "Mode of Payment",
        mode_of_payment,
        "custom_ebarimt_payment_type"
    )
    
    if not payment_type:
        return None
    
    return frappe.db.get_value(
        "eBarimt Payment Type",
        payment_type,
        "payment_code"
    )


@frappe.whitelist()
def sync_payment_type_mappings():
    """
    Auto-map common payment modes to eBarimt payment types
    """
    # Common mappings
    mappings = {
        "Cash": "P",      # Cash payment
        "Bank Draft": "T",  # Bank transfer
        "Bank Transfer": "T",
        "Credit Card": "C",  # Card payment
        "Debit Card": "C",
        "Check": "T",
        "Wire Transfer": "T"
    }
    
    updated = 0
    
    for mode_name, code in mappings.items():
        if frappe.db.exists("Mode of Payment", mode_name):
            # Find payment type with this code
            payment_type = frappe.db.get_value(
                "eBarimt Payment Type",
                {"payment_code": code},
                "name"
            )
            
            if payment_type:
                current = frappe.db.get_value(
                    "Mode of Payment",
                    mode_name,
                    "custom_ebarimt_payment_type"
                )
                
                if not current:
                    frappe.db.set_value(
                        "Mode of Payment",
                        mode_name,
                        "custom_ebarimt_payment_type",
                        payment_type
                    )
                    updated += 1
    
    frappe.db.commit()
    
    return {
        "success": True,
        "updated": updated,
        "message": _("{0} payment modes mapped to eBarimt types").format(updated)
    }


@frappe.whitelist()
def get_all_payment_mappings():
    """
    Get all Mode of Payment to eBarimt Payment Type mappings
    """
    modes = frappe.get_all(
        "Mode of Payment",
        fields=["name", "enabled", "type", "custom_ebarimt_payment_type"]
    )
    
    result = []
    for mode in modes:
        payment_code = None
        payment_name = None
        
        if mode.custom_ebarimt_payment_type:
            payment_info = frappe.db.get_value(
                "eBarimt Payment Type",
                mode.custom_ebarimt_payment_type,
                ["payment_code", "payment_name"],
                as_dict=True
            )
            if payment_info:
                payment_code = payment_info.payment_code
                payment_name = payment_info.payment_name
        
        result.append({
            "mode_of_payment": mode.name,
            "enabled": mode.enabled,
            "type": mode.type,
            "ebarimt_payment_type": mode.custom_ebarimt_payment_type,
            "ebarimt_payment_code": payment_code,
            "ebarimt_payment_name": payment_name
        })
    
    return result


@frappe.whitelist()
def set_payment_mapping(mode_of_payment, ebarimt_payment_type):
    """
    Set eBarimt payment type for a mode of payment
    """
    if not frappe.db.exists("Mode of Payment", mode_of_payment):
        frappe.throw(_("Mode of Payment not found: {0}").format(mode_of_payment))
    
    if ebarimt_payment_type and not frappe.db.exists("eBarimt Payment Type", ebarimt_payment_type):
        frappe.throw(_("eBarimt Payment Type not found: {0}").format(ebarimt_payment_type))
    
    frappe.db.set_value(
        "Mode of Payment",
        mode_of_payment,
        "custom_ebarimt_payment_type",
        ebarimt_payment_type
    )
    
    return {"success": True}


def get_payment_amounts_by_type(invoice_doc):
    """
    Get payment amounts grouped by eBarimt payment type for an invoice
    Used when creating eBarimt receipt with multiple payment types
    """
    payments = []
    
    # Get payments linked to this invoice
    payment_refs = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": invoice_doc.doctype,
            "reference_name": invoice_doc.name,
            "docstatus": 1
        },
        fields=["parent", "allocated_amount"]
    )
    
    for ref in payment_refs:
        pe = frappe.get_cached_doc("Payment Entry", ref.parent)
        
        # Get eBarimt payment code
        payment_code = "P"  # Default to cash
        
        if pe.get("custom_ebarimt_payment_code"):
            code = frappe.db.get_value(
                "eBarimt Payment Type",
                pe.custom_ebarimt_payment_code,
                "payment_code"
            )
            if code:
                payment_code = code
        elif pe.mode_of_payment:
            code = get_ebarimt_payment_code(pe.mode_of_payment)
            if code:
                payment_code = code
        
        payments.append({
            "code": payment_code,
            "amount": ref.allocated_amount
        })
    
    # Group by code
    grouped = {}
    for p in payments:
        code = p["code"]
        if code in grouped:
            grouped[code] += p["amount"]
        else:
            grouped[code] = p["amount"]
    
    return [{"code": k, "amount": v} for k, v in grouped.items()]
