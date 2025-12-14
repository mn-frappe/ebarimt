# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportAttributeAccessIssue=false, reportIndexIssue=false

"""
eBarimt API Endpoints
Whitelisted API functions for frontend access
"""

import frappe
from frappe import _
from frappe.utils import flt
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
def get_receipt_stats():
    """Get eBarimt receipt statistics"""
    total = frappe.db.count("eBarimt Receipt Log")
    success = frappe.db.count("eBarimt Receipt Log", {"status": "Success"})
    failed = frappe.db.count("eBarimt Receipt Log", {"status": "Failed"})
    pending = frappe.db.count("eBarimt Receipt Log", {"status": "Pending"})
    
    result = frappe.db.sql("""
        SELECT COALESCE(SUM(total_amount), 0) as total
        FROM `tabeBarimt Receipt Log`
        WHERE status = 'Success'
    """, as_dict=True)
    total_amount = result[0].get("total", 0) if result else 0
    
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "total_amount": total_amount,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0
    }


# =========================================================================
# Product Code Operations
# =========================================================================

@frappe.whitelist()
def sync_product_codes(file_path=None):
    """
    Sync GS1 product codes from Excel file.
    
    Args:
        file_path: Path to QPayAPIv2.xlsx file (optional, defaults to /opt/docs/QPayAPIv2.xlsx)
    
    Returns:
        dict with import statistics
    """
    from ebarimt.ebarimt.doctype.ebarimt_product_code.import_gs1_codes import sync_product_codes as do_sync
    return do_sync(file_path)


@frappe.whitelist()
def load_default_product_codes():
    """Load commonly used product codes with correct tax settings."""
    from ebarimt.ebarimt.doctype.ebarimt_product_code.import_gs1_codes import load_default_product_codes as do_load
    return do_load()


@frappe.whitelist()
def get_product_tax_info(classification_code):
    """
    Get tax information for a product by classification code.
    
    Args:
        classification_code: GS1 classification code
    
    Returns:
        dict with vat_type, vat_rate, city_tax_applicable, excise_type
    """
    from ebarimt.ebarimt.doctype.ebarimt_product_code.ebarimt_product_code import get_product_tax_info as get_tax
    return get_tax(classification_code)


@frappe.whitelist()
def calculate_item_taxes(amount, classification_code=None):
    """
    Calculate taxes for an item amount.
    
    Args:
        amount: Item amount (includes VAT)
        classification_code: GS1 product code (optional)
    
    Returns:
        dict with net_amount, vat_amount, city_tax_amount, total_amount
    """
    from ebarimt.ebarimt.doctype.ebarimt_product_code.ebarimt_product_code import calculate_item_taxes as calc_taxes
    return calc_taxes(flt(amount), classification_code)


# =========================================================================
# Unified Product Code Operations (for QPay integration)
# =========================================================================

@frappe.whitelist()
def get_unified_product_code(code):
    """
    Get product code from eBarimt (preferred) or QPay.
    
    This is the unified API for both apps.
    eBarimt is preferred because it has tax configuration.
    
    Args:
        code: Product classification code (GS1)
    
    Returns:
        dict: Product code info with source
    """
    from ebarimt.integrations.unified_product_codes import get_product_code
    return get_product_code(code)


@frappe.whitelist()
def search_unified_product_codes(query, limit=20):
    """
    Search product codes from both eBarimt and QPay.
    
    Args:
        query: Search string
        limit: Max results
    
    Returns:
        list: Matching product codes with source
    """
    from ebarimt.integrations.unified_product_codes import search_product_codes
    return search_product_codes(query, limit)


@frappe.whitelist()
def sync_with_qpay():
    """
    Bidirectional sync between eBarimt and QPay product codes.
    
    Ensures both apps have the same codes without duplication.
    
    Returns:
        dict: Sync results
    """
    from ebarimt.integrations.unified_product_codes import sync_product_codes
    return sync_product_codes()


@frappe.whitelist()
def get_item_tax_info(item_code):
    """
    Get complete tax information for an Item.
    
    Args:
        item_code: Item code
    
    Returns:
        dict: Tax info (vat_type, vat_rate, city_tax_rate, excise_type)
    """
    from ebarimt.integrations.unified_product_codes import get_tax_info_for_item
    return get_tax_info_for_item(item_code)


@frappe.whitelist()
def create_items_from_product_codes(force=False):
    """
    Create ERPNext Items from eBarimt Product Codes.
    
    Avoids duplicates by checking existing Items globally.
    Links Items to eBarimt Product Code via custom field.
    
    Args:
        force: If True, update existing items
    
    Returns:
        dict: Import statistics
    """
    from ebarimt.ebarimt.doctype.ebarimt_product_code.import_gs1_codes import create_items_from_product_codes as do_create
    if isinstance(force, str):
        force = force.lower() == "true"
    return do_create(force)


