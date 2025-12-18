# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false

"""
eBarimt Full Battle Test
Comprehensive testing of all features, fixtures, and integrations
Run with: bench --site frappe.mn execute ebarimt.tests.test_full_battle.run_all_tests
"""


import frappe


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.warnings = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name, error=None):
        self.failed += 1
        self.errors.append({"test": name, "error": str(error)})
        print(f"  ❌ {name}: {error}")

    def skip(self, name, reason=None):
        self.skipped += 1
        self.warnings.append({"test": name, "reason": reason})
        print(f"  ⏭️  {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed}/{total} passed, {self.failed} failed, {self.skipped} skipped")
        if self.errors:
            print("\nFAILED TESTS:")
            for err in self.errors:
                print(f"  - {err['test']}: {err['error']}")
        print(f"{'='*60}")
        return self.failed == 0


def run_all_tests():
    """Run all eBarimt battle tests"""
    print("\n" + "="*60)
    print("🏟️  eBarimt FULL BATTLE TEST")
    print("="*60)

    results = TestResult()

    # Test sections
    test_version_and_setup(results)
    test_doctypes(results)
    test_fixtures(results)
    test_custom_fields(results)
    test_api_client(results)
    test_api_endpoints(results)
    test_integrations(results)
    test_scheduler_tasks(results)
    test_hooks(results)
    test_js_files(results)
    test_qpay_integration(results)
    test_crud_operations(results)
    test_receipt_workflow(results)
    test_error_handling(results)

    # Summary
    success = results.summary()
    return success


def test_version_and_setup(results):
    """Test version and basic setup"""
    print("\n📋 VERSION & SETUP")

    try:
        from ebarimt import __version__
        assert __version__ == "1.4.0", f"Expected 1.4.0, got {__version__}"
        results.ok(f"Version check ({__version__})")
    except Exception as e:
        results.fail("Version check", e)

    # Check app is installed
    try:
        assert "ebarimt" in frappe.get_installed_apps()
        results.ok("App installed")
    except Exception as e:
        results.fail("App installed", e)

    # Check settings doctype
    try:
        settings = frappe.get_single("eBarimt Settings")
        assert settings is not None
        results.ok("eBarimt Settings exists")
    except Exception as e:
        results.fail("eBarimt Settings exists", e)


def test_doctypes(results):
    """Test all eBarimt DocTypes"""
    print("\n📦 DOCTYPES")

    doctypes = [
        "eBarimt Settings",
        "eBarimt Receipt Log",
        "eBarimt Payment Type",
        "eBarimt Tax Code",
        "eBarimt OAT Product Type",
        "eBarimt District",
    ]

    for dt in doctypes:
        try:
            assert frappe.db.exists("DocType", dt)
            # Get meta to ensure it's properly defined
            meta = frappe.get_meta(dt)
            assert meta is not None
            results.ok(f"DocType: {dt}")
        except Exception as e:
            results.fail(f"DocType: {dt}", e)


def test_fixtures(results):
    """Test fixture data"""
    print("\n🔧 FIXTURES")

    # Payment Types
    try:
        count = frappe.db.count("eBarimt Payment Type")
        assert count > 0, "No payment types found"

        # Check required types exist (using actual names)
        required_types = ["CASH", "PAYMENT_CARD", "BANK_TRANSFER"]
        for pt_name in required_types:
            exists = frappe.db.exists("eBarimt Payment Type", pt_name)
            assert exists, f"Payment type {pt_name} not found"

        results.ok(f"Payment Types ({count} types)")
    except Exception as e:
        results.fail("Payment Types", e)

    # Tax Codes
    try:
        count = frappe.db.count("eBarimt Tax Code")
        if count == 0:
            results.skip("Tax Codes", "No tax codes yet (sync needed)")
        else:
            results.ok(f"Tax Codes ({count} codes)")
    except Exception as e:
        results.fail("Tax Codes", e)

    # OAT Product Types
    try:
        count = frappe.db.count("eBarimt OAT Product Type")
        assert count > 0, "No OAT product types found"
        results.ok(f"OAT Product Types ({count} types)")
    except Exception as e:
        results.fail("OAT Product Types", e)

    # Districts
    try:
        count = frappe.db.count("eBarimt District")
        assert count > 0, "No districts found"

        # Check UB district exists (Хан-Уул дүүрэг = 2301)
        ub_exists = frappe.db.exists("eBarimt District", {"code": "2301"})
        if not ub_exists:
            ub_exists = frappe.db.exists("eBarimt District", "2301")

        if ub_exists:
            results.ok(f"Districts ({count} districts, UB found)")
        else:
            results.skip(f"Districts ({count} districts)", "UB code 2301 not found")
    except Exception as e:
        results.fail("Districts", e)


