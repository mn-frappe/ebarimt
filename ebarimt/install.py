# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Installation script for eBarimt app
Sets up default configuration for staging environment
"""

import json

import frappe


def after_install():
    """Run after app installation"""
    create_custom_fields()
    setup_default_settings()
    load_default_fixtures()
    add_to_integrations_workspace()

    frappe.db.commit()

    print("=" * 60)
    print("eBarimt app installed successfully!")
    print("=" * 60)
    print("Default environment: Staging")
    print("Test credentials have been configured.")
    print("Go to eBarimt Settings to test connection.")
    print("")
    print("District codes: Loaded from eBarimt District DocType")
    print("  - eBarimt app manages its own district codes independently")
    print("=" * 60)


def create_custom_fields():
    """Create custom fields for ERPNext integration"""
    from ebarimt.integrations.custom_fields import create_custom_fields as _create_custom_fields

    print("Creating custom fields...")
    _create_custom_fields()
    print("Custom fields created.")


def setup_default_settings():
    """Setup default eBarimt Settings with staging credentials"""
    print("Setting up default eBarimt Settings...")

    # Create or update eBarimt Settings
    if frappe.db.exists("eBarimt Settings", "eBarimt Settings"):
        settings = frappe.get_doc("eBarimt Settings", "eBarimt Settings")
    else:
        settings = frappe.new_doc("eBarimt Settings")

    # Default to staging environment
    settings.enabled = 1
    settings.environment = "Staging"

    # Staging test credentials (field names from JSON)
    settings.operator_tin = "23354214778"  # TEST OPERATOR 1
    settings.pos_no = "10011702"
    settings.merchant_tin = "37900846788"  # ТЕСТИЙН ХЭРЭГЛЭГЧ 1

    # ITC OAuth credentials for staging
    settings.api_username = "test_user"  # Default test username

    # API URLs (via proxy)
    settings.proxy_url = "https://api.frappe.mn"
    settings.fallback_ip = "103.153.141.167"

    # Default settings
    settings.default_bill_type = "B2C_RECEIPT"
    settings.auto_submit_receipt = 1
    settings.auto_void_on_cancel = 1

    # Default payment type - Cash
    settings.default_payment_type = "CASH"

    # ERPNext integration
    settings.enable_erpnext_integration = 1
    settings.auto_lookup_tin = 1
    settings.auto_lookup_barcode = 1

    # Tax settings
    settings.include_city_tax = 1
    settings.auto_sync_tax_codes = 1

    # API settings
    settings.timeout = 30
    settings.max_retries = 3

    settings.flags.ignore_permissions = True
    settings.save()

    print(f"eBarimt Settings configured for {settings.environment} environment.")


def load_default_fixtures():
    """Load default fixture data"""
    print("Loading default fixtures...")

    # Load payment types
    from ebarimt.ebarimt.doctype.ebarimt_payment_type.ebarimt_payment_type import load_default_payment_types
    load_default_payment_types()
    print("Payment types loaded.")

    # Load OAT product types
    from ebarimt.ebarimt.doctype.ebarimt_oat_product_type.ebarimt_oat_product_type import (
        load_default_oat_product_types,
    )
    load_default_oat_product_types()
    print("OAT product types loaded.")

    # Load district codes (eBarimt District DocType)
    load_district_codes()

    # Note: Tax codes are synced from eBarimt API via sync_tax_codes_daily task


def load_district_codes():
    """
    Load district codes into eBarimt District DocType.

    eBarimt app manages its own district codes independently.
    This allows eBarimt to work without QPay installed.
    """
    import os

    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "ebarimt_district.json"
    )

    if not os.path.exists(fixture_path):
        print("  ⚠ District fixture file not found.")
        return

    try:
        with open(fixture_path, encoding="utf-8") as f:
            districts = json.load(f)

        created = 0
        updated = 0
        skipped = 0

        for district in districts:
            code = district.get("code")
            if not code:
                continue

            if frappe.db.exists("eBarimt District", code):
                # Check if needs update
                existing = frappe.get_doc("eBarimt District", code)
                needs_update = (
                    existing.name_mn != district.get("name_mn") or
                    existing.aimag != district.get("aimag") or
                    existing.sum != district.get("sum")
                )

                if needs_update:
                    existing.name_mn = district.get("name_mn")
                    existing.name_en = district.get("name_en", "")
                    existing.aimag = district.get("aimag")
                    existing.sum = district.get("sum")
                    existing.flags.ignore_permissions = True
                    existing.save()
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new district
                doc = frappe.new_doc("eBarimt District")
                doc.code = code
                doc.name_mn = district.get("name_mn")
                doc.name_en = district.get("name_en", "")
                doc.aimag = district.get("aimag")
                doc.sum = district.get("sum")
                doc.flags.ignore_permissions = True
                doc.insert()
                created += 1

        frappe.db.commit()
        print(f"  District codes: {created} created, {updated} updated, {skipped} unchanged")

    except Exception as e:
        print(f"  ⚠ Error loading district codes: {e}")


def before_uninstall():
    """Run before app uninstallation"""
    print("Removing eBarimt custom fields...")

    from ebarimt.integrations.custom_fields import delete_custom_fields
    delete_custom_fields()

    remove_from_integrations_workspace()

    print("eBarimt uninstalled.")


def add_to_integrations_workspace():
    """
    Add eBarimt Settings link to MN Settings section in Integrations workspace.

    Creates "MN Settings" card if it doesn't exist (for standalone installation),
    or adds to existing MN Settings card (if QPay is installed).
    """
    if not frappe.db.exists("Workspace", "Integrations"):
        return

    try:
        ws = frappe.get_doc("Workspace", "Integrations")

        # Check if MN Settings card already exists (from QPay or other MN apps)
        mn_card_exists = any(
            link.label == "MN Settings" and link.type == "Card Break"
            for link in ws.links
        )

        if not mn_card_exists:
            # Add MN Settings card break
            ws.append("links", {
                "type": "Card Break",
                "label": "MN Settings",
                "hidden": 0,
                "is_query_report": 0,
                "link_count": 0,
                "onboard": 0
            })

        # Check if eBarimt Settings link already exists
        ebarimt_link_exists = any(
            link.link_to == "eBarimt Settings" and link.type == "Link"
            for link in ws.links
        )

        if not ebarimt_link_exists:
            # Add eBarimt Settings link
            ws.append("links", {
                "type": "Link",
                "label": "eBarimt Settings",
                "link_type": "DocType",
                "link_to": "eBarimt Settings",
                "hidden": 0,
                "is_query_report": 0,
                "link_count": 0,
                "onboard": 0,
                "dependencies": "",
                "only_for": ""
            })

        # Update content JSON to include MN Settings card
        if ws.content:
            content = json.loads(ws.content)
            mn_card_in_content = any(
                item.get("data", {}).get("card_name") == "MN Settings"
                for item in content
                if item.get("type") == "card"
            )
            if not mn_card_in_content:
                # Add MN Settings card to content
                content.append({
                    "id": frappe.generate_hash(length=10),
                    "type": "card",
                    "data": {"card_name": "MN Settings", "col": 4}
                })
                ws.content = json.dumps(content)

        ws.save(ignore_permissions=True)
        frappe.db.commit()
        print("  ✓ Added eBarimt Settings to Integrations workspace (MN Settings section)")

    except Exception as e:
        print(f"  ⚠ Could not add to Integrations workspace: {e}")


def remove_from_integrations_workspace():
    """
    Remove eBarimt Settings link from Integrations workspace during uninstall.

    Only removes eBarimt-specific link, keeps MN Settings card if other apps use it.
    """
    if not frappe.db.exists("Workspace", "Integrations"):
        return

    try:
        ws = frappe.get_doc("Workspace", "Integrations")

        # Remove eBarimt Settings link
        ws.links = [
            link for link in ws.links
            if not (link.link_to == "eBarimt Settings" and link.type == "Link")
        ]

        # Check if MN Settings card has any remaining links
        mn_card_idx = None
        has_other_mn_links = False

        for idx, link in enumerate(ws.links):
            if link.label == "MN Settings" and link.type == "Card Break":
                mn_card_idx = idx
            elif mn_card_idx is not None and link.type == "Card Break":
                # Next card started, check if there were links
                break
            elif mn_card_idx is not None and link.type == "Link":
                has_other_mn_links = True

        # If no other MN links, remove the MN Settings card too
        if mn_card_idx is not None and not has_other_mn_links:
            ws.links = [
                link for link in ws.links
                if not (link.label == "MN Settings" and link.type == "Card Break")
            ]

            # Also remove from content
            if ws.content:
                content = json.loads(ws.content)
                content = [
                    item for item in content
                    if not (item.get("type") == "card" and
                           item.get("data", {}).get("card_name") == "MN Settings")
                ]
                ws.content = json.dumps(content)

        ws.save(ignore_permissions=True)
        frappe.db.commit()
        print("  ✓ Removed eBarimt Settings from Integrations workspace")

    except Exception as e:
        print(f"  ⚠ Could not remove from Integrations workspace: {e}")


def sync_district_codes():
    """
    Sync district codes on migration.

    Called by after_migrate hook to ensure districts are available.
    eBarimt app manages its own district codes independently.
    """
    import os

    # Check if we need to sync (only if empty or has fewer records)
    current_count = frappe.db.count("eBarimt District")

    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "ebarimt_district.json"
    )

    if not os.path.exists(fixture_path):
        return

    try:
        with open(fixture_path, encoding="utf-8") as f:
            districts = json.load(f)

        fixture_count = len(districts)

        # Only sync if we have fewer districts than the fixture
        if current_count >= fixture_count:
            return

        created = 0
        for district in districts:
            code = district.get("code")
            if not code:
                continue

            if not frappe.db.exists("eBarimt District", code):
                doc = frappe.new_doc("eBarimt District")
                doc.code = code
                doc.name_mn = district.get("name_mn")
                doc.name_en = district.get("name_en", "")
                doc.aimag = district.get("aimag")
                doc.sum = district.get("sum")
                doc.flags.ignore_permissions = True
                doc.insert()
                created += 1

        if created > 0:
            frappe.db.commit()
            print(f"  ✓ Synced {created} district codes")

    except Exception:
        pass  # Silent fail on migrate
