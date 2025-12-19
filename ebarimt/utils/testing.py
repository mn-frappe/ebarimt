# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Test Utilities for eBarimt

Provides mock fixtures, test helpers, and factory functions for testing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import frappe


@dataclass
class MockResponse:
    """Mock HTTP response"""
    status_code: int = 200
    content: bytes | str = b""
    headers: dict = field(default_factory=dict)
    text: str = field(init=False, default="")
    
    def __post_init__(self):
        if isinstance(self.content, str):
            self.content = self.content.encode("utf-8")
        self.text = bytes(self.content).decode("utf-8")
    
    def json(self) -> dict:
        return json.loads(self.content)
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class EBarimtMockClient:
    """
    Mock eBarimt API client for testing.
    
    Usage:
        with EBarimtMockClient() as mock_client:
            mock_client.set_response("create_receipt", {
                "success": True,
                "billId": "ABC123",
                "lottery": "12345678",
                "qrData": "https://ebarimt.mn/..."
            })
            
            result = create_receipt(data)
            assert result["success"]
    """
    
    def __init__(self):
        self._responses: dict[str, Any] = {}
        self._calls: dict[str, list] = {}
        self._patch = None
    
    def set_response(self, method: str, response: Any):
        self._responses[method] = response
    
    def set_error(self, method: str, error: Exception):
        self._responses[method] = error
    
    def call_count(self, method: str) -> int:
        return len(self._calls.get(method, []))
    
    def get_calls(self, method: str) -> list:
        return self._calls.get(method, [])
    
    def _record_call(self, method: str, *args, **kwargs):
        if method not in self._calls:
            self._calls[method] = []
        self._calls[method].append({"args": args, "kwargs": kwargs})
    
    def _get_response(self, method: str):
        response = self._responses.get(method)
        if isinstance(response, Exception):
            raise response
        return response or {"success": True}
    
    def __enter__(self):
        self._patch = patch("ebarimt.ebarimt.api.EBarimtClient")
        mock_class = self._patch.start()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        def make_mock_method(method_name):
            def mock_method(*args, **kwargs):
                self._record_call(method_name, *args, **kwargs)
                return self._get_response(method_name)
            return mock_method
        
        for method in ["create_receipt", "return_receipt", "get_info", "check_api", "get_receipt"]:
            setattr(mock_instance, method, make_mock_method(method))
        
        return self
    
    def __exit__(self, *args):
        if self._patch:
            self._patch.stop()


# Test data factories

def make_receipt_item(
    name: str = "Test Product",
    qty: float = 1,
    unit_price: float = 10000,
    tax_code: str = "VAT_ABLE",
    **kwargs
) -> dict:
    """Create test receipt item"""
    total = qty * unit_price
    discount = kwargs.get("discount", 0)
    
    return {
        "name": name,
        "qty": qty,
        "unit_price": unit_price,
        "total": total - discount,
        "tax_code": tax_code,
        "discount": discount,
        "barcode": kwargs.get("barcode"),
        **{k: v for k, v in kwargs.items() if k not in ["discount", "barcode"]}
    }


def make_receipt_data(
    receipt_type: str = "B2C_RECEIPT",
    seller_tin: str = "1234567",
    items: list | None = None,
    **kwargs
) -> dict:
    """Create test receipt data"""
    items = items or [make_receipt_item()]
    total_amount = sum(item["total"] for item in items)
    vat_amount = total_amount * 0.1  # 10% VAT
    
    data = {
        "receipt_type": receipt_type,
        "seller_tin": seller_tin,
        "items": items,
        "total_amount": total_amount,
        "vat_amount": vat_amount,
        **kwargs
    }
    
    # B2B requires customer info
    if receipt_type in ["B2B_RECEIPT", "B2B_RETURN"]:
        data.setdefault("customer_tin", "7654321")
        data.setdefault("customer_name", "Customer Company LLC")
    
    return data


