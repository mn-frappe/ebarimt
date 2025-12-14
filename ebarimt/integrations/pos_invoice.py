# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt POS Invoice Integration
Handles automatic receipt submission for POS Invoice
POS Invoices are auto-submitted immediately on payment
"""

import frappe
from frappe import _
from frappe.utils import flt, cint, now_datetime, getdate


def validate_pos_invoice(doc, method=None):
    """Validate POS Invoice for eBarimt requirements"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    # Skip if already has receipt
    if doc.get("custom_ebarimt_receipt_id"):
        return
    
    # Skip returns - handled separately
    if doc.is_return:
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Validate customer TIN for B2B
    bill_type = doc.get("custom_ebarimt_bill_type") or settings.default_bill_type or "B2C_RECEIPT"
    
    if bill_type == "B2B_RECEIPT":
        customer_tin = get_customer_tin(doc.customer)
        if not customer_tin:
            frappe.throw(_("Customer TIN is required for B2B receipts. Please set TIN in Customer master."))


def on_submit_pos_invoice(doc, method=None):
    """Auto-submit eBarimt receipt on POS Invoice submission"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Check if auto-submit is enabled
    if not settings.auto_submit_on_invoice:
        return
    
    # Skip if already has receipt
    if doc.get("custom_ebarimt_receipt_id"):
        frappe.msgprint(_("eBarimt receipt already exists for this POS invoice"))
        return
    
    # Handle return/credit note
    if doc.is_return:
        # Check if settings allow auto return processing
        if settings.get("auto_process_returns"):
            try:
                create_pos_return_receipt(doc)
            except Exception as e:
                frappe.log_error(
                    message=str(e),
                    title=f"eBarimt POS Return Failed: {doc.name}"
                )
        return
    
    # Queue the receipt submission
    try:
        submit_pos_ebarimt_receipt(doc)
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"eBarimt POS Submit Failed: {doc.name}"
        )
        frappe.msgprint(
            _("eBarimt receipt submission failed: {0}").format(str(e)),
            indicator="red"
        )


def on_cancel_pos_invoice(doc, method=None):
    """Handle eBarimt on POS Invoice cancellation"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    if not doc.get("custom_ebarimt_receipt_id"):
        return
    
    # Log cancellation - actual reversal may need manual processing
    frappe.log_error(
        message=f"POS Invoice {doc.name} with eBarimt receipt {doc.custom_ebarimt_receipt_id} was cancelled. Manual return may be required.",
        title="eBarimt POS Invoice Cancelled"
    )
    
    # Update receipt log status
    try:
        receipt_log = frappe.get_doc("eBarimt Receipt Log", {
            "receipt_id": doc.custom_ebarimt_receipt_id
        })
        receipt_log.db_set("status", "Cancelled", update_modified=True)
        receipt_log.add_comment("Info", _("Invoice cancelled. Consider creating a return receipt."))
    except Exception:
        pass


def submit_pos_ebarimt_receipt(pos_doc):
    """Submit eBarimt receipt for a POS Invoice"""
    from ebarimt.api.client import EBarimtClient
    from ebarimt.ebarimt.doctype.ebarimt_receipt_log.ebarimt_receipt_log import create_receipt_log
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Initialize client
    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )
    
    # Determine bill type
    bill_type = pos_doc.get("custom_ebarimt_bill_type") or settings.default_bill_type or "B2C_RECEIPT"
    
    # Build receipt data
    receipt_data = build_pos_receipt_data(pos_doc, settings, bill_type)
    
    # Submit receipt
    response = client.create_receipt(receipt_data)
    
    if response.get("success"):
        # Update POS invoice with receipt info
        frappe.db.set_value("POS Invoice", pos_doc.name, {
            "custom_ebarimt_receipt_id": response.get("billId"),
            "custom_ebarimt_lottery": response.get("lottery"),
            "custom_ebarimt_qr_data": response.get("qrData"),
            "custom_ebarimt_date": response.get("date") or now_datetime()
        }, update_modified=False)
        
        # Create receipt log
        create_receipt_log(pos_doc, response, bill_type)
        
        frappe.msgprint(
            _("eBarimt receipt created successfully. Lottery: {0}").format(
                response.get("lottery") or "N/A"
            ),
            indicator="green"
        )
        
        return response
    else:
        error_msg = response.get("message") or _("Unknown error")
        frappe.log_error(
            message=f"eBarimt submission failed: {error_msg}\nData: {receipt_data}",
            title=f"eBarimt POS Failed: {pos_doc.name}"
        )
        frappe.throw(_("eBarimt receipt creation failed: {0}").format(error_msg))


