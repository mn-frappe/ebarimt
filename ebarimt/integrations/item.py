# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Item Integration
Handles barcode/BUNA lookup and synchronization
"""

import frappe
from frappe import _


def validate_item(doc, method=None):
    """Validate item eBarimt fields"""
    # Validate barcode format if provided
    if doc.get("custom_ebarimt_barcode"):
        barcode = doc.custom_ebarimt_barcode.strip()
        # Basic validation - alphanumeric
        if not barcode.replace("-", "").replace("_", "").isalnum():
            frappe.throw(_("Invalid eBarimt barcode format"))


def after_insert_item(doc, method=None):
    """Auto-lookup barcode info for new items"""
    settings = frappe.db.get_single_value("eBarimt Settings", "enabled")

    if not settings:
        return

    auto_lookup = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_barcode")

    if not auto_lookup:
        return

    # Check if item has a barcode
    barcode = doc.get("custom_ebarimt_barcode")
    if not barcode and doc.barcodes:
        barcode = doc.barcodes[0].barcode

    if barcode and not doc.get("custom_barcode_synced"):
        frappe.enqueue(
            "ebarimt.integrations.item.sync_barcode_info",
            item_code=doc.name,
            barcode=barcode,
            queue="short"
        )


def sync_barcode_info(item_code, barcode):
    """Sync barcode/BUNA information from eBarimt"""
    from ebarimt.api.client import EBarimtClient

    item = frappe.get_doc("Item", item_code)
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
        barcode_info = client.lookup_barcode(barcode)

        if barcode_info.get("found"):
            # Update item with barcode info
            item.db_set("custom_ebarimt_barcode", barcode, update_modified=False)
            item.db_set("custom_ebarimt_product_name", barcode_info.get("name"), update_modified=False)
            item.db_set("custom_ebarimt_manufacturer", barcode_info.get("manufacturer"), update_modified=False)
            item.db_set("custom_barcode_synced", 1, update_modified=False)

            # Set tax code if available
            if barcode_info.get("taxProductCode"):
                item.db_set("custom_ebarimt_tax_code", barcode_info.get("taxProductCode"), update_modified=False)

            return {
                "success": True,
                "data": barcode_info
            }
        else:
            return {
                "success": False,
                "message": _("Barcode not found in eBarimt database")
            }

    except Exception as e:
        frappe.log_error(
            message=str(e),
            title=f"Barcode Sync Failed: {item_code}"
        )
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def lookup_barcode(barcode):
    """
    Lookup barcode/BUNA in eBarimt database
    Returns product info if found
    """
    from ebarimt.api.client import EBarimtClient

    if not barcode:
        frappe.throw(_("Please provide a barcode"))

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

    result = client.lookup_barcode(barcode)

    if result.get("found"):
        return {
            "success": True,
            "barcode": result.get("barcode") or barcode,
            "name": result.get("name"),
            "manufacturer": result.get("manufacturer"),
            "measure_unit": result.get("measureUnit"),
            "tax_product_code": result.get("taxProductCode"),
            "is_buna": result.get("isBuna")
        }

    return {"success": False, "message": _("Barcode not found")}


@frappe.whitelist()
def sync_item_from_barcode(item_code, barcode):
    """Sync item data from barcode lookup"""
    result = lookup_barcode(barcode)

    if result.get("success"):
        item = frappe.get_doc("Item", item_code)
        item.custom_ebarimt_barcode = barcode
        item.custom_ebarimt_product_name = result.get("name")
        item.custom_ebarimt_manufacturer = result.get("manufacturer")
        item.custom_barcode_synced = 1

        if result.get("tax_product_code"):
            item.custom_ebarimt_tax_code = result.get("tax_product_code")

        item.save(ignore_permissions=True)

        return {"success": True, "data": result}

    return result


@frappe.whitelist()
def get_oat_product_info(item_code):
    """Get OAT (excise) product information for an item"""
    from ebarimt.api.client import EBarimtClient

    item = frappe.get_doc("Item", item_code)

    if not item.get("custom_is_oat"):
        return {"success": False, "message": _("Item is not marked as OAT product")}

    barcode = item.get("custom_ebarimt_barcode")
    if not barcode:
        return {"success": False, "message": _("Item has no eBarimt barcode")}

    settings = frappe.get_cached_doc("eBarimt Settings")

    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )

    result = client.get_oat_product_info(barcode)

    if result.get("found"):
        return {
            "success": True,
            "product_code": result.get("productCode"),
            "product_name": result.get("productName"),
            "capacity": result.get("capacity"),
            "alcohol_percent": result.get("alcoholPercent"),
            "excise_rate": result.get("exciseRate"),
            "available_stamps": result.get("availableStamps")
        }

    return {"success": False, "message": _("OAT product info not found")}


@frappe.whitelist()
def auto_set_item_barcode(item_code):
    """
    Auto-set eBarimt barcode from item's primary barcode
    """
    item = frappe.get_doc("Item", item_code)

    if item.get("custom_ebarimt_barcode"):
        return {"success": True, "barcode": item.custom_ebarimt_barcode}

    # Get first barcode from item
    if item.barcodes:
        barcode = item.barcodes[0].barcode
        item.db_set("custom_ebarimt_barcode", barcode, update_modified=False)
        return {"success": True, "barcode": barcode}

    return {"success": False, "message": _("No barcode found on item")}


@frappe.whitelist()
def bulk_sync_item_barcodes(items=None):
    """
    Bulk sync barcode info for multiple items
    """
    if items:
        if isinstance(items, str):
            import json
            items = json.loads(items)
    else:
        # Get items with barcode but not synced
        items = frappe.get_all(
            "Item",
            filters={
                "custom_ebarimt_barcode": ["is", "set"],
                "custom_barcode_synced": 0
            },
            pluck="name",
            limit=100
        )

    synced = 0
    failed = 0

    for item_code in items:
        item = frappe.get_doc("Item", item_code)
        barcode = item.get("custom_ebarimt_barcode")

        if barcode:
            try:
                result = sync_barcode_info(item_code, barcode)
                if result.get("success"):
                    synced += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    frappe.db.commit()

    return {
        "success": True,
        "synced": synced,
        "failed": failed
    }


@frappe.whitelist()
def get_buna_classification(barcode):
    """
    Get full BUNA classification for a barcode
    Returns product category, classification code, etc.
    """
    from ebarimt.api.client import EBarimtClient

    settings = frappe.get_cached_doc("eBarimt Settings")

    if not settings.enabled:
        return {"success": False, "message": _("eBarimt is not enabled")}

    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )

    result = client.lookup_barcode(barcode)

    if result.get("found"):
        return {
            "success": True,
            "barcode": result.get("barcode"),
            "name": result.get("name"),
            "manufacturer": result.get("manufacturer"),
            "measure_unit": result.get("measureUnit"),
            "classification_code": result.get("classificationCode"),
            "classification_name": result.get("classificationName"),
            "tax_product_code": result.get("taxProductCode"),
            "is_buna": result.get("isBuna"),
            "barcode_type": result.get("barcodeType")  # GS1, ISBN, UNDEFINED
        }

    return {"success": False, "message": _("Barcode not found in BUNA database")}


@frappe.whitelist()
def auto_map_tax_code(item_code):
    """
    Auto-map eBarimt tax code based on item properties
    """
    item = frappe.get_doc("Item", item_code)

    # Check if already has tax code
    if item.get("custom_ebarimt_tax_code"):
        return {"success": True, "tax_code": item.custom_ebarimt_tax_code}

    # Logic to determine tax code based on item properties
    tax_code = None

    # Check item tax template for VAT exemption
    if item.taxes:
        for tax in item.taxes:
            template = frappe.get_cached_doc("Item Tax Template", tax.item_tax_template)
            for row in template.taxes:
                if row.tax_rate == 0:
                    # Zero-rated - find matching tax code
                    tax_code = frappe.db.get_value(
                        "eBarimt Tax Code",
                        {"code_type": "VAT_ZERO"},
                        "name"
                    )
                    break

    if tax_code:
        item.db_set("custom_ebarimt_tax_code", tax_code, update_modified=False)
        return {"success": True, "tax_code": tax_code}

    return {"success": False, "message": _("Could not determine tax code automatically")}