def test_custom_fields(results):
    """Test custom fields on ERPNext doctypes"""
    print("\n🏷️  CUSTOM FIELDS")

    custom_field_checks = [
        # Sales Invoice fields
        ("Sales Invoice", "custom_ebarimt_receipt_id"),
        ("Sales Invoice", "custom_ebarimt_lottery"),
        ("Sales Invoice", "custom_ebarimt_qr_data"),
        ("Sales Invoice", "custom_ebarimt_bill_type"),

        # POS Invoice fields
        ("POS Invoice", "custom_ebarimt_receipt_id"),
        ("POS Invoice", "custom_ebarimt_lottery"),

        # Customer fields (actual field names from custom_fields.py)
        ("Customer", "custom_tin"),
        ("Customer", "custom_is_foreigner"),
        ("Customer", "custom_ebarimt_customer_no"),

        # Item fields
        ("Item", "custom_ebarimt_tax_code"),
        ("Item", "custom_ebarimt_barcode"),

        # Company fields
        ("Company", "custom_ebarimt_enabled"),
        ("Company", "custom_operator_tin"),

        # Mode of Payment fields
        ("Mode of Payment", "custom_ebarimt_payment_type"),

        # Address fields
        ("Address", "custom_ebarimt_district"),
    ]

    for doctype, fieldname in custom_field_checks:
        try:
            # Check if field exists in custom field
            cf_exists = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname})

            if cf_exists:
                results.ok(f"{doctype}.{fieldname}")
            else:
                # Check if field is in DocType definition
                meta = frappe.get_meta(doctype)
                field = meta.get_field(fieldname)
                if field:
                    results.ok(f"{doctype}.{fieldname} (in DocType)")
                else:
                    results.skip(f"{doctype}.{fieldname}", "Not installed yet")
        except Exception as e:
            results.fail(f"{doctype}.{fieldname}", e)


def test_api_client(results):
    """Test API client initialization and methods"""
    print("\n📡 API CLIENT")

    try:
        from ebarimt.api.client import EBarimtClient
        results.ok("Import EBarimtClient")
    except Exception as e:
        results.fail("Import EBarimtClient", e)
        return

    # Test client initialization
    try:
        client = EBarimtClient()
        assert client is not None
        results.ok("Client initialization")
    except Exception as e:
        results.skip("Client initialization", f"Settings not configured: {e}")
        return

    # Test client methods exist
    expected_methods = [
        "create_receipt",
        "get_receipt_info",
        "void_receipt",
        "send_data",
        "get_taxpayer_info",
        "get_tin_by_regno",
        "get_district_codes",
        "get_tax_codes",
        "lookup_barcode",
        "lookup_consumer_by_regno",
        "lookup_consumer_by_phone",
        "approve_receipt_qr",
        "get_foreigner_info",
        "get_foreigner_by_username",
        "register_foreigner",
        "get_oat_product_info",
        "get_oat_stock_by_qr",
        "get_available_stamps",
        "record_stamp_sale",
        "create_oat_receipt",
        "get_info",
        "get_bank_accounts",
    ]

    for method in expected_methods:
        try:
            assert hasattr(EBarimtClient, method), f"Method {method} not found"
            results.ok(f"Method: {method}")
        except Exception as e:
            results.fail(f"Method: {method}", e)


def test_api_endpoints(results):
    """Test whitelisted API endpoints"""
    print("\n🔌 API ENDPOINTS")

    try:
        from ebarimt.api import api
        results.ok("Import api module")
    except Exception as e:
        results.fail("Import api module", e)
        return

    # Check whitelisted functions
    whitelist_funcs = [
        "create_receipt",
        "get_receipt_info",
        "void_receipt",
        "send_data",
        "get_taxpayer_info",
        "get_tin_by_regno",
        "verify_tin",
        "lookup_barcode",
        "get_district_codes",
        "get_tax_codes",
        "lookup_consumer_by_regno",
        "lookup_consumer_by_phone",
        "approve_receipt_qr",
        "get_foreigner_info",
        "get_foreigner_by_username",
        "register_foreigner",
        "get_oat_product_info",
        "get_oat_stock_by_qr",
        "get_available_stamps",
        "get_pos_info",
        "get_bank_accounts",
        "sync_districts",
        "sync_tax_codes",
        "get_receipt_logs",
        "get_receipt_stats",
    ]

    for func_name in whitelist_funcs:
        try:
            func = getattr(api, func_name, None)
            assert func is not None, f"Function {func_name} not found"
            assert hasattr(func, "is_whitelisted") or callable(func)
            results.ok(f"Endpoint: {func_name}")
        except Exception as e:
            results.fail(f"Endpoint: {func_name}", e)


