# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt API Endpoints
Whitelisted API functions for frontend access
"""

import frappe
from frappe import _
from ebarimt.api.client import EBarimtClient


# =========================================================================
# Receipt Operations
# =========================================================================

@frappe.whitelist()
def create_receipt(doctype, docname):
    """Create eBarimt receipt for a document"""
    if doctype == "Sales Invoice":
        from ebarimt.integrations.sales_invoice import submit_ebarimt_receipt
        doc = frappe.get_doc(doctype, docname)
        return submit_ebarimt_receipt(doc)
    elif doctype == "POS Invoice":
        from ebarimt.integrations.pos_invoice import submit_pos_ebarimt_receipt
        doc = frappe.get_doc(doctype, docname)
        return submit_pos_ebarimt_receipt(doc)
    else:
        frappe.throw(_("Unsupported document type for eBarimt"))


@frappe.whitelist()
def get_receipt_info(receipt_id):
    """Get receipt information from eBarimt"""
    client = EBarimtClient()
    return client.get_receipt_info(receipt_id)


@frappe.whitelist()
def void_receipt(receipt_id, receipt_date=None):
    """Void an eBarimt receipt"""
    client = EBarimtClient()
    return client.void_receipt(receipt_id, receipt_date)


@frappe.whitelist()
def send_data():
    """Sync pending receipts with central eBarimt system"""
    client = EBarimtClient()
    return client.send_data()


# =========================================================================
# Taxpayer Information
# =========================================================================

@frappe.whitelist()
def get_taxpayer_info(tin):
    """Get taxpayer information by TIN"""
    client = EBarimtClient()
    return client.get_taxpayer_info(tin)


@frappe.whitelist()
def get_tin_by_regno(reg_no):
    """Get TIN from registration number"""
    client = EBarimtClient()
    return client.get_tin_by_regno(reg_no)


@frappe.whitelist()
def verify_tin(tin):
    """Verify if TIN is valid"""
    client = EBarimtClient()
    info = client.get_taxpayer_info(tin)
    return {
        "valid": info is not None,
        "info": info
    }


# =========================================================================
# Barcode & Product Info
# =========================================================================

@frappe.whitelist()
def lookup_barcode(*levels):
    """Lookup BUNA classification or barcode"""
    client = EBarimtClient()
    return client.lookup_barcode(*levels)


@frappe.whitelist()
def get_district_codes():
    """Get all district codes"""
    client = EBarimtClient()
    return client.get_district_codes()


@frappe.whitelist()
def get_tax_codes():
    """Get VAT exempt/zero-rate product codes"""
    client = EBarimtClient()
    return client.get_tax_codes()


# =========================================================================
# Consumer/Lottery Operations
# =========================================================================

@frappe.whitelist()
def lookup_consumer_by_regno(reg_no):
    """Lookup consumer by registration number"""
    client = EBarimtClient()
    return client.lookup_consumer_by_regno(reg_no)


@frappe.whitelist()
def lookup_consumer_by_phone(phone):
    """Lookup consumer by phone number"""
    client = EBarimtClient()
    return client.lookup_consumer_by_phone(phone)


@frappe.whitelist()
def approve_receipt_qr(customer_no, qr_data):
    """Approve receipt for consumer lottery"""
    client = EBarimtClient()
    return client.approve_receipt_qr(customer_no, qr_data)


# =========================================================================
# Foreign Tourist Operations
# =========================================================================

@frappe.whitelist()
def get_foreigner_info(passport_no=None, f_register=None):
    """Lookup foreign tourist by passport or F-register"""
    client = EBarimtClient()
    return client.get_foreigner_info(passport_no, f_register)


@frappe.whitelist()
def get_foreigner_by_username(username):
    """Lookup foreign tourist by eBarimt username"""
    client = EBarimtClient()
    return client.get_foreigner_by_username(username)


@frappe.whitelist()
def register_foreigner(passport_no, first_name, last_name, country_code, 
                       email=None, phone=None):
    """Register foreign tourist for VAT refund"""
    client = EBarimtClient()
    return client.register_foreigner(
        passport_no, first_name, last_name, country_code, email, phone
    )


# =========================================================================
# OAT - Excise Tax Operations
# =========================================================================

@frappe.whitelist()
def get_oat_product_info(barcode):
    """Get excise tax product information"""
    client = EBarimtClient()
    return client.get_oat_product_info(barcode)


@frappe.whitelist()
def get_oat_stock_by_qr(qr_code):
    """Get excise stamp info by QR code"""
    client = EBarimtClient()
    return client.get_oat_stock_by_qr(qr_code)


@frappe.whitelist()
def get_available_stamps(reg_no, barcode, stock_type, position_id, year, month):
    """Get available excise stamps for sale"""
    client = EBarimtClient()
    return client.get_available_stamps(
        reg_no, barcode, stock_type, position_id, year, month
    )


# =========================================================================
# Company & POS Info
# =========================================================================

@frappe.whitelist()
def get_pos_info():
    """Get current POS registration info"""
    client = EBarimtClient()
    return client.get_info()


@frappe.whitelist()
def get_bank_accounts(tin=None):
    """Get registered bank accounts"""
    client = EBarimtClient()
    return client.get_bank_accounts(tin)


# =========================================================================
# Sync Operations
# =========================================================================

@frappe.whitelist()
def sync_districts():
    """Sync district codes from eBarimt"""
    from ebarimt.install import sync_district_codes
    sync_district_codes()
    return {"success": True, "message": _("District codes synced")}


@frappe.whitelist()
def sync_tax_codes():
    """Sync tax codes from eBarimt"""
    from ebarimt.tasks import sync_tax_codes_daily
    sync_tax_codes_daily()
    return {"success": True, "message": _("Tax codes synced")}


# =========================================================================
# Receipt Status & History
# =========================================================================

@frappe.whitelist()
def get_receipt_logs(filters=None, limit=20, offset=0):
    """Get eBarimt receipt logs with filters"""
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)
    
    logs = frappe.get_all(
        "eBarimt Receipt Log",
        filters=filters or {},
        fields=[
            "name", "receipt_id", "bill_type", "status", 
            "grand_total", "lottery", "reference_doctype", 
            "reference_name", "creation"
        ],
        order_by="creation desc",
        limit_page_length=limit,
        limit_start=offset
    )
    
    total = frappe.db.count("eBarimt Receipt Log", filters=filters or {})
    
    return {
        "data": logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@frappe.whitelist()
def get_receipt_stats(company=None):
    """Get eBarimt receipt statistics"""
    filters = {}
    if company:
        filters["company"] = company
    
    total = frappe.db.count("eBarimt Receipt Log", filters)
    success = frappe.db.count("eBarimt Receipt Log", {**filters, "status": "Success"})
    failed = frappe.db.count("eBarimt Receipt Log", {**filters, "status": "Failed"})
    pending = frappe.db.count("eBarimt Receipt Log", {**filters, "status": "Pending"})
    
    total_amount = frappe.db.sql("""
        SELECT COALESCE(SUM(grand_total), 0) as total
        FROM `tabeBarimt Receipt Log`
        WHERE status = 'Success'
        {company_filter}
    """.format(
        company_filter=f"AND company = '{company}'" if company else ""
    ), as_dict=True)[0].total
    
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "total_amount": total_amount,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0
    }
