# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Validation Utilities for eBarimt

Provides data validation for receipt creation before sending to VAT system.
Prevents invalid receipts from being submitted.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import frappe
from frappe import _


@dataclass
class ValidationError:
    """Single validation error"""
    field: str
    message: str
    code: str = "invalid"
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: list[ValidationError]
    
    def raise_if_invalid(self):
        """Raise ValidationException if invalid"""
        if not self.is_valid:
            error_messages = [f"{e.field}: {e.message}" for e in self.errors]
            frappe.throw(
                _("Validation failed: {0}").format("; ".join(error_messages)),
                title=_("eBarimt Validation Error")
            )


class Validator:
    """Chainable field validator"""
    
    def __init__(self):
        self._errors: list[ValidationError] = []
        self._current_field: str | None = None
        self._current_value: Any = None
        self._skip_remaining = False
    
    def field(self, name: str, value: Any) -> "Validator":
        """Start validating a new field"""
        self._current_field = name
        self._current_value = value
        self._skip_remaining = False
        return self
    
    def _add_error(self, message: str, code: str = "invalid"):
        self._errors.append(ValidationError(
            field=self._current_field or "unknown",
            message=message,
            code=code,
            value=self._current_value
        ))
    
    def required(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if self._current_value is None or self._current_value == "":
            self._add_error(message or _("This field is required"), "required")
            self._skip_remaining = True
        return self
    
    def optional(self) -> "Validator":
        if self._current_value is None or self._current_value == "":
            self._skip_remaining = True
        return self
    
    def regex(self, pattern: str, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if not re.match(pattern, str(self._current_value)):
            self._add_error(message or _("Invalid format"), "format")
        return self
    
    def min_length(self, length: int, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if len(str(self._current_value)) < length:
            self._add_error(message or _("Must be at least {0} characters").format(length), "min_length")
        return self
    
    def max_length(self, length: int, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if len(str(self._current_value)) > length:
            self._add_error(message or _("Must be at most {0} characters").format(length), "max_length")
        return self
    
    def between(self, min_val: float, max_val: float, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            val = float(self._current_value)
            if val < min_val or val > max_val:
                self._add_error(message or _("Must be between {0} and {1}").format(min_val, max_val), "range")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def positive(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            if float(self._current_value) <= 0:
                self._add_error(message or _("Must be positive"), "positive")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def non_negative(self, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        try:
            if float(self._current_value) < 0:
                self._add_error(message or _("Must be non-negative"), "non_negative")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def in_list(self, valid_values: list, message: str | None = None) -> "Validator":
        if self._skip_remaining:
            return self
        if self._current_value not in valid_values:
            self._add_error(
                message or _("Must be one of: {0}").format(", ".join(str(v) for v in valid_values)),
                "choices"
            )
        return self
    
    def is_decimal(self, max_places: int = 2, message: str | None = None) -> "Validator":
        """Value must be valid decimal with max decimal places"""
        if self._skip_remaining:
            return self
        try:
            dec = Decimal(str(self._current_value))
            exponent = dec.as_tuple().exponent
            if isinstance(exponent, int) and exponent < -max_places:
                self._add_error(
                    message or _("Maximum {0} decimal places allowed").format(max_places),
                    "decimal_places"
                )
        except InvalidOperation:
            self._add_error(_("Invalid decimal number"), "decimal")
        return self
    
    def custom(self, validator_func: Callable[[Any], bool], message: str) -> "Validator":
        if self._skip_remaining:
            return self
        if not validator_func(self._current_value):
            self._add_error(message, "custom")
        return self
    
    def validate(self) -> ValidationResult:
        return ValidationResult(
            is_valid=len(self._errors) == 0,
            errors=self._errors.copy()
        )


# eBarimt-specific validators

def validate_tin(tin: str) -> ValidationResult:
    """Validate Tax Identification Number (TIN)"""
    v = Validator()
    v.field("tin", tin).required()
    
    # TIN must be 7-11 digits (company vs individual)
    if tin:
        v.regex(r"^\d{7,11}$", _("TIN must be 7-11 digits"))
    
    return v.validate()


def validate_register_number(reg_no: str) -> ValidationResult:
    """Validate Mongolian registration number (company or personal)"""
    v = Validator()
    v.field("register_number", reg_no).required()
    
    if reg_no:
        # Company: 7 digits, Individual: 2 letters + 8 digits (e.g., УА12345678)
        company_pattern = r"^\d{7}$"
        individual_pattern = r"^[А-ЯӨҮЁ]{2}\d{8}$"
        
        is_valid = bool(re.match(company_pattern, reg_no) or re.match(individual_pattern, reg_no))
        if not is_valid:
            v.custom(lambda x: False, _("Invalid registration number format"))
    
    return v.validate()


def validate_receipt_type(receipt_type: str) -> ValidationResult:
    """Validate receipt type code"""
    valid_types = ["B2C_RECEIPT", "B2B_RECEIPT", "B2C_RETURN", "B2B_RETURN"]
    return (Validator()
        .field("receipt_type", receipt_type)
        .required()
        .in_list(valid_types, _("Invalid receipt type"))
        .validate())


def validate_receipt_item(item: dict, index: int) -> ValidationResult:
    """Validate a single receipt item"""
    v = Validator()
    prefix = f"items[{index}]"
    
    # Required fields
    v.field(f"{prefix}.name", item.get("name")).required().max_length(200)
    v.field(f"{prefix}.qty", item.get("qty")).required().positive()
    v.field(f"{prefix}.unit_price", item.get("unit_price")).required().non_negative().is_decimal(2)
    v.field(f"{prefix}.total", item.get("total")).required().non_negative().is_decimal(2)
    
    # Tax code validation
    v.field(f"{prefix}.tax_code", item.get("tax_code")).required().in_list(
        ["VAT_ABLE", "VAT_FREE", "VAT_ZERO", "NO_VAT"],
        _("Invalid tax code")
    )
    
    # GS1/barcode validation (optional but if present must be valid)
    if item.get("barcode"):
        v.field(f"{prefix}.barcode", item["barcode"]).max_length(50)
    
    # Discount validation
    if item.get("discount"):
        v.field(f"{prefix}.discount", item["discount"]).non_negative().is_decimal(2)
    
    return v.validate()


def validate_receipt_data(data: dict) -> ValidationResult:
    """Validate complete receipt data before eBarimt submission"""
    v = Validator()
    
    # Seller info
    v.field("seller_tin", data.get("seller_tin")).required().regex(r"^\d{7,11}$")
    
    # Customer info (B2B requires customer details)
    receipt_type = data.get("receipt_type", "B2C_RECEIPT")
    if receipt_type in ["B2B_RECEIPT", "B2B_RETURN"]:
        v.field("customer_tin", data.get("customer_tin")).required()
        validate_tin(data.get("customer_tin", "")).raise_if_invalid()
    
    # Items
    items = data.get("items", [])
    v.field("items", items).required().custom(
        lambda x: isinstance(x, list) and len(x) > 0,
        _("At least one item is required")
    )
    
    # Validate each item
    for i, item in enumerate(items):
        item_result = validate_receipt_item(item, i)
        v._errors.extend(item_result.errors)
    
    # Amounts
    v.field("total_amount", data.get("total_amount")).required().positive().is_decimal(2)
    v.field("vat_amount", data.get("vat_amount")).required().non_negative().is_decimal(2)
    
    # Validate amounts match items
    if items and data.get("total_amount"):
        calculated_total = sum(float(item.get("total", 0)) for item in items)
        v.field("total_amount", data["total_amount"]).custom(
            lambda x: abs(float(x) - calculated_total) < 0.01,
            _("Total amount must match sum of item totals ({0})").format(calculated_total)
        )
    
    # Receipt type
    v.field("receipt_type", receipt_type).in_list(
        ["B2C_RECEIPT", "B2B_RECEIPT", "B2C_RETURN", "B2B_RETURN"]
    )
    
    return v.validate()


def validate_lottery_number(lottery_number: str) -> ValidationResult:
    """Validate lottery number format"""
    return (Validator()
        .field("lottery_number", lottery_number)
        .required()
        .regex(r"^\d{8}$", _("Lottery number must be exactly 8 digits"))
        .validate())


def validate_qrcode_data(qrcode: str) -> ValidationResult:
    """Validate eBarimt QR code data"""
    return (Validator()
        .field("qrcode", qrcode)
        .required()
        .min_length(10, _("Invalid QR code"))
        .validate())


# Helper
def validate_or_throw(result: ValidationResult):
    """Raise exception if validation failed"""
    result.raise_if_invalid()
