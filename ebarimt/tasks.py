# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Scheduled Tasks for eBarimt
"""

import frappe
from frappe import _


def sync_tax_codes_daily():
    """Daily sync of tax codes from eBarimt"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
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


def sync_districts_weekly():
    """Weekly sync of district codes from eBarimt"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return
    
    try:
        from ebarimt.ebarimt.doctype.ebarimt_district.ebarimt_district import sync_districts
        result = sync_districts()
        
        if result.get("success"):
            frappe.logger("ebarimt").info(
                f"Districts synced successfully: {result.get('count', 0)} districts"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt District Sync Failed"
        )


def cleanup_old_receipt_logs():
    """
    Cleanup old receipt logs (optional - run manually or add to scheduler)
    Keeps logs for 5 years as per tax requirements
    """
    from frappe.utils import add_years, now_datetime
    
    cutoff_date = add_years(now_datetime(), -5)
    
    # Only delete failed logs, keep successful ones
    frappe.db.delete("eBarimt Receipt Log", {
        "status": "Failed",
        "creation": ["<", cutoff_date]
    })
    
    frappe.db.commit()