def build_pos_receipt_data(pos_doc, settings, bill_type):
    """Build receipt data for POS Invoice"""
    # District code from company address or settings
    district_code = get_pos_district_code(pos_doc, settings)
    
    # Customer info
    customer_tin = None
    customer_name = pos_doc.customer_name or pos_doc.customer
    
    if bill_type == "B2B_RECEIPT":
        customer_tin = get_customer_tin(pos_doc.customer)
    
    # Build items
    stocks = []
    for item in pos_doc.items:
        tax_code = get_item_tax_code(item.item_code, settings)
        barcode = get_item_barcode(item.item_code)
        
        stocks.append({
            "code": item.item_code,
            "name": item.item_name,
            "measureUnit": item.uom or "ширхэг",
            "qty": flt(item.qty, 2),
            "unitPrice": flt(item.rate, 2),
            "totalAmount": flt(item.amount, 2),
            "cityTax": get_city_tax_amount(item, settings),
            "vat": get_vat_amount(item),
            "barCode": barcode or item.item_code
        })
    
    # Build payments from POS payment entries
    payments = build_pos_payments(pos_doc)
    
    receipt_data = {
        "amount": flt(pos_doc.grand_total, 2),
        "vat": flt(pos_doc.total_taxes_and_charges or 0, 2),
        "cashAmount": payments.get("P", 0),
        "nonCashAmount": payments.get("non_cash", 0),
        "cityTax": flt(pos_doc.get("custom_city_tax") or 0, 2),
        "districtCode": district_code,
        "posNo": settings.pos_no,
        "customerTin": customer_tin,
        "customerName": customer_name,
        "billType": bill_type,
        "stocks": stocks,
        "payments": [
            {"code": code, "amount": amount}
            for code, amount in payments.items()
            if code != "non_cash" and amount > 0
        ]
    }
    
    return receipt_data


def build_pos_payments(pos_doc):
    """Build payment breakdown from POS Invoice payments"""
    from ebarimt.integrations.mode_of_payment import get_ebarimt_payment_code
    
    payments = {"P": 0, "non_cash": 0}  # P = Cash
    
    for payment in pos_doc.payments or []:
        if payment.amount <= 0:
            continue
        
        payment_code = get_ebarimt_payment_code(payment.mode_of_payment) or "P"
        
        if payment_code in payments:
            payments[payment_code] += flt(payment.amount, 2)
        else:
            payments[payment_code] = flt(payment.amount, 2)
        
        # Track non-cash total
        if payment_code != "P":
            payments["non_cash"] += flt(payment.amount, 2)
    
    return payments


def get_pos_district_code(pos_doc, settings):
    """Get district code for POS Invoice"""
    # Try company address first
    if pos_doc.company:
        company_address = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "Company",
                "link_name": pos_doc.company,
                "parenttype": "Address"
            },
            "parent"
        )
        
        if company_address:
            district = frappe.db.get_value("Address", company_address, "custom_ebarimt_district")
            if district:
                district_code = frappe.db.get_value("eBarimt District", district, "district_code")
                if district_code:
                    return district_code
    
    # Fall back to settings
    if settings.get("default_district"):
        return frappe.db.get_value("eBarimt District", settings.default_district, "district_code")
    
    # Default district code
    return "34"  # Ulaanbaatar


def get_customer_tin(customer):
    """Get customer TIN for B2B receipt"""
    if not customer:
        return None
    
    return frappe.db.get_value("Customer", customer, "custom_taxpayer_tin")


def get_item_tax_code(item_code, settings):
    """Get eBarimt tax code for item"""
    tax_code = frappe.db.get_value("Item", item_code, "custom_ebarimt_tax_code")
    
    if tax_code:
        return frappe.db.get_value("eBarimt Tax Code", tax_code, "tax_code")
    
    # Default tax code
    if settings.get("default_tax_code"):
        return frappe.db.get_value("eBarimt Tax Code", settings.default_tax_code, "tax_code")
    
    return "VAT_ABLE"


def get_item_barcode(item_code):
    """Get barcode for item"""
    barcode = frappe.db.get_value(
        "Item Barcode",
        {"parent": item_code},
        "barcode",
        order_by="idx"
    )
    return barcode


def get_city_tax_amount(item, settings):
    """Calculate city tax amount for item"""
    # Only certain categories have city tax
    if not settings.get("enable_city_tax"):
        return 0
    
    city_tax_rate = flt(settings.get("city_tax_rate") or 0) / 100
    return flt(item.amount * city_tax_rate, 2)


def get_vat_amount(item):
    """Get VAT amount from item"""
    # VAT is typically included in price in Mongolia (10%)
    return flt(item.amount * 10 / 110, 2)


