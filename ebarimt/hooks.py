# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt - Mongolian VAT Receipt System

Compatible with ERPNext and all ERPNext-based apps:
- ERPNext Core: Sales Invoice, POS Invoice, Payment Entry
- Healthcare: Patient Encounter billing
- Education: Student Fees
- Lending: Loan Disbursements
- Webshop: E-commerce transactions

All integrations are automatic when the respective apps are installed.
"""

app_name = "ebarimt"
app_title = "eBarimt"
app_publisher = "Digital Consulting Service LLC (Mongolia)"
app_description = (
    "eBarimt Mongolian VAT Receipt System - ERPNext Integration. "
    "Compatible with Healthcare, Education, Lending, and Webshop apps."
)
app_email = "dev@frappe.mn"
app_license = "gpl-3.0"
app_version = "1.10.0"

# Required Apps - ERPNext is required for eBarimt (Sales Invoice, Item, Customer)
required_apps = ["frappe", "erpnext"]


# =============================================================================
# App Detection for Optional Integrations
# =============================================================================
_app_cache: dict = {}


def _has_app(name: str) -> bool:
    """Check if an app is installed."""
    if name not in _app_cache:
        try:
            __import__(name)
            _app_cache[name] = True
        except ImportError:
            _app_cache[name] = False
    return _app_cache[name]


def _has_healthcare() -> bool:
    return _has_app("healthcare")


def _has_education() -> bool:
    return _has_app("education")


def _has_lending() -> bool:
    return _has_app("lending")

# App include
app_include_js = "/assets/ebarimt/js/ebarimt.bundle.js"

# DocType JS
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "POS Invoice": "public/js/pos_invoice.js",
    "Customer": "public/js/customer.js",
    "Item": "public/js/item.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Company": "public/js/company.js",
    "Mode of Payment": "public/js/mode_of_payment.js"
}

# Installation
after_install = "ebarimt.install.after_install"
before_uninstall = "ebarimt.install.before_uninstall"

# Error Reporting / Telemetry
# ---------------------------
# Reports unhandled exceptions to GitHub Issues (if enabled in settings)
exception_handler = "ebarimt.ebarimt.telemetry.on_error"

# Migration - ensure workspace links exist and districts are synced
after_migrate = [
    "ebarimt.install.add_to_integrations_workspace",
    "ebarimt.install.sync_district_codes",
    "ebarimt.performance.ensure_indexes"
]

# Fixtures - Payment Types, Tax Codes, OAT Product Types, Districts, and Custom Fields
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
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["name", "like", "Customer-custom_%"],
            ["name", "like", "Customer-ebarimt%"]
        ],
        "or_filters": [
            ["name", "like", "Item-custom_ebarimt%"],
            ["name", "like", "Item-ebarimt%"],
            ["name", "like", "Sales Invoice-custom_ebarimt%"],
            ["name", "like", "Sales Invoice-ebarimt%"],
            ["name", "like", "POS Invoice-custom_ebarimt%"],
            ["name", "like", "POS Invoice-ebarimt%"],
            ["name", "like", "Company-custom_ebarimt%"],
            ["name", "like", "Company-ebarimt%"]
        ]
    }
]

# Document Events - ERPNext Core + Optional App Integrations
# Events for Healthcare, Education, Lending are handled gracefully
# if those apps are installed
doc_events = {
    # ERPNext Core DocTypes
    "Sales Invoice": {
        "validate": "ebarimt.integrations.sales_invoice.validate_invoice_for_ebarimt",
        "on_submit": "ebarimt.integrations.sales_invoice.on_submit_invoice",
        "on_cancel": "ebarimt.integrations.sales_invoice.on_cancel_invoice"
    },
    "POS Invoice": {
        "validate": "ebarimt.integrations.pos_invoice.validate_pos_invoice",
        "on_submit": "ebarimt.integrations.pos_invoice.on_submit_pos_invoice",
        "on_cancel": "ebarimt.integrations.pos_invoice.on_cancel_pos_invoice"
    },
    "Customer": {
        "validate": "ebarimt.integrations.customer.validate_customer",
        "after_insert": "ebarimt.integrations.customer.after_insert_customer"
    },
    "Item": {
        "validate": "ebarimt.integrations.item.validate_item",
        "after_insert": "ebarimt.integrations.item.after_insert_item"
    },
    "Payment Entry": {
        "validate": "ebarimt.integrations.payment_entry.validate_payment_entry",
        "on_submit": "ebarimt.integrations.payment_entry.on_submit_payment_entry",
        "on_cancel": "ebarimt.integrations.payment_entry.on_cancel_payment_entry"
    },
    "Company": {
        "validate": "ebarimt.integrations.company.validate_company",
        "after_insert": "ebarimt.integrations.company.after_insert_company"
    },
    "Mode of Payment": {
        "validate": "ebarimt.integrations.mode_of_payment.validate_mode_of_payment"
    },
    # Healthcare App - Patient Encounter creates Sales Invoice, handled automatically
    # Education App - Fees creates Sales Invoice, handled automatically
    # Lending App - Loan creates Journal Entry/Sales Invoice, handled automatically
}

# Scheduled Tasks
# District sync handled by after_migrate hook
scheduler_events = {
    "daily": [
        "ebarimt.tasks.sync_tax_codes_daily",
        "ebarimt.tasks.sync_pending_receipts_daily",
        "ebarimt.tasks.cleanup_old_failed_logs"
    ],
    "hourly": [
        "ebarimt.tasks.sync_unsent_receipts",
        "ebarimt.performance.auto_retry_failed_receipts",
        "ebarimt.performance.auto_sync_pending_receipts"
    ],
    "weekly": [
        "ebarimt.tasks.sync_taxpayer_info_weekly",
        "ebarimt.tasks.sync_barcode_info_weekly",
        "ebarimt.performance.ensure_indexes"
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

