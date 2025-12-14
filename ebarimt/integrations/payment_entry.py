# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Payment Entry Integration
Handles payment tracking for eBarimt receipts
"""

import frappe
from frappe import _
from frappe.utils import flt, cint


def validate_payment_entry(doc, method=None):
    """
    Validate Payment Entry for eBarimt
    - Ensure payment code is set if linked to eBarimt invoice
    - Validate payment type mapping
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    # Check if this payment is linked to an eBarimt invoice
    has_ebarimt_invoice = False
    
    for ref in doc.references or []:
        if ref.reference_doctype in ("Sales Invoice", "POS Invoice"):
            receipt_id = frappe.db.get_value(
                ref.reference_doctype, 
                ref.reference_name, 
                "custom_ebarimt_receipt_id"
            )
            if receipt_id:
                has_ebarimt_invoice = True
                break
    
    if has_ebarimt_invoice:
        # Auto-set payment code from Mode of Payment if not set
        if not doc.get("custom_ebarimt_payment_code") and doc.mode_of_payment:
            payment_type = frappe.db.get_value(
                "Mode of Payment", 
                doc.mode_of_payment, 
                "custom_ebarimt_payment_type"
            )
            if payment_type:
                doc.custom_ebarimt_payment_code = payment_type


def on_submit_payment_entry(doc, method=None):
    """
    On submit - update eBarimt Receipt Log with payment info
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    # Find linked eBarimt receipts and update payment status
    for ref in doc.references or []:
        if ref.reference_doctype in ("Sales Invoice", "POS Invoice"):
            receipt_id = frappe.db.get_value(
                ref.reference_doctype, 
                ref.reference_name, 
                "custom_ebarimt_receipt_id"
            )
            if receipt_id:
                _update_receipt_payment_status(receipt_id, doc, ref.allocated_amount)


def on_cancel_payment_entry(doc, method=None):
    """
    On cancel - update eBarimt Receipt Log payment status
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    for ref in doc.references or []:
        if ref.reference_doctype in ("Sales Invoice", "POS Invoice"):
            receipt_id = frappe.db.get_value(
                ref.reference_doctype, 
                ref.reference_name, 
                "custom_ebarimt_receipt_id"
            )
            if receipt_id:
                _revert_receipt_payment_status(receipt_id, doc.name)


def _update_receipt_payment_status(receipt_id, payment_doc, amount):
    """Update eBarimt Receipt Log with payment information"""
    try:
        receipt_log = frappe.get_doc("eBarimt Receipt Log", {"receipt_id": receipt_id})
        
        # Track payment
        receipt_log.db_set("payment_entry", payment_doc.name, update_modified=False)
        receipt_log.db_set("payment_amount", flt(amount), update_modified=False)
        receipt_log.db_set("payment_date", payment_doc.posting_date, update_modified=False)
        
        # Get payment type code
        payment_code = payment_doc.get("custom_ebarimt_payment_code")
        if payment_code:
            receipt_log.db_set("payment_type", payment_code, update_modified=False)
        
        frappe.db.commit()
        
    except frappe.DoesNotExistError:
        pass  # No receipt log found
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Payment Entry Update Failed: {receipt_id}"
        )


def _revert_receipt_payment_status(receipt_id, payment_name):
    """Revert payment tracking on cancellation"""
    try:
        receipt_log = frappe.get_doc("eBarimt Receipt Log", {"receipt_id": receipt_id})
        
        if receipt_log.payment_entry == payment_name:
            receipt_log.db_set("payment_entry", None, update_modified=False)
            receipt_log.db_set("payment_amount", 0, update_modified=False)
            receipt_log.db_set("payment_date", None, update_modified=False)
            frappe.db.commit()
            
    except frappe.DoesNotExistError:
        pass
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Payment Entry Revert Failed: {receipt_id}"
        )


@frappe.whitelist()
def get_ebarimt_payment_types():
    """Get all eBarimt payment types for selection"""
    return frappe.get_all(
        "eBarimt Payment Type",
        filters={"enabled": 1},
        fields=["name", "payment_code", "payment_name"],
        order_by="payment_code"
    )


@frappe.whitelist()
def update_payment_type_mapping(mode_of_payment, ebarimt_payment_type):
    """Update Mode of Payment with eBarimt payment type mapping"""
    frappe.db.set_value(
        "Mode of Payment",
        mode_of_payment,
        "custom_ebarimt_payment_type",
        ebarimt_payment_type
    )
    return {"success": True}


@frappe.whitelist()
def get_payment_summary_for_invoice(doctype, docname):
    """Get payment summary with eBarimt codes for an invoice"""
    payments = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": doctype,
            "reference_name": docname,
            "docstatus": 1
        },
        fields=["parent", "allocated_amount"]
    )
    
    result = []
    for payment in payments:
        pe = frappe.get_doc("Payment Entry", payment.parent)
        result.append({
            "payment_entry": pe.name,
            "amount": payment.allocated_amount,
            "mode_of_payment": pe.mode_of_payment,
            "ebarimt_payment_code": pe.get("custom_ebarimt_payment_code"),
            "posting_date": pe.posting_date
        })
    
    return result