@frappe.whitelist()
def create_pos_return_receipt(pos_doc_name):
    """Create return receipt for a POS Invoice"""
    from ebarimt.api.client import EBarimtClient
    from ebarimt.ebarimt.doctype.ebarimt_receipt_log.ebarimt_receipt_log import create_receipt_log
    
    if isinstance(pos_doc_name, str):
        pos_doc = frappe.get_doc("POS Invoice", pos_doc_name)
    else:
        pos_doc = pos_doc_name
    
    if not pos_doc.is_return:
        frappe.throw(_("This is not a return invoice"))
    
    # Get original invoice
    original_invoice = pos_doc.return_against
    if not original_invoice:
        frappe.throw(_("Return against invoice not specified"))
    
    original_receipt_id = frappe.db.get_value(
        "POS Invoice", original_invoice, "custom_ebarimt_receipt_id"
    )
    
    if not original_receipt_id:
        frappe.throw(_("Original invoice has no eBarimt receipt"))
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )
    
    # Build return receipt data
    receipt_data = build_pos_receipt_data(pos_doc, settings, "B2C_RECEIPT")
    receipt_data["returnBillId"] = original_receipt_id
    
    # Submit return receipt
    response = client.create_receipt(receipt_data)
    
    if response.get("success"):
        frappe.db.set_value("POS Invoice", pos_doc.name, {
            "custom_ebarimt_receipt_id": response.get("billId"),
            "custom_ebarimt_date": response.get("date") or now_datetime()
        }, update_modified=False)
        
        create_receipt_log(pos_doc, response, "RETURN")
        
        return {
            "success": True,
            "receipt_id": response.get("billId"),
            "message": _("Return receipt created successfully")
        }
    else:
        frappe.throw(_("Return receipt creation failed: {0}").format(response.get("message")))


@frappe.whitelist()
def get_pos_receipt_status(pos_invoice_name):
    """Get eBarimt receipt status for a POS Invoice"""
    pos_doc = frappe.get_doc("POS Invoice", pos_invoice_name)
    
    if not pos_doc.get("custom_ebarimt_receipt_id"):
        return {"status": "No Receipt", "has_receipt": False}
    
    # Check receipt log
    receipt_log = frappe.db.get_value(
        "eBarimt Receipt Log",
        {"receipt_id": pos_doc.custom_ebarimt_receipt_id},
        ["status", "lottery", "creation"],
        as_dict=True
    )
    
    return {
        "status": receipt_log.status if receipt_log else "Unknown",
        "has_receipt": True,
        "receipt_id": pos_doc.custom_ebarimt_receipt_id,
        "lottery": pos_doc.get("custom_ebarimt_lottery") or (receipt_log.lottery if receipt_log else None),
        "date": pos_doc.get("custom_ebarimt_date") or (receipt_log.creation if receipt_log else None)
    }


@frappe.whitelist()
def retry_pos_receipt(pos_invoice_name):
    """Retry failed eBarimt submission for POS Invoice"""
    pos_doc = frappe.get_doc("POS Invoice", pos_invoice_name)
    
    if pos_doc.get("custom_ebarimt_receipt_id"):
        frappe.throw(_("POS Invoice already has an eBarimt receipt"))
    
    if pos_doc.docstatus != 1:
        frappe.throw(_("POS Invoice must be submitted"))
    
    try:
        response = submit_pos_ebarimt_receipt(pos_doc)
        return {
            "success": True,
            "receipt_id": response.get("billId"),
            "lottery": response.get("lottery")
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def bulk_submit_pos_receipts(invoices=None, filters=None):
    """Bulk submit eBarimt receipts for multiple POS Invoices"""
    if isinstance(invoices, str):
        import json
        invoices = json.loads(invoices)
    
    if not invoices and filters:
        if isinstance(filters, str):
            import json
            filters = json.loads(filters)
        
        # Get POS invoices without receipts
        default_filters = {
            "docstatus": 1,
            "custom_ebarimt_receipt_id": ["is", "not set"]
        }
        default_filters.update(filters or {})
        
        invoices = frappe.get_all(
            "POS Invoice",
            filters=default_filters,
            pluck="name",
            limit=100
        )
    
    results = {"success": [], "failed": []}
    
    for inv_name in invoices or []:
        try:
            pos_doc = frappe.get_doc("POS Invoice", inv_name)
            
            if pos_doc.get("custom_ebarimt_receipt_id"):
                continue
            
            if pos_doc.docstatus != 1:
                continue
            
            submit_pos_ebarimt_receipt(pos_doc)
            results["success"].append(inv_name)
            
        except Exception as e:
            results["failed"].append({
                "invoice": inv_name,
                "error": str(e)
            })
        
        # Commit after each to avoid long transactions
        frappe.db.commit()
    
    return {
        "total": len(invoices or []),
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "details": results
    }


@frappe.whitelist()
def get_pos_qr_image(pos_invoice_name):
    """Get QR code image URL for POS Invoice receipt"""
    pos_doc = frappe.get_doc("POS Invoice", pos_invoice_name)
    
    if not pos_doc.get("custom_ebarimt_qr_data"):
        return None
    
    # Return QR data for client-side rendering
    return {
        "qr_data": pos_doc.custom_ebarimt_qr_data,
        "lottery": pos_doc.get("custom_ebarimt_lottery"),
        "receipt_id": pos_doc.get("custom_ebarimt_receipt_id")
    }
