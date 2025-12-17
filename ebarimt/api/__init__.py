# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt API Module
Complete API client and whitelisted endpoints
"""

# Import all whitelisted API functions for easy access
from ebarimt.api.api import (
    approve_receipt_qr,
    # Receipt operations
    create_receipt,
    get_available_stamps,
    get_bank_accounts,
    get_district_codes,
    get_foreigner_by_username,
    # Foreign Tourist
    get_foreigner_info,
    # OAT - Excise Tax
    get_oat_product_info,
    get_oat_stock_by_qr,
    # Company & POS
    get_pos_info,
    get_receipt_info,
    # Receipt logs & stats
    get_receipt_logs,
    get_receipt_stats,
    get_tax_codes,
    # Taxpayer information
    get_taxpayer_info,
    get_tin_by_regno,
    # Barcode & Product
    lookup_barcode,
    lookup_consumer_by_phone,
    # Consumer/Lottery
    lookup_consumer_by_regno,
    register_foreigner,
    send_data,
    # Sync operations
    sync_districts,
    sync_tax_codes,
    verify_tin,
    void_receipt,
)
from ebarimt.api.auth import ITCAuth
from ebarimt.api.client import EBarimtClient

__all__ = [
    "EBarimtClient",
    "ITCAuth",
    "approve_receipt_qr",
    # Receipt operations
    "create_receipt",
    "get_available_stamps",
    "get_bank_accounts",
    "get_district_codes",
    "get_foreigner_by_username",
    # Foreign Tourist
    "get_foreigner_info",
    # OAT - Excise Tax
    "get_oat_product_info",
    "get_oat_stock_by_qr",
    # Company & POS
    "get_pos_info",
    "get_receipt_info",
    # Receipt logs
    "get_receipt_logs",
    "get_receipt_stats",
    "get_tax_codes",
    # Taxpayer information
    "get_taxpayer_info",
    "get_tin_by_regno",
    # Barcode & Product
    "lookup_barcode",
    "lookup_consumer_by_phone",
    # Consumer/Lottery
    "lookup_consumer_by_regno",
    "register_foreigner",
    "send_data",
    # Sync
    "sync_districts",
    "sync_tax_codes",
    "verify_tin",
    "void_receipt",
]