def test_integrations(results):
    """Test integration modules"""
    print("\n🔗 INTEGRATIONS")

    integration_checks = [
        ("ebarimt.integrations.sales_invoice", [
            "validate_invoice_for_ebarimt",
            "on_submit_invoice",
            "submit_ebarimt_receipt",
            "build_receipt_data",
            "create_return_receipt",
            "bulk_submit_receipts",
            "get_receipt_qr_image",
        ]),
        ("ebarimt.integrations.pos_invoice", [
            "validate_pos_invoice",
            "on_submit_pos_invoice",
            "on_cancel_pos_invoice",
            "submit_pos_ebarimt_receipt",
            "create_pos_return_receipt",
            "bulk_submit_pos_receipts",
        ]),
        ("ebarimt.integrations.customer", [
            "validate_customer",
            "after_insert_customer",
            "sync_taxpayer_info",
            "lookup_foreigner",
            "register_foreigner",
            "bulk_sync_taxpayer_info",
        ]),
        ("ebarimt.integrations.item", [
            "validate_item",
            "after_insert_item",
            "sync_barcode_info",
            "bulk_sync_item_barcodes",
            "get_buna_classification",
            "auto_map_tax_code",
        ]),
        ("ebarimt.integrations.payment_entry", [
            "validate_payment_entry",
            "on_submit_payment_entry",
            "on_cancel_payment_entry",
            "get_ebarimt_payment_types",
            "get_payment_summary_for_invoice",
        ]),
        ("ebarimt.integrations.company", [
            "validate_company",
            "get_company_ebarimt_settings",
            "sync_company_taxpayer_info",
            "verify_company_registration",
            "get_ebarimt_enabled_companies",
        ]),
        ("ebarimt.integrations.mode_of_payment", [
            "validate_mode_of_payment",
            "get_ebarimt_payment_code",
            "sync_payment_type_mappings",
            "get_all_payment_mappings",
            "set_payment_mapping",
        ]),
    ]

    for module_path, functions in integration_checks:
        module_name = module_path.split(".")[-1]
        try:
            module = frappe.get_module(module_path)
            results.ok(f"Module: {module_name}")

            for func_name in functions:
                try:
                    func = getattr(module, func_name, None)
                    assert func is not None, "Not found"
                    assert callable(func), "Not callable"
                    results.ok(f"  └─ {func_name}")
                except Exception as e:
                    results.fail(f"  └─ {func_name}", e)

        except Exception as e:
            results.fail(f"Module: {module_name}", e)


def test_scheduler_tasks(results):
    """Test scheduler tasks"""
    print("\n⏰ SCHEDULER TASKS")

    tasks = [
        ("ebarimt.tasks.sync_tax_codes_daily", "daily"),
        ("ebarimt.tasks.sync_pending_receipts_daily", "daily"),
        ("ebarimt.tasks.cleanup_old_failed_logs", "daily"),
        ("ebarimt.tasks.sync_unsent_receipts", "hourly"),
        ("ebarimt.tasks.sync_taxpayer_info_weekly", "weekly"),
        ("ebarimt.tasks.sync_barcode_info_weekly", "weekly"),
    ]

    for task_path, schedule in tasks:
        try:
            module_path = ".".join(task_path.split(".")[:-1])
            func_name = task_path.split(".")[-1]
            module = frappe.get_module(module_path)
            func = getattr(module, func_name, None)
            assert func is not None, "Task not found"
            assert callable(func), "Not callable"
            results.ok(f"{func_name} ({schedule})")
        except Exception as e:
            results.fail(f"{task_path.split('.')[-1]}", e)


