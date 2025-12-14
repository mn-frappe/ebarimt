# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Installation script for eBarimt app
Sets up default configuration for staging environment
"""

import frappe
from frappe import _


def after_install():
    """Run after app installation"""
    create_custom_fields()
    setup_default_settings()
    load_default_fixtures()
    setup_workspace()
    
    frappe.db.commit()
    
    print("=" * 60)
    print("eBarimt app installed successfully!")
    print("=" * 60)
    print("Default environment: Staging")
    print("Test credentials have been configured.")
    print("Go to eBarimt Settings to test connection.")
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
    # settings.api_password = "test_pass"  # Will need to be updated - skip password for now
    
    # API URLs (via proxy)
    settings.proxy_url = "https://api.frappe.mn"
    settings.fallback_ip = "103.153.141.167"
    
    # Default settings
    settings.default_bill_type = "B2C_RECEIPT"
    settings.auto_submit_receipt = 1  # Field name from JSON
    
    # Default payment type - Cash
    settings.default_payment_type = "CASH"
    
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
    
    # Load districts (default set)
    from ebarimt.ebarimt.doctype.ebarimt_district.ebarimt_district import load_default_districts
    load_default_districts()
    print("Districts loaded.")


def setup_workspace():
    """Add eBarimt to MN Settings workspace"""
    print("Setting up workspace...")
    
    # Check if MN Settings workspace exists
    if frappe.db.exists("Workspace", "MN Settings"):
        workspace = frappe.get_doc("Workspace", "MN Settings")
        
        # Check if eBarimt shortcut already exists
        existing_shortcuts = [s.link_to for s in workspace.shortcuts if s.type == "DocType"]
        
        if "eBarimt Settings" not in existing_shortcuts:
            # Add eBarimt Settings shortcut
            workspace.append("shortcuts", {
                "type": "DocType",
                "link_to": "eBarimt Settings",
                "label": "eBarimt Settings",
                "icon": "receipt",
                "color": "#4299E1"
            })
            
            workspace.flags.ignore_permissions = True
            workspace.save()
            print("Added eBarimt to MN Settings workspace.")
    else:
        # Create eBarimt workspace
        create_ebarimt_workspace()


def create_ebarimt_workspace():
    """Create eBarimt workspace if MN Settings doesn't exist"""
    if frappe.db.exists("Workspace", "eBarimt"):
        return
    
    workspace = frappe.new_doc("Workspace")
    workspace.name = "eBarimt"
    workspace.label = "eBarimt"
    workspace.module = "ebarimt"
    workspace.icon = "receipt"
    workspace.category = "Modules"
    
    # Add shortcuts
    workspace.append("shortcuts", {
        "type": "DocType",
        "link_to": "eBarimt Settings",
        "label": "Settings",
        "icon": "settings"
    })
    
    workspace.append("shortcuts", {
        "type": "DocType",
        "link_to": "eBarimt Receipt Log",
        "label": "Receipt Log",
        "icon": "file-text"
    })
    
    # Add links
    workspace.append("links", {
        "type": "DocType",
        "link_to": "eBarimt Settings",
        "label": "eBarimt Settings",
        "link_type": "DocType"
    })
    
    workspace.append("links", {
        "type": "DocType",
        "link_to": "eBarimt Receipt Log",
        "label": "Receipt Log",
        "link_type": "DocType"
    })
    
    workspace.append("links", {
        "type": "DocType",
        "link_to": "eBarimt District",
        "label": "Districts",
        "link_type": "DocType"
    })
    
    workspace.append("links", {
        "type": "DocType",
        "link_to": "eBarimt Tax Code",
        "label": "Tax Codes",
        "link_type": "DocType"
    })
    
    workspace.append("links", {
        "type": "DocType",
        "link_to": "eBarimt Payment Type",
        "label": "Payment Types",
        "link_type": "DocType"
    })
    
    workspace.flags.ignore_permissions = True
    workspace.insert()
    
    print("Created eBarimt workspace.")


def before_uninstall():
    """Run before app uninstallation"""
    print("Removing eBarimt custom fields...")
    
    from ebarimt.integrations.custom_fields import delete_custom_fields
    delete_custom_fields()
    
    print("eBarimt uninstalled.")
