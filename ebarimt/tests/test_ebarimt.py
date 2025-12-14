# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Unit Tests for CI
"""

import unittest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestEBarimtBasic(FrappeTestCase):
    """Basic tests for eBarimt app"""

    def test_app_installed(self):
        """Test that eBarimt app is installed"""
        self.assertIn("ebarimt", frappe.get_installed_apps())

    def test_ebarimt_settings_exists(self):
        """Test eBarimt Settings DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt Settings"))

    def test_ebarimt_receipt_log_exists(self):
        """Test eBarimt Receipt Log DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt Receipt Log"))

    def test_ebarimt_payment_type_exists(self):
        """Test eBarimt Payment Type DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt Payment Type"))

    def test_ebarimt_tax_code_exists(self):
        """Test eBarimt Tax Code DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt Tax Code"))

    def test_ebarimt_oat_product_type_exists(self):
        """Test eBarimt OAT Product Type DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt OAT Product Type"))

    def test_ebarimt_district_exists(self):
        """Test eBarimt District DocType exists"""
        self.assertTrue(frappe.db.exists("DocType", "eBarimt District"))


class TestEBarimtAPI(FrappeTestCase):
    """Test eBarimt API imports"""

    def test_api_module_import(self):
        """Test that API module can be imported"""
        from ebarimt import api
        self.assertTrue(hasattr(api, "create_receipt"))
        self.assertTrue(hasattr(api, "get_taxpayer_info"))

    def test_client_import(self):
        """Test that client module can be imported"""
        from ebarimt.api.client import EBarimtClient
        self.assertTrue(callable(EBarimtClient))

    def test_client_methods(self):
        """Test client has required methods"""
        from ebarimt.api.client import EBarimtClient
        client = EBarimtClient.__new__(EBarimtClient)
        self.assertTrue(hasattr(client, "create_receipt"))
        self.assertTrue(hasattr(client, "get_taxpayer_info"))
        self.assertTrue(hasattr(client, "get_receipt_info"))
        self.assertTrue(hasattr(client, "void_receipt"))


class TestEBarimtIntegrations(FrappeTestCase):
    """Test eBarimt integrations"""

    def test_sales_invoice_integration(self):
        """Test Sales Invoice integration module"""
        from ebarimt.integrations import sales_invoice
        self.assertTrue(hasattr(sales_invoice, "validate_invoice_for_ebarimt"))
        self.assertTrue(hasattr(sales_invoice, "on_submit_invoice"))
        self.assertTrue(hasattr(sales_invoice, "build_receipt_data"))
        self.assertTrue(hasattr(sales_invoice, "get_district_code"))

    def test_pos_invoice_integration(self):
        """Test POS Invoice integration module"""
        from ebarimt.integrations import pos_invoice
        self.assertTrue(hasattr(pos_invoice, "validate_pos_invoice"))
        self.assertTrue(hasattr(pos_invoice, "on_submit_pos_invoice"))

    def test_customer_integration(self):
        """Test Customer integration module"""
        from ebarimt.integrations import customer
        self.assertTrue(hasattr(customer, "validate_customer"))
        self.assertTrue(hasattr(customer, "sync_taxpayer_info"))
        self.assertTrue(hasattr(customer, "validate_tin_format"))

    def test_item_integration(self):
        """Test Item integration module"""
        from ebarimt.integrations import item
        self.assertTrue(hasattr(item, "validate_item"))
        self.assertTrue(hasattr(item, "sync_barcode_info"))

    def test_company_integration(self):
        """Test Company integration module"""
        from ebarimt.integrations import company
        self.assertTrue(hasattr(company, "validate_company"))
        self.assertTrue(hasattr(company, "get_company_ebarimt_settings"))

    def test_payment_entry_integration(self):
        """Test Payment Entry integration module"""
        from ebarimt.integrations import payment_entry
        self.assertTrue(hasattr(payment_entry, "validate_payment_entry"))

    def test_mode_of_payment_integration(self):
        """Test Mode of Payment integration module"""
        from ebarimt.integrations import mode_of_payment
        self.assertTrue(hasattr(mode_of_payment, "validate_mode_of_payment"))


class TestEBarimtFixtures(FrappeTestCase):
    """Test eBarimt fixtures are loaded"""

    def test_payment_types_loaded(self):
        """Test Payment Types fixture loaded"""
        count = frappe.db.count("eBarimt Payment Type")
        self.assertGreater(count, 0, "Payment types should be loaded from fixtures")

    def test_oat_product_types_loaded(self):
        """Test OAT Product Types fixture loaded"""
        count = frappe.db.count("eBarimt OAT Product Type")
        self.assertGreater(count, 0, "OAT product types should be loaded from fixtures")


class TestEBarimtCustomFields(FrappeTestCase):
    """Test eBarimt custom fields"""

    def test_sales_invoice_custom_fields(self):
        """Test Sales Invoice has eBarimt custom fields"""
        fields = ["custom_ebarimt_receipt_id", "custom_ebarimt_lottery", "custom_ebarimt_qr_data"]
        for field in fields:
            exists = frappe.db.exists("Custom Field", {"dt": "Sales Invoice", "fieldname": field})
            self.assertTrue(exists, f"Custom field {field} should exist on Sales Invoice")

    def test_customer_custom_fields(self):
        """Test Customer has eBarimt custom fields"""
        exists = frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "custom_tin"})
        self.assertTrue(exists, "Custom field custom_tin should exist on Customer")

    def test_item_custom_fields(self):
        """Test Item has eBarimt custom fields"""
        fields = ["custom_ebarimt_tax_code", "custom_ebarimt_barcode"]
        for field in fields:
            exists = frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": field})
            self.assertTrue(exists, f"Custom field {field} should exist on Item")

    def test_company_custom_fields(self):
        """Test Company has eBarimt custom fields"""
        fields = ["custom_ebarimt_enabled", "custom_operator_tin"]
        for field in fields:
            exists = frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": field})
            self.assertTrue(exists, f"Custom field {field} should exist on Company")
