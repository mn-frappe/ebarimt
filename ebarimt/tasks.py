# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Scheduled Tasks for eBarimt

eBarimt app manages its own district codes via eBarimt District DocType.
This allows independent operation without QPay installed.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_years, now_datetime


def sync_tax_codes_daily():
    """Daily sync of tax codes from eBarimt"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    if not frappe.db.get_single_value("eBarimt Settings", "auto_sync_tax_codes"):
        return
    
    try:
        from ebarimt.ebarimt.doctype.ebarimt_tax_code.ebarimt_tax_code import sync_tax_codes
        result = sync_tax_codes()
        
        if result.get("success"):
            frappe.logger("ebarimt").info(
                f"Tax codes synced successfully: {result.get('count', 0)} codes"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Tax Code Sync Failed"
        )


def sync_pending_receipts_daily():
    """
    Daily sync of pending/unsent receipts to eBarimt
    Retries failed receipts from the last 7 days
    OPTIMIZED: Uses batch operations and single sendData call
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    from ebarimt.api.client import EBarimtClient
    from ebarimt.performance import bulk_update_receipt_status, get_pending_receipts_fast
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    # OPTIMIZED: Use fast SQL query
    pending_logs = get_pending_receipts_fast(limit=100, days=7)
    
    if not pending_logs:
        return
    
    client = EBarimtClient(settings=settings)
    
    try:
        # Single sendData call syncs all pending receipts
        result = client.send_data()
        
        if result.get("success"):
            # OPTIMIZED: Batch update all pending logs to Synced
            updates = {log["name"]: "Synced" for log in pending_logs}
            synced = bulk_update_receipt_status(updates)
            
            frappe.logger("ebarimt").info(
                f"Daily receipt sync: {synced} receipts potentially synced"
            )
        else:
            frappe.log_error(
                message=f"sendData failed: {result.get('message', 'Unknown error')}",
                title="eBarimt Daily Sync Failed"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Daily Sync Failed"
        )
    
    frappe.db.commit()
    
    frappe.logger("ebarimt").info(
        f"Daily receipt sync: {synced} synced, {failed} failed"
    )


def sync_unsent_receipts():
    """
    Hourly sync of unsent receipts
    Uses sendData API to push any locally stored receipts
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    from ebarimt.api.client import EBarimtClient
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )
    
    try:
        result = client.send_data()
        
        if result.get("success"):
            frappe.logger("ebarimt").info(
                f"Hourly receipt sync completed: {result.get('message', 'OK')}"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Hourly Sync Failed"
        )


def cleanup_old_failed_logs():
    """
    Daily cleanup of old failed receipt logs
    Keeps logs for 5 years as per tax requirements
    """
    cutoff_date = add_years(now_datetime(), -5)
    
    # Only delete failed logs older than 5 years
    deleted = frappe.db.delete("eBarimt Receipt Log", {
        "status": "Failed",
        "creation": ["<", cutoff_date]
    })
    
    if deleted:
        frappe.db.commit()
        frappe.logger("ebarimt").info(f"Cleaned up {deleted} old failed receipt logs")


def sync_taxpayer_info_weekly():
    """
    Weekly sync of taxpayer information for customers with TIN
    Updates VAT payer status, city tax status, etc.
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    auto_sync = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_taxpayer")
    if not auto_sync:
        return
    
    from ebarimt.integrations.customer import sync_taxpayer_info
    
    # Get customers with TIN that haven't been synced recently
    cutoff_date = add_days(now_datetime(), -30)  # Sync if not updated in 30 days
    
    customers = frappe.get_all(
        "Customer",
        filters={
            "custom_tin": ["is", "set"],
            "custom_tin": ["!=", ""],
            "modified": ["<", cutoff_date]
        },
        fields=["name"],
        limit=50
    )
    
    synced = 0
    for customer in customers:
        try:
            result = sync_taxpayer_info(customer.name)
            if result.get("success"):
                synced += 1
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Taxpayer Sync Failed: {customer.name}"
            )
    
    frappe.db.commit()
    
    if synced:
        frappe.logger("ebarimt").info(f"Weekly taxpayer sync: {synced} customers updated")


def sync_barcode_info_weekly():
    """
    Weekly sync of barcode/BUNA information for items
    Updates product names, manufacturers, tax codes
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    auto_sync = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_barcode")
    if not auto_sync:
        return
    
    from ebarimt.integrations.item import sync_barcode_info
    
    # Get items with barcode that haven't been synced recently
    cutoff_date = add_days(now_datetime(), -30)
    
    items = frappe.get_all(
        "Item",
        filters=[
            ["custom_ebarimt_barcode", "is", "set"],
            ["custom_ebarimt_barcode", "!=", ""],
            ["modified", "<", cutoff_date]
        ],
        fields=["name", "custom_ebarimt_barcode"],
        limit=50
    )
    
    synced = 0
    for item in items:
        try:
            result = sync_barcode_info(item.name, item.custom_ebarimt_barcode)
            if result.get("success"):
                synced += 1
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Barcode Sync Failed: {item.name}"
            )
    
    frappe.db.commit()
    
    if synced:
        frappe.logger("ebarimt").info(f"Weekly barcode sync: {synced} items updated")