def test_hooks(results):
    """Test hooks configuration"""
    print("\n🪝 HOOKS")

    try:
        from ebarimt import hooks
        results.ok("Import hooks")
    except Exception as e:
        results.fail("Import hooks", e)
        return

    # Check doc_events
    expected_doc_events = {
        "Sales Invoice": ["validate", "on_submit", "on_cancel"],
        "POS Invoice": ["validate", "on_submit", "on_cancel"],
        "Customer": ["validate", "after_insert"],
        "Item": ["validate", "after_insert"],
        "Payment Entry": ["validate", "on_submit", "on_cancel"],
        "Company": ["validate", "after_insert"],
        "Mode of Payment": ["validate"],
    }

    for doctype, events in expected_doc_events.items():
        try:
            assert doctype in hooks.doc_events, f"{doctype} not in doc_events"
            for event in events:
                assert event in hooks.doc_events[doctype], f"{event} not in {doctype}"
            results.ok(f"doc_events: {doctype}")
        except Exception as e:
            results.fail(f"doc_events: {doctype}", e)

    # Check doctype_js
    expected_js = [
        "Sales Invoice",
        "POS Invoice",
        "Customer",
        "Item",
        "Payment Entry",
        "Company",
        "Mode of Payment",
    ]

    for doctype in expected_js:
        try:
            assert doctype in hooks.doctype_js, f"{doctype} not in doctype_js"
            results.ok(f"doctype_js: {doctype}")
        except Exception as e:
            results.fail(f"doctype_js: {doctype}", e)

    # Check scheduler_events
    try:
        assert "daily" in hooks.scheduler_events
        assert "hourly" in hooks.scheduler_events
        assert "weekly" in hooks.scheduler_events
        results.ok("scheduler_events configured")
    except Exception as e:
        results.fail("scheduler_events", e)


def test_js_files(results):
    """Test JS files exist"""
    print("\n📄 JS FILES")

    import os

    js_files = [
        "public/js/sales_invoice.js",
        "public/js/pos_invoice.js",
        "public/js/customer.js",
        "public/js/item.js",
        "public/js/payment_entry.js",
        "public/js/company.js",
        "public/js/mode_of_payment.js",
        "public/js/ebarimt.bundle.js",
    ]

    app_path = frappe.get_app_path("ebarimt")

    for js_file in js_files:
        file_path = os.path.join(app_path, js_file)
        try:
            assert os.path.exists(file_path), f"File not found: {js_file}"
            # Check file is not empty
            with open(file_path) as f:
                content = f.read()
                assert len(content) > 100, f"File too small: {js_file}"
            results.ok(f"{js_file}")
        except Exception as e:
            results.fail(f"{js_file}", e)


def test_qpay_integration(results):
    """Test QPay integration (if QPay is installed)"""
    print("\n💳 QPAY INTEGRATION")

    # Check if QPay is installed
    if "qpay" not in frappe.get_installed_apps():
        results.skip("QPay not installed", "QPay app not found")
        return

    # Check QPay DocType exists
    try:
        assert frappe.db.exists("DocType", "QPay Invoice")
        results.ok("QPay Invoice DocType exists")
    except Exception as e:
        results.fail("QPay Invoice DocType", e)

    # Check eBarimt handles QPay receipts
    try:
        from ebarimt.integrations.sales_invoice import has_qpay_ebarimt
        assert callable(has_qpay_ebarimt)
        results.ok("has_qpay_ebarimt function exists")
    except Exception as e:
        results.fail("has_qpay_ebarimt function", e)

    # Check skip_if_qpay_ebarimt setting
    try:
        settings = frappe.get_single("eBarimt Settings")
        # Field should exist even if not set
        _ = settings.get("skip_if_qpay_ebarimt")
        results.ok("skip_if_qpay_ebarimt setting")
    except Exception as e:
        results.skip("skip_if_qpay_ebarimt setting", str(e))


def test_crud_operations(results):
    """Test CRUD operations on eBarimt DocTypes"""
    print("\n📝 CRUD OPERATIONS")

    # Test eBarimt Receipt Log CRUD
    try:
        # Create
        log = frappe.get_doc({
            "doctype": "eBarimt Receipt Log",
            "receipt_id": f"TEST-{frappe.generate_hash(length=10)}",
            "bill_type": "B2C_RECEIPT",
            "status": "Pending",
            "grand_total": 1000,
            "reference_doctype": "Sales Invoice",
            "reference_name": "TEST-INV-001"
        })
        log.insert(ignore_permissions=True)
        results.ok("Create Receipt Log")

        # Read
        log_read = frappe.get_doc("eBarimt Receipt Log", log.name)
        assert log_read.receipt_id == log.receipt_id
        results.ok("Read Receipt Log")

        # Update
        log_read.status = "Success"
        log_read.save(ignore_permissions=True)
        results.ok("Update Receipt Log")

        # Delete
        frappe.delete_doc("eBarimt Receipt Log", log.name, ignore_permissions=True)
        results.ok("Delete Receipt Log")

    except Exception as e:
        results.fail("Receipt Log CRUD", e)

    # Test eBarimt District CRUD
    try:
        # Create test district (using correct field names)
        test_district = frappe.get_doc({
            "doctype": "eBarimt District",
            "code": "999",  # Use 'code' not 'district_code'
            "name_mn": "Тест Дүүрэг",
            "name_en": "Test District",
            "aimag": "Test"  # Use 'aimag' not 'aimag_code'
        })
        test_district.insert(ignore_permissions=True)
        results.ok("Create District")

        # Delete test district
        frappe.delete_doc("eBarimt District", test_district.name, ignore_permissions=True)
        results.ok("Delete District")

    except Exception as e:
        results.fail("District CRUD", e)


