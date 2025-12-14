# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Sales Invoice Integration
Handles automatic receipt submission on Sales Invoice submission
"""

import frappe
from frappe import _
from frappe.utils import flt, cint, now_datetime, getdate

def validate_invoice_for_ebarimt(doc, method=None):
    """Validate Sales Invoice for eBarimt requirements"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    # Skip if already has receipt
    if doc.get("custom_ebarimt_receipt_id"):
        return
    
    # Skip if returns - will need different handling
    if doc.is_return:
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Validate customer TIN for B2B
    bill_type = doc.get("custom_ebarimt_bill_type") or settings.default_bill_type or "B2C_RECEIPT"
    
    if bill_type == "B2B_RECEIPT":
        customer_tin = get_customer_tin(doc.customer)
        if not customer_tin:
            frappe.throw(_("Customer TIN is required for B2B receipts. Please set TIN in Customer master."))


def on_submit_invoice(doc, method=None):
    """Auto-submit eBarimt receipt on Sales Invoice submission"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # Check if auto-submit is enabled
    if not settings.auto_submit_on_invoice:
        return
    
    # Skip if already has receipt (from eBarimt app)
    if doc.get("custom_ebarimt_receipt_id"):
        frappe.msgprint(_("eBarimt receipt already exists for this invoice"))
        return
    
    # Skip if QPay app already handled eBarimt (if setting enabled)
    # QPay creates eBarimt via its own API and stores it in QPay Invoice
    if settings.get("skip_if_qpay_ebarimt") and has_qpay_ebarimt(doc):
        return
    
    # Skip credit notes / returns for now
    if doc.is_return:
        frappe.msgprint(_("Return receipts need to be processed separately via eBarimt Settings"))
        return
    
    # Queue the receipt submission
    try:
        submit_ebarimt_receipt(doc)
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"eBarimt Submit Failed: {doc.name}"
        )
        frappe.msgprint(
            _("eBarimt receipt submission failed: {0}").format(str(e)),
            indicator="red"
        )


def has_qpay_ebarimt(doc):
    """
    Check if QPay app already created eBarimt for this invoice.
    
    QPay app creates eBarimt via QPay's API (ebarimt_v3/create) when payment is received.
    This prevents duplicate eBarimt receipts when both apps are installed.
    
    Returns:
        bool: True if QPay already handled eBarimt for this invoice
    """
    # Check if QPay Invoice DocType exists (QPay app installed)
    if not frappe.db.exists("DocType", "QPay Invoice"):
        return False
    
    # Check if there's a QPay Invoice with eBarimt for this Sales Invoice
    # QPay uses 'payment_status' for payment state and 'ebarimt_created' as checkbox
    qpay_invoice = frappe.db.get_value(
        "QPay Invoice",
        {
            "reference_doctype": "Sales Invoice",
            "reference_name": doc.name,
        },
        ["name", "ebarimt_id", "ebarimt_created", "payment_status"],
        as_dict=True
    )
    
    if qpay_invoice and qpay_invoice.get("ebarimt_created") and qpay_invoice.get("ebarimt_id"):
        frappe.msgprint(
            _("eBarimt already created via QPay (ID: {0})").format(qpay_invoice.ebarimt_id),
            indicator="blue"
        )
        return True
    
    return False


def submit_ebarimt_receipt(invoice_doc):
    """Submit eBarimt receipt for a Sales Invoice"""
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
    bill_type = invoice_doc.get("custom_ebarimt_bill_type") or settings.default_bill_type or "B2C_RECEIPT"
    
    # Build receipt data
    receipt_data = build_receipt_data(invoice_doc, settings, bill_type)
    
    # Submit receipt
    response = client.create_receipt(receipt_data)
    
    if response.get("success"):
        # Update invoice with receipt info
        frappe.db.set_value("Sales Invoice", invoice_doc.name, {
            "custom_ebarimt_receipt_id": response.get("billId"),
            "custom_ebarimt_lottery": response.get("lottery"),
            "custom_ebarimt_qr_data": response.get("qrData"),
            "custom_ebarimt_date": response.get("date") or now_datetime()
        }, update_modified=False)
        
        # Create receipt log
        create_receipt_log(invoice_doc, response, bill_type)
        
        frappe.msgprint(
            _("eBarimt receipt submitted successfully. Lottery: {0}").format(
                response.get("lottery") or "N/A"
            ),
            indicator="green"
        )
    else:
        # Log failure
        log = frappe.new_doc("eBarimt Receipt Log")
        log.sales_invoice = invoice_doc.name
        log.environment = settings.environment
        log.bill_type = bill_type
        log.status = "Failed"
        log.error_message = response.get("message") or str(response)
        log.request_data = frappe.as_json(receipt_data)
        log.response_data = frappe.as_json(response)
        log.flags.ignore_permissions = True
        log.insert()
        
        frappe.throw(
            _("eBarimt receipt failed: {0}").format(response.get("message"))
        )


def build_receipt_data(invoice_doc, settings, bill_type):
    """Build receipt data from Sales Invoice"""
    from ebarimt.ebarimt.doctype.ebarimt_tax_code.ebarimt_tax_code import get_tax_type_for_item
    from ebarimt.ebarimt.doctype.ebarimt_payment_type.ebarimt_payment_type import get_payment_type_code
    
    # Get customer info
    customer_tin = ""
    customer_regno = ""
    
    if bill_type == "B2B_RECEIPT":
        customer_tin = get_customer_tin(invoice_doc.customer)
        customer_regno = get_customer_regno(invoice_doc.customer)
    
    # Build items (stocks)
    stocks = []
    for item in invoice_doc.items:
        item_data = build_item_data(item, settings)
        stocks.append(item_data)
    
    # Calculate taxes
    total_vat = flt(invoice_doc.get("custom_total_vat") or calculate_vat(invoice_doc), 2)
    total_city_tax = flt(invoice_doc.get("custom_total_city_tax") or 0, 2)
    
    # Build payments
    payments = build_payment_data(invoice_doc, settings)
    
    # Get district code
    district_code = settings.default_district or ""
    
    # Build receipt payload
    receipt = {
        "amount": flt(invoice_doc.grand_total, 2),
        "vat": total_vat,
        "cityTax": total_city_tax,
        "districtCode": district_code,
        "branchNo": settings.branch_no or "",
        "billType": bill_type.replace("_RECEIPT", "").replace("_", " "),
        "stocks": stocks,
        "payments": payments,
        "reportMonth": getdate(invoice_doc.posting_date).strftime("%Y%m")
    }
    
    # Add customer info for B2B
    if bill_type == "B2B_RECEIPT":
        receipt["customerTin"] = customer_tin
        if customer_regno:
            receipt["customerRegno"] = customer_regno
    
    # Add lottery info for B2C if customer wants lottery
    if bill_type == "B2C_RECEIPT" and invoice_doc.get("custom_ebarimt_customer_regno"):
        receipt["merchantId"] = settings.pos_no
        receipt["registerNo"] = invoice_doc.get("custom_ebarimt_customer_regno")
    
    return receipt


def build_item_data(item, settings):
    """Build item/stock data for receipt"""
    from ebarimt.ebarimt.doctype.ebarimt_tax_code.ebarimt_tax_code import get_tax_type_for_item
    
    # Get item details
    item_doc = frappe.get_cached_doc("Item", item.item_code)
    
    # Get barcode/code
    barcode = item_doc.get("custom_ebarimt_barcode") or ""
    if not barcode and item_doc.barcodes:
        barcode = item_doc.barcodes[0].barcode
    
    # Get tax type
    tax_code = item_doc.get("custom_ebarimt_tax_code") or ""
    tax_type = get_tax_type_for_item(item.item_code) if tax_code else "VAT_ABLE"
    
    # Calculate item VAT
    item_rate = flt(item.rate, 2)
    item_amount = flt(item.amount, 2)
    
    if tax_type == "VAT_ABLE":
        # VAT is 10% of amount
        item_vat = flt(item_amount * 0.1 / 1.1, 2)
    else:
        item_vat = 0
    
    # City tax (2% if applicable)
    item_city_tax = 0
    if item_doc.get("custom_city_tax_applicable"):
        item_city_tax = flt(item_amount * 0.02, 2)
    
    stock_data = {
        "code": barcode or item.item_code,
        "name": item.item_name,
        "measureUnit": item.uom or "ш",
        "qty": flt(item.qty, 3),
        "unitPrice": item_rate,
        "totalAmount": item_amount,
        "vat": item_vat,
        "cityTax": item_city_tax,
        "barCode": barcode
    }
    
    # Add tax product code if exempt/zero
    if tax_code and tax_type != "VAT_ABLE":
        stock_data["taxProductCode"] = tax_code
    
    return stock_data


def build_payment_data(invoice_doc, settings):
    """Build payment data from Sales Invoice"""
    payments = []
    
    # Check if there are linked Payment Entries
    payment_entries = get_linked_payments(invoice_doc.name)
    
    if payment_entries:
        for pe in payment_entries:
            payment_code = pe.get("custom_ebarimt_payment_code") or "P0001"  # Default to cash
            payments.append({
                "code": payment_code,
                "status": "PAID",
                "paidAmount": flt(pe.allocated_amount, 2),
                "date": pe.posting_date.strftime("%Y-%m-%d") if pe.posting_date else ""
            })
    else:
        # No linked payments - use invoice payment method or default to cash
        default_payment = settings.default_payment_type or "P0001"
        payments.append({
            "code": default_payment,
            "status": "PAID",
            "paidAmount": flt(invoice_doc.grand_total, 2),
            "date": invoice_doc.posting_date.strftime("%Y-%m-%d")
        })
    
    return payments


def get_linked_payments(invoice_name):
    """Get Payment Entries linked to Sales Invoice"""
    return frappe.db.sql("""
        SELECT pe.name, pe.posting_date, per.allocated_amount, pe.custom_ebarimt_payment_code
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON per.parent = pe.name
        WHERE per.reference_name = %s
        AND pe.docstatus = 1
    """, invoice_name, as_dict=True)


def get_customer_tin(customer_name):
    """Get TIN from Customer"""
    return frappe.db.get_value("Customer", customer_name, "custom_tin") or ""


def get_customer_regno(customer_name):
    """Get Registration Number from Customer"""
    return frappe.db.get_value("Customer", customer_name, "custom_regno") or ""


def calculate_vat(invoice_doc):
    """Calculate total VAT from invoice"""
    # Try to get from tax table
    for tax in invoice_doc.get("taxes", []):
        if "VAT" in (tax.account_head or "").upper() or "НӨАТ" in (tax.account_head or "").upper():
            return flt(tax.tax_amount, 2)
    
    # Default: Calculate 10% VAT on VAT-able items
    total_vat = 0
    for item in invoice_doc.items:
        item_doc = frappe.get_cached_doc("Item", item.item_code)
        tax_code = item_doc.get("custom_ebarimt_tax_code") or ""
        
        # Only VAT for items without exempt code
        if not tax_code:
            total_vat += flt(item.amount * 0.1 / 1.1, 2)
    
    return total_vat


@frappe.whitelist()
def manual_submit_receipt(invoice_name):
    """Manually submit eBarimt receipt for an invoice"""
    invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
    
    if invoice_doc.docstatus != 1:
        frappe.throw(_("Invoice must be submitted first"))
    
    if invoice_doc.get("custom_ebarimt_receipt_id"):
        frappe.throw(_("eBarimt receipt already exists for this invoice"))
    
    submit_ebarimt_receipt(invoice_doc)
    
    return {"success": True}


@frappe.whitelist()
def void_invoice_receipt(invoice_name):
    """Void eBarimt receipt for an invoice"""
    from ebarimt.ebarimt.doctype.ebarimt_receipt_log.ebarimt_receipt_log import get_receipt_for_invoice
    
    invoice_doc = frappe.get_doc("Sales Invoice", invoice_name)
    
    if not invoice_doc.get("custom_ebarimt_receipt_id"):
        frappe.throw(_("No eBarimt receipt found for this invoice"))
    
    # Get receipt log
    receipt_log = get_receipt_for_invoice(invoice_name)
    
    if receipt_log:
        log_doc = frappe.get_doc("eBarimt Receipt Log", receipt_log.name)
        result = log_doc.void_receipt()
        
        if result.get("success"):
            # Clear invoice receipt info
            frappe.db.set_value("Sales Invoice", invoice_name, {
                "custom_ebarimt_receipt_id": "",
                "custom_ebarimt_lottery": "",
                "custom_ebarimt_qr_data": ""
            }, update_modified=False)
            
            return {"success": True}
        else:
            return result
    
    frappe.throw(_("Receipt log not found"))


def on_cancel_invoice(doc, method=None):
    """Handle Sales Invoice cancellation - void receipt if exists"""
    if not doc.get("custom_ebarimt_receipt_id"):
        return
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    if settings.auto_void_on_cancel:
        try:
            void_invoice_receipt(doc.name)
            frappe.msgprint(_("eBarimt receipt voided"), indicator="green")
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"eBarimt Void Failed: {doc.name}"
            )
            frappe.msgprint(
                _("Warning: eBarimt receipt could not be voided automatically. Please void manually."),
                indicator="orange"
            )
