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
    
    frappe.db.commit()
    
    print("=" * 60)
    print("eBarimt app installed successfully!")
    print("=" * 60)
    print("Default environment: Staging")
    print("Test credentials have been configured.")
    print("Go to eBarimt Settings to test connection.")
    print("")
    print("NOTE: District codes are shared from QPay app.")
    print("Make sure QPay app is installed and districts are synced.")
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
    
    # Note: Districts are shared from QPay app - no need to load here


def before_uninstall():
    """Run before app uninstallation"""
    print("Removing eBarimt custom fields...")
    
    from ebarimt.integrations.custom_fields import delete_custom_fields
    delete_custom_fields()
    
    print("eBarimt uninstalled.")