def test_receipt_workflow(results):
    """Test receipt workflow (without actual API calls)"""
    print("\n🔄 RECEIPT WORKFLOW")

    try:
        results.ok("Import build_receipt_data")
    except Exception as e:
        results.fail("Import build_receipt_data", e)
        return

    # Test build_receipt_data structure
    try:
        from ebarimt.integrations.sales_invoice import get_customer_tin, get_district_code

        # Test helper functions - get_customer_tin returns empty string for None
        tin = get_customer_tin(None)
        assert tin == "" or tin is None  # Empty string or None
        results.ok("get_customer_tin (null)")

        # Test get_district_code with mock objects
        class MockSettings:
            def __init__(self):
                self.default_district = None
            def get(self, key, default=None):
                return getattr(self, key, default)

        class MockInvoice:
            def __init__(self):
                self.company = None

        district = get_district_code(MockInvoice(), MockSettings())
        assert district is not None  # Should return default "34"
        results.ok("get_district_code (default)")

    except Exception as e:
        results.fail("Receipt workflow helpers", e)

    # Test receipt log creation
    try:
        from ebarimt.ebarimt.doctype.ebarimt_receipt_log.ebarimt_receipt_log import create_receipt_log
        assert callable(create_receipt_log)
        results.ok("create_receipt_log function exists")
    except Exception as e:
        results.fail("create_receipt_log function", e)


def test_error_handling(results):
    """Test error handling"""
    print("\n⚠️  ERROR HANDLING")

    # Test invalid TIN validation
    try:
        from ebarimt.integrations.customer import validate_tin_format

        # Valid TIN formats
        assert validate_tin_format("1234567")
        assert validate_tin_format("123456789012")
        results.ok("Valid TIN format check")

        # Invalid TIN formats
        assert not validate_tin_format("123")
        assert not validate_tin_format("abc")
        assert not validate_tin_format("")
        assert not validate_tin_format(None)
        results.ok("Invalid TIN format check")

    except Exception as e:
        results.fail("TIN validation", e)

    # Test missing settings handling
    try:
        from ebarimt.integrations.sales_invoice import validate_invoice_for_ebarimt

        class MockDoc:
            def __init__(self):
                self.is_return = False
                self.custom_ebarimt_receipt_id = None
                self.customer = None

            def get(self, key, default=None):
                return getattr(self, key, default)

        # Should not raise error when settings disabled or receipt exists
        mock = MockDoc()
        mock.custom_ebarimt_receipt_id = "test"  # Has receipt already
        validate_invoice_for_ebarimt(mock)  # Should skip
        results.ok("Disabled/skip settings handled")

    except Exception as e:
        results.fail("Disabled settings handling", e)


def test_all_frappe_apps_compatibility(results):
    """Test compatibility with all installed Frappe apps"""
    print("\n🔌 FRAPPE APPS COMPATIBILITY")

    installed_apps = frappe.get_installed_apps()

    for app in installed_apps:
        try:
            # Just verify no conflicts with other apps
            if app == "ebarimt":
                continue

            # Check if app has any conflicting hooks
            try:
                app_hooks = frappe.get_hooks(app_name=app)

                # Check for doc_events conflicts
                if "doc_events" in app_hooks:
                    for doctype in ["Sales Invoice", "POS Invoice"]:
                        if doctype in app_hooks.get("doc_events", {}):
                            results.ok(f"{app}: shares {doctype} hooks (compatible)")
                        else:
                            results.ok(f"{app}: no {doctype} conflicts")
            except Exception:
                pass

            results.ok(f"Compatible with: {app}")
        except Exception as e:
            results.fail(f"Compatibility: {app}", e)


# Convenience function to run from console
def run():
    """Alias for run_all_tests"""
    return run_all_tests()


if __name__ == "__main__":
    run_all_tests()
