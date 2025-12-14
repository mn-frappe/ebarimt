# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Custom Fields for ERPNext Integration
"""

def get_custom_fields():
    """Return custom fields to be created during installation"""
    return {
        "Customer": [
            {
                "fieldname": "ebarimt_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "tax_id",
                "collapsible": 1
            },
            {
                "fieldname": "custom_tin",
                "label": "TIN (ТИН)",
                "fieldtype": "Data",
                "insert_after": "ebarimt_section",
                "description": "Taxpayer Identification Number"
            },
            {
                "fieldname": "custom_regno",
                "label": "Registration No (РД)",
                "fieldtype": "Data",
                "insert_after": "custom_tin",
                "description": "Company Registration Number"
            },
            {
                "fieldname": "custom_vat_payer",
                "label": "VAT Payer",
                "fieldtype": "Check",
                "insert_after": "custom_regno",
                "default": 0,
                "read_only": 1,
                "description": "Is VAT payer (synced from eBarimt)"
            },
            {
                "fieldname": "custom_city_payer",
                "label": "City Tax Payer",
                "fieldtype": "Check",
                "insert_after": "custom_vat_payer",
                "default": 0,
                "read_only": 1,
                "description": "Is city tax payer (synced from eBarimt)"
            },
            {
                "fieldname": "custom_taxpayer_name",
                "label": "Taxpayer Name (eBarimt)",
                "fieldtype": "Data",
                "insert_after": "custom_city_payer",
                "read_only": 1,
                "description": "Official taxpayer name from eBarimt"
            },
            {
                "fieldname": "custom_taxpayer_synced",
                "label": "Taxpayer Info Synced",
                "fieldtype": "Check",
                "insert_after": "custom_taxpayer_name",
                "default": 0,
                "read_only": 1,
                "hidden": 1
            },
            {
                "fieldname": "ebarimt_foreigner_section",
                "label": "Foreign Customer (VAT Refund)",
                "fieldtype": "Section Break",
                "insert_after": "custom_taxpayer_synced",
                "collapsible": 1,
                "depends_on": "custom_is_foreigner"
            },
            {
                "fieldname": "custom_is_foreigner",
                "label": "Is Foreign Customer",
                "fieldtype": "Check",
                "insert_after": "ebarimt_foreigner_section",
                "default": 0,
                "description": "Check for foreign tourists eligible for VAT refund"
            },
            {
                "fieldname": "custom_ebarimt_customer_no",
                "label": "eBarimt Customer No",
                "fieldtype": "Data",
                "insert_after": "custom_is_foreigner",
                "read_only": 1,
                "depends_on": "custom_is_foreigner",
                "description": "eBarimt customer number for foreigners"
            },
            {
                "fieldname": "custom_passport_no",
                "label": "Passport Number",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_customer_no",
                "depends_on": "custom_is_foreigner",
                "description": "Foreign passport number"
            },
            {
                "fieldname": "custom_country_code",
                "label": "Country Code",
                "fieldtype": "Data",
                "insert_after": "custom_passport_no",
                "depends_on": "custom_is_foreigner",
                "description": "ISO country code (e.g., US, CN, KR)"
            }
        ],
        "Item": [
            {
                "fieldname": "ebarimt_item_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "barcodes",
                "collapsible": 1
            },
            {
                "fieldname": "custom_ebarimt_barcode",
                "label": "eBarimt Barcode",
                "fieldtype": "Data",
                "insert_after": "ebarimt_item_section",
                "description": "Barcode for eBarimt receipt (BUNA/EAN/UPC)"
            },
            {
                "fieldname": "custom_ebarimt_tax_code",
                "label": "eBarimt Tax Code",
                "fieldtype": "Link",
                "options": "eBarimt Tax Code",
                "insert_after": "custom_ebarimt_barcode",
                "description": "Tax product code for exempt/zero-rated items"
            },
            {
                "fieldname": "custom_is_oat",
                "label": "Is OAT/Excise Product",
                "fieldtype": "Check",
                "insert_after": "custom_ebarimt_tax_code",
                "default": 0,
                "description": "Check if this is an excise product (alcohol, tobacco)"
            },
            {
                "fieldname": "custom_city_tax_applicable",
                "label": "City Tax Applicable",
                "fieldtype": "Check",
                "insert_after": "custom_is_oat",
                "default": 0,
                "description": "Check if city tax applies to this item"
            },
            {
                "fieldname": "custom_ebarimt_product_name",
                "label": "eBarimt Product Name",
                "fieldtype": "Data",
                "insert_after": "custom_city_tax_applicable",
                "read_only": 1,
                "description": "Product name from eBarimt database"
            },
            {
                "fieldname": "custom_ebarimt_manufacturer",
                "label": "eBarimt Manufacturer",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_product_name",
                "read_only": 1,
                "description": "Manufacturer from eBarimt database"
            },
            {
                "fieldname": "custom_barcode_synced",
                "label": "Barcode Synced",
                "fieldtype": "Check",
                "insert_after": "custom_ebarimt_manufacturer",
                "default": 0,
                "read_only": 1,
                "hidden": 1
            }
        ],
        "Sales Invoice": [
            {
                "fieldname": "ebarimt_invoice_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "remarks",
                "collapsible": 1
            },
            {
                "fieldname": "custom_ebarimt_bill_type",
                "label": "eBarimt Bill Type",
                "fieldtype": "Select",
                "options": "\nB2C_RECEIPT\nB2B_RECEIPT",
                "insert_after": "ebarimt_invoice_section",
                "description": "Receipt type - B2C for consumers, B2B for businesses"
            },
            {
                "fieldname": "custom_ebarimt_customer_regno",
                "label": "Customer Reg No (for Lottery)",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_bill_type",
                "description": "Customer registration number for lottery participation"
            },
            {
                "fieldname": "ebarimt_receipt_col",
                "fieldtype": "Column Break",
                "insert_after": "custom_ebarimt_customer_regno"
            },
            {
                "fieldname": "custom_ebarimt_receipt_id",
                "label": "eBarimt Receipt ID",
                "fieldtype": "Data",
                "insert_after": "ebarimt_receipt_col",
                "read_only": 1,
                "description": "Receipt ID from eBarimt (billId)"
            },
            {
                "fieldname": "custom_ebarimt_lottery",
                "label": "Lottery Number",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_receipt_id",
                "read_only": 1,
                "description": "eBarimt lottery number"
            },
            {
                "fieldname": "custom_ebarimt_qr_data",
                "label": "QR Data",
                "fieldtype": "Small Text",
                "insert_after": "custom_ebarimt_lottery",
                "read_only": 1,
                "hidden": 1,
                "description": "QR code data for receipt"
            },
            {
                "fieldname": "custom_ebarimt_date",
                "label": "eBarimt Date",
                "fieldtype": "Datetime",
                "insert_after": "custom_ebarimt_qr_data",
                "read_only": 1,
                "description": "Receipt submission date/time"
            },
            {
                "fieldname": "custom_total_vat",
                "label": "Total VAT",
                "fieldtype": "Currency",
                "insert_after": "custom_ebarimt_date",
                "read_only": 1,
                "description": "Total VAT amount for eBarimt"
            },
            {
                "fieldname": "custom_total_city_tax",
                "label": "Total City Tax",
                "fieldtype": "Currency",
                "insert_after": "custom_total_vat",
                "read_only": 1,
                "description": "Total city tax amount"
            }
        ],
        "POS Invoice": [
            {
                "fieldname": "ebarimt_pos_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "remarks",
                "collapsible": 1
            },
            {
                "fieldname": "custom_ebarimt_bill_type",
                "label": "eBarimt Bill Type",
                "fieldtype": "Select",
                "options": "\nB2C_RECEIPT\nB2B_RECEIPT",
                "insert_after": "ebarimt_pos_section",
                "default": "B2C_RECEIPT"
            },
            {
                "fieldname": "custom_ebarimt_customer_regno",
                "label": "Customer Reg No",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_bill_type"
            },
            {
                "fieldname": "ebarimt_pos_col",
                "fieldtype": "Column Break",
                "insert_after": "custom_ebarimt_customer_regno"
            },
            {
                "fieldname": "custom_ebarimt_receipt_id",
                "label": "eBarimt Receipt ID",
                "fieldtype": "Data",
                "insert_after": "ebarimt_pos_col",
                "read_only": 1
            },
            {
                "fieldname": "custom_ebarimt_lottery",
                "label": "Lottery Number",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_receipt_id",
                "read_only": 1
            },
            {
                "fieldname": "custom_ebarimt_qr_data",
                "label": "QR Data",
                "fieldtype": "Small Text",
                "insert_after": "custom_ebarimt_lottery",
                "read_only": 1,
                "hidden": 1
            }
        ],
        "Payment Entry": [
            {
                "fieldname": "ebarimt_payment_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "remarks",
                "collapsible": 1
            },
            {
                "fieldname": "custom_ebarimt_payment_code",
                "label": "eBarimt Payment Code",
                "fieldtype": "Link",
                "options": "eBarimt Payment Type",
                "insert_after": "ebarimt_payment_section",
                "description": "Payment type code for eBarimt receipt"
            }
        ],
        "Mode of Payment": [
            {
                "fieldname": "custom_ebarimt_payment_type",
                "label": "eBarimt Payment Type",
                "fieldtype": "Link",
                "options": "eBarimt Payment Type",
                "insert_after": "enabled",
                "description": "Map to eBarimt payment type"
            }
        ],
        "Company": [
            {
                "fieldname": "ebarimt_company_section",
                "label": "eBarimt",
                "fieldtype": "Section Break",
                "insert_after": "date_of_commencement",
                "collapsible": 1
            },
            {
                "fieldname": "custom_ebarimt_enabled",
                "label": "Enable eBarimt for this Company",
                "fieldtype": "Check",
                "insert_after": "ebarimt_company_section",
                "default": 0
            },
            {
                "fieldname": "custom_operator_tin",
                "label": "Operator TIN",
                "fieldtype": "Data",
                "insert_after": "custom_ebarimt_enabled",
                "depends_on": "custom_ebarimt_enabled",
                "description": "TIN for this company's eBarimt operator"
            },
            {
                "fieldname": "custom_pos_no",
                "label": "POS No",
                "fieldtype": "Data",
                "insert_after": "custom_operator_tin",
                "depends_on": "custom_ebarimt_enabled",
                "description": "POS terminal number for this company"
            },
            {
                "fieldname": "custom_merchant_tin",
                "label": "Merchant TIN",
                "fieldtype": "Data",
                "insert_after": "custom_pos_no",
                "depends_on": "custom_ebarimt_enabled",
                "description": "Merchant TIN if different from operator"
            }
        ]
    }


def create_custom_fields():
    """Create all custom fields for eBarimt integration"""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as _create_custom_fields
    
    custom_fields = get_custom_fields()
    _create_custom_fields(custom_fields)


def delete_custom_fields():
    """Delete custom fields on uninstall"""
    import frappe
    
    custom_fields = get_custom_fields()
    
    for doctype, fields in custom_fields.items():
        for field in fields:
            fieldname = field.get("fieldname")
            try:
                frappe.delete_doc("Custom Field", f"{doctype}-{fieldname}", force=True)
            except:
                pass
