# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false

"""
eBarimt Company Integration
Multi-company support with per-company eBarimt settings
"""

import frappe
from frappe import _
from frappe.utils import cint


def validate_company(doc, method=None):
    """
    Validate company eBarimt settings
    """
    if not doc.get("custom_ebarimt_enabled"):
        return

    # Validate required fields
    if not doc.get("custom_operator_tin"):
        frappe.throw(_("Operator TIN is required when eBarimt is enabled for company"))

    # Validate TIN format
    tin = doc.custom_operator_tin.strip()
    if not tin.isdigit() or len(tin) < 7 or len(tin) > 12:
        frappe.throw(_("Invalid Operator TIN format. TIN should be 7-12 digits."))

    # POS No validation
    if doc.get("custom_pos_no"):
        pos_no = doc.custom_pos_no.strip()
        if not pos_no.isdigit() or len(pos_no) > 10:
            frappe.throw(_("Invalid POS No format. Should be digits only."))


def after_insert_company(doc, method=None):
    """
    After company insert - optionally sync company info
    """
    pass  # Reserved for future use


def get_company_ebarimt_settings(company):
    """
    Get eBarimt settings for a specific company
    Falls back to global settings if not configured
    """
    settings = frappe.get_cached_doc("eBarimt Settings")

    # Check if company has custom settings
    company_doc = frappe.get_cached_doc("Company", company)

    if company_doc.get("custom_ebarimt_enabled"):
        return {
            "enabled": True,
            "operator_tin": company_doc.custom_operator_tin or settings.operator_tin,
            "pos_no": company_doc.custom_pos_no or settings.pos_no,
            "merchant_tin": company_doc.custom_merchant_tin or settings.merchant_tin,
            "environment": settings.environment,
            "company_specific": True
        }

    # Fall back to global settings
    return {
        "enabled": settings.enabled,
        "operator_tin": settings.operator_tin,
        "pos_no": settings.pos_no,
        "merchant_tin": settings.merchant_tin,
        "environment": settings.environment,
        "company_specific": False
    }


@frappe.whitelist()
def get_company_ebarimt_info(company):
    """Get eBarimt info for a company - API endpoint"""
    return get_company_ebarimt_settings(company)


@frappe.whitelist()
def sync_company_taxpayer_info(company):
    """
    Sync company taxpayer information from eBarimt
    """
    from ebarimt.api.client import EBarimtClient

    company_doc = frappe.get_doc("Company", company)

    tin = company_doc.get("custom_operator_tin") or company_doc.get("tax_id")

    if not tin:
        return {"success": False, "message": _("No TIN configured for company")}

    settings = frappe.get_cached_doc("eBarimt Settings")

    if not settings.enabled:
        return {"success": False, "message": _("eBarimt is not enabled")}

    client = EBarimtClient(settings=settings)

    try:
        taxpayer_info = client.get_taxpayer_info(tin)

        if taxpayer_info and taxpayer_info.get("found"):
            # Update company tax_id if not set
            if not company_doc.tax_id:
                company_doc.db_set("tax_id", tin, update_modified=False)

            return {
                "success": True,
                "data": {
                    "tin": taxpayer_info.get("tin"),
                    "name": taxpayer_info.get("name"),
                    "vat_payer": taxpayer_info.get("vatPayer"),
                    "city_payer": taxpayer_info.get("cityPayer")
                }
            }
        else:
            return {"success": False, "message": _("Company TIN not found in eBarimt")}

    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Company Taxpayer Sync Failed: {company}"
        )
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def verify_company_registration(company):
    """
    Verify company is properly registered with eBarimt
    Checks POS registration status
    """
    from ebarimt.api.client import EBarimtClient

    company_settings = get_company_ebarimt_settings(company)

    if not company_settings.get("enabled"):
        return {"success": False, "message": _("eBarimt not enabled for this company")}

    settings = frappe.get_cached_doc("eBarimt Settings")

    client = EBarimtClient(settings=settings)

    try:
        pos_info = client.get_info()

        if pos_info and pos_info.get("success"):
            return {
                "success": True,
                "registered": True,
                "pos_info": {
                    "pos_no": pos_info.get("posNo"),
                    "merchant_tin": pos_info.get("merchantTin"),
                    "status": pos_info.get("status")
                }
            }
        else:
            return {
                "success": True,
                "registered": False,
                "message": _("POS not registered or inactive")
            }

    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_ebarimt_enabled_companies():
    """Get list of companies with eBarimt enabled"""
    # Companies with custom eBarimt settings
    custom_companies = frappe.get_all(
        "Company",
        filters={"custom_ebarimt_enabled": 1},
        pluck="name"
    )

    # All companies if global settings enabled and no specific company set
    settings = frappe.get_cached_doc("eBarimt Settings")

    if settings.enabled and not custom_companies:
        return frappe.get_all("Company", pluck="name")

    return custom_companies
