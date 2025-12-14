# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

app_name = "ebarimt"
app_title = "eBarimt"
app_publisher = "Digital Consulting Service LLC (Mongolia)"
app_description = "eBarimt Mongolian VAT Receipt System - Full ERPNext Integration"
app_email = "dev@frappe.mn"
app_license = "gpl-3.0"
app_version = "1.3.0"

# Required Apps
required_apps = ["frappe", "erpnext"]

# App include
app_include_js = "/assets/ebarimt/js/ebarimt.bundle.js"

# DocType JS
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "POS Invoice": "public/js/pos_invoice.js",
    "Customer": "public/js/customer.js",
    "Item": "public/js/item.js"
}

# Installation
after_install = "ebarimt.install.after_install"
before_uninstall = "ebarimt.install.before_uninstall"

# Migration - ensure workspace links exist and districts are synced
after_migrate = [
    "ebarimt.install.add_to_integrations_workspace",
    "ebarimt.install.sync_district_codes"
]

# Fixtures - Payment Types, Tax Codes, OAT Product Types, and Districts
# eBarimt app manages its own districts independently
fixtures = [
    {
        "doctype": "eBarimt Payment Type",
        "filters": {"is_default": 1}
    },
    {
        "doctype": "eBarimt Tax Code",
        "filters": {"is_default": 1}
    },
    {
        "doctype": "eBarimt OAT Product Type",
        "filters": {"is_default": 1}
    },
    {
        "doctype": "eBarimt District"
    }
]

# Document Events
doc_events = {
    "Sales Invoice": {
        "validate": "ebarimt.integrations.sales_invoice.validate_invoice_for_ebarimt",
        "on_submit": "ebarimt.integrations.sales_invoice.on_submit_invoice",
        "on_cancel": "ebarimt.integrations.sales_invoice.on_cancel_invoice"
    },
    "POS Invoice": {
        "validate": "ebarimt.integrations.sales_invoice.validate_invoice_for_ebarimt",
        "on_submit": "ebarimt.integrations.sales_invoice.on_submit_invoice",
        "on_cancel": "ebarimt.integrations.sales_invoice.on_cancel_invoice"
    },
    "Customer": {
        "validate": "ebarimt.integrations.customer.validate_customer",
        "after_insert": "ebarimt.integrations.customer.after_insert_customer"
    },
    "Item": {
        "validate": "ebarimt.integrations.item.validate_item",
        "after_insert": "ebarimt.integrations.item.after_insert_item"
    }
}

# Scheduled Tasks
# District sync handled by after_migrate hook
scheduler_events = {
    "daily": [
        "ebarimt.tasks.sync_tax_codes_daily"
    ]
}

# Boot Session
boot_session = "ebarimt.startup.boot_session"

# Jinja Environment
jinja = {
    "methods": [
        "ebarimt.utils.jinja.get_qr_code",
        "ebarimt.utils.jinja.format_lottery_number"
    ]
}

# Notification Config
notification_config = "ebarimt.notifications.get_notification_config"