def make_receipt_response(
    success: bool = True,
    bill_id: str = "BILL123456",
    lottery: str = "12345678",
    **kwargs
) -> dict:
    """Create mock receipt response"""
    if not success:
        return {
            "success": False,
            "errorCode": kwargs.get("error_code", "ERR001"),
            "message": kwargs.get("message", "Test error")
        }
    
    return {
        "success": True,
        "billId": bill_id,
        "lottery": lottery,
        "qrData": f"https://ebarimt.mn/bill/{bill_id}",
        "date": datetime.now().isoformat(),
        **kwargs
    }


def make_return_receipt_data(
    original_bill_id: str = "BILL123456",
    items: list | None = None,
    **kwargs
) -> dict:
    """Create test return receipt data"""
    items = items or [make_receipt_item()]
    
    return {
        "receipt_type": "B2C_RETURN",
        "original_bill_id": original_bill_id,
        "items": items,
        "total_amount": sum(item["total"] for item in items),
        "return_reason": kwargs.get("return_reason", "Customer return"),
        **kwargs
    }


# Test fixtures

class TestFixtures:
    """Test fixtures for eBarimt"""
    
    @staticmethod
    def create_test_settings(
        enabled: bool = True,
        api_url: str = "https://test.ebarimt.mn",
        pos_id: str = "TEST_POS_001"
    ) -> None:
        """Create or update test settings"""
        try:
            settings = frappe.get_single("eBarimt Settings")
        except frappe.DoesNotExistError:
            settings = frappe.new_doc("eBarimt Settings")
        
        setattr(settings, "enabled", enabled)
        setattr(settings, "api_url", api_url)
        setattr(settings, "pos_id", pos_id)
        settings.save(ignore_permissions=True)
    
    @staticmethod
    def create_test_gs1_code(
        barcode: str = "4901234567890",
        product_name: str = "Test Product",
        **kwargs
    ) -> str | None:
        """Create test GS1 product code"""
        if not frappe.db.table_exists("GS1 Product Code"):
            return None
        
        if frappe.db.exists("GS1 Product Code", {"barcode": barcode}):
            return barcode
        
        doc = frappe.get_doc({
            "doctype": "GS1 Product Code",
            "barcode": barcode,
            "product_name": product_name,
            **kwargs
        })
        doc.insert(ignore_permissions=True)
        return str(getattr(doc, "barcode", barcode))
    
    @staticmethod
    def cleanup():
        """Clean up test data"""
        frappe.db.commit()


# Assertion helpers

def assert_receipt_valid(receipt_data: dict):
    """Assert receipt data is valid"""
    assert "items" in receipt_data and len(receipt_data["items"]) > 0
    assert "total_amount" in receipt_data and receipt_data["total_amount"] > 0
    assert "seller_tin" in receipt_data


def assert_api_called(mock_client: EBarimtMockClient, method: str, times: int = 1):
    actual = mock_client.call_count(method)
    assert actual == times, f"Expected {method} to be called {times} times, got {actual}"


# Context managers

class DisabledCircuitBreaker:
    """Disable circuit breaker during tests"""
    
    def __enter__(self):
        self._patch = patch("ebarimt.utils.resilience.ebarimt_circuit_breaker")
        mock_cb = self._patch.start()
        mock_cb.call.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        return mock_cb
    
    def __exit__(self, *args):
        self._patch.stop()


class MockedOfflineQueue:
    """Mock offline queue for testing"""
    
    def __init__(self):
        self.items: list = []
        self._patch: Any = None
    
    def __enter__(self):
        self._patch = patch("ebarimt.utils.offline_queue.offline_queue")
        mock_queue = self._patch.start()
        mock_queue.enqueue = MagicMock(side_effect=lambda *args, **kwargs: self.items.append(kwargs))
        mock_queue.get_queue_stats = MagicMock(return_value={"pending": len(self.items)})
        return self
    
    def __exit__(self, *args):
        if self._patch:
            self._patch.stop()
