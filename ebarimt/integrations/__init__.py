# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

from .sales_invoice import (
    validate_invoice_for_ebarimt,
    on_submit_invoice,
    on_cancel_invoice,
    manual_submit_receipt,
    void_invoice_receipt,
    submit_ebarimt_receipt
)

from .customer import (
    validate_customer,
    after_insert_customer,
    sync_taxpayer_info,
    lookup_taxpayer,
    sync_customer_from_tin
)

from .item import (
    validate_item,
    after_insert_item,
    sync_barcode_info,
    lookup_barcode,
    sync_item_from_barcode,
    get_oat_product_info
)

__all__ = [
    # Sales Invoice
    "validate_invoice_for_ebarimt",
    "on_submit_invoice",
    "on_cancel_invoice",
    "manual_submit_receipt",
    "void_invoice_receipt",
    "submit_ebarimt_receipt",
    
    # Customer
    "validate_customer",
    "after_insert_customer",
    "sync_taxpayer_info",
    "lookup_taxpayer",
    "sync_customer_from_tin",
    
    # Item
    "validate_item",
    "after_insert_item",
    "sync_barcode_info",
    "lookup_barcode",
    "sync_item_from_barcode",
    "get_oat_product_info"
]
