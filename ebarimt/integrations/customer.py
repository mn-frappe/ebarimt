# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Customer Integration
Handles TIN lookup and synchronization
"""

import frappe
from frappe import _
from frappe.utils import cint


def validate_customer(doc, method=None):
    """Validate customer TIN if provided"""
    if not doc.get("custom_tin"):
        return
    
    tin = doc.custom_tin.strip()
    
    # Validate TIN format (should be 7-12 digits)
    if not tin.isdigit() or len(tin) < 7 or len(tin) > 12:
        frappe.throw(_("Invalid TIN format. TIN should be 7-12 digits."))


def after_insert_customer(doc, method=None):
    """Auto-lookup taxpayer info for new customers with TIN"""
    settings = frappe.db.get_single_value("eBarimt Settings", "enabled")
    
    if not settings:
        return
    
    auto_lookup = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_taxpayer")
    
    if not auto_lookup:
        return
    
    if doc.get("custom_tin") and not doc.get("custom_taxpayer_synced"):
        frappe.enqueue(
            "ebarimt.integrations.customer.sync_taxpayer_info",
            customer_name=doc.name,
            queue="short"
        )


def sync_taxpayer_info(customer_name):
    """Sync taxpayer information from eBarimt"""
    from ebarimt.api.client import EBarimtClient
    
    customer = frappe.get_doc("Customer", customer_name)
    
    if not customer.get("custom_tin"):
        return {"success": False, "message": _("No TIN provided")}
    
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
        taxpayer_info = client.get_taxpayer_info(customer.custom_tin)
        
        if taxpayer_info.get("found"):
            # Update customer with taxpayer info
            customer.db_set("custom_taxpayer_name", taxpayer_info.get("name"), update_modified=False)
            customer.db_set("custom_vat_payer", cint(taxpayer_info.get("vatPayer")), update_modified=False)
            customer.db_set("custom_city_payer", cint(taxpayer_info.get("cityPayer")), update_modified=False)
            customer.db_set("custom_taxpayer_synced", 1, update_modified=False)
            
            # Update customer name if empty
            if not customer.customer_name or customer.customer_name == customer_name:
                customer.db_set("customer_name", taxpayer_info.get("name"), update_modified=False)
            
            return {
                "success": True,
                "data": taxpayer_info
            }
        else:
            return {
                "success": False,
                "message": _("Taxpayer not found")
            }
    
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Taxpayer Sync Failed: {customer_name}"
        )
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def lookup_taxpayer(tin=None, regno=None):
    """
    Lookup taxpayer by TIN or registration number
    Can be called from Customer form
    """
    from ebarimt.api.client import EBarimtClient
    
    if not tin and not regno:
        frappe.throw(_("Please provide TIN or Registration Number"))
    
    settings = frappe.get_cached_doc("eBarimt Settings")
    
    if not settings.enabled:
        frappe.throw(_("eBarimt is not enabled"))
    
    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )
    
    if tin:
        result = client.get_taxpayer_info(tin)
    else:
        # Lookup by regno first to get TIN
        tin_result = client.get_tin_by_regno(regno)
        if tin_result.get("found"):
            result = client.get_taxpayer_info(tin_result.get("tin"))
        else:
            return {"success": False, "message": _("Registration number not found")}
    
    if result.get("found"):
        return {
            "success": True,
            "tin": result.get("tin"),
            "name": result.get("name"),
            "vat_payer": result.get("vatPayer"),
            "city_payer": result.get("cityPayer"),
            "regno": result.get("regno")
        }
    
    return {"success": False, "message": _("Taxpayer not found")}


@frappe.whitelist()
def sync_customer_from_tin(customer_name, tin):
    """Sync customer data from TIN"""
    result = lookup_taxpayer(tin=tin)
    
    if result.get("success"):
        customer = frappe.get_doc("Customer", customer_name)
        customer.custom_tin = result.get("tin")
        customer.custom_taxpayer_name = result.get("name")
        customer.custom_vat_payer = cint(result.get("vat_payer"))
        customer.custom_city_payer = cint(result.get("city_payer"))
        customer.custom_regno = result.get("regno")
        customer.custom_taxpayer_synced = 1
        
        if not customer.customer_name or customer.customer_name == "New Customer":
            customer.customer_name = result.get("name")
        
        customer.save(ignore_permissions=True)
        
        return {"success": True, "data": result}
    
    return result