@frappe.whitelist()
def sync_product_codes_to_qpay():
    """
    Sync eBarimt Product Codes to QPay Product Code DocType.
    
    Ensures QPay has the same codes with tax info from eBarimt.
    
    Returns:
        dict: Sync statistics
    """
    from ebarimt.ebarimt.doctype.ebarimt_product_code.import_gs1_codes import sync_to_qpay
    return sync_to_qpay()


@frappe.whitelist()
def import_all_gs1_codes():
    """
    Import ALL GS1 codes from QPayAPIv2.xlsx (4500+ codes).
    
    This imports all hierarchy levels:
    - Segment (2 digit): 70 codes
    - Family (3 digit): 289 codes
    - Class (4 digit): 462 codes
    - SubBrick (5 digit): 234 codes -> mapped to Brick
    - Brick (6 digit): 3499 codes
    
    Returns:
        dict: Import statistics
    """
    import json
    import os
    
    # First extract codes from Excel if JSON doesn't exist
    json_path = '/tmp/all_gs1_codes.json'
    if not os.path.exists(json_path):
        _extract_gs1_from_excel(json_path)
    
    # Load extracted codes
    with open(json_path, 'r', encoding='utf-8') as f:
        all_codes = json.load(f)
    
    # Get existing codes
    existing = set(frappe.get_all("eBarimt Product Code", pluck="classification_code"))
    
    # Map SubBrick to Brick for code_level
    level_map = {'SubBrick': 'Brick'}
    
    created = 0
    skipped = 0
    
    for code_info in all_codes:
        code = code_info['code']
        level = level_map.get(code_info['level'], code_info['level'])
        
        if code in existing:
            skipped += 1
            continue
        
        try:
            doc = frappe.new_doc("eBarimt Product Code")
            doc.classification_code = code
            doc.name_mn = code_info['name']
            doc.code_level = level
            doc.vat_type = "STANDARD"
            doc.enabled = 1
            
            if code_info.get('segment_code'):
                doc.segment_code = code_info['segment_code']
                doc.segment_name = code_info.get('segment_name')
            if code_info.get('family_code'):
                doc.family_code = code_info['family_code']
                doc.family_name = code_info.get('family_name')
            if code_info.get('class_code'):
                doc.class_code = code_info['class_code']
                doc.class_name = code_info.get('class_name')
            if level == 'Brick':
                doc.brick_code = code
                doc.brick_name = code_info['name']
            
            doc.insert(ignore_permissions=True)
            created += 1
            existing.add(code)
            
            if created % 500 == 0:
                frappe.db.commit()
                
        except Exception:
            pass
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "created": created,
        "skipped": skipped,
        "total_in_file": len(all_codes),
        "total_in_db": frappe.db.count("eBarimt Product Code")
    }


def _extract_gs1_from_excel(output_path):
    """Extract all GS1 codes from QPayAPIv2.xlsx to JSON."""
    import pandas as pd
    import json
    
    df = pd.read_excel("/opt/docs/QPayAPIv2.xlsx", sheet_name="GS1")
    
    all_codes = []
    current_segment = current_segment_name = None
    current_family = current_family_name = None
    current_class = current_class_name = None
    
    for idx, row in df.iterrows():
        if idx < 2:
            continue
        
        col1 = row.get('Unnamed: 1')
        col2 = row.get('Unnamed: 2')
        col3 = row.get('Unnamed: 3')
        col4 = row.get('Unnamed: 4')
        col5 = row.get('Unnamed: 5')
        col6 = row.get('Unnamed: 6')
        
        name = str(col6).strip() if pd.notna(col6) else None
        if not name or name == 'nan':
            continue
        
        code_info = None
        
        if pd.notna(col5):
            try:
                code = str(int(float(col5))).zfill(6)
                code_info = {'code': code, 'name': name, 'level': 'Brick'}
            except: pass
        elif pd.notna(col4):
            try:
                code = str(int(float(col4))).zfill(5)
                code_info = {'code': code, 'name': name, 'level': 'SubBrick'}
            except: pass
        elif pd.notna(col3):
            try:
                code = str(int(float(col3))).zfill(4)
                current_class = code
                current_class_name = name
                code_info = {'code': code, 'name': name, 'level': 'Class'}
            except: pass
        elif pd.notna(col2):
            try:
                code = str(int(float(col2))).zfill(3)
                current_family = code
                current_family_name = name
                current_class = None
                code_info = {'code': code, 'name': name, 'level': 'Family'}
            except: pass
        elif pd.notna(col1):
            try:
                code = str(int(float(col1))).zfill(2)
                current_segment = code
                current_segment_name = name
                current_family = current_class = None
                code_info = {'code': code, 'name': name, 'level': 'Segment'}
            except: pass
        
        if code_info:
            code_info['segment_code'] = current_segment
            code_info['segment_name'] = current_segment_name
            code_info['family_code'] = current_family
            code_info['family_name'] = current_family_name
            code_info['class_code'] = current_class
            code_info['class_name'] = current_class_name
            all_codes.append(code_info)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_codes, f, ensure_ascii=False)
