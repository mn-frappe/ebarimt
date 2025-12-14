# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt API Module
Complete API client and whitelisted endpoints
"""

from ebarimt.api.client import EBarimtClient
from ebarimt.api.auth import ITCAuth

# Import all whitelisted API functions for easy access
from ebarimt.api.api import (
    # Receipt operations
    create_receipt,
    get_receipt_info,
    void_receipt,
    send_data,
    
    # Taxpayer information
    get_taxpayer_info,
    get_tin_by_regno,
    verify_tin,
    
    # Barcode & Product
    lookup_barcode,
    get_district_codes,
    get_tax_codes,
    
    # Consumer/Lottery
    lookup_consumer_by_regno,
    lookup_consumer_by_phone,
    approve_receipt_qr,
    
    # Foreign Tourist
    get_foreigner_info,
    get_foreigner_by_username,
    register_foreigner,
    
    # OAT - Excise Tax
    get_oat_product_info,
    get_oat_stock_by_qr,
    get_available_stamps,
    
    # Company & POS
    get_pos_info,
    get_bank_accounts,
    
    # Sync operations
    sync_districts,
    sync_tax_codes,
    
    # Receipt logs & stats
    get_receipt_logs,
    get_receipt_stats,
)

__all__ = [
    "EBarimtClient", 
    "ITCAuth",
    # Receipt operations
    "create_receipt",
    "get_receipt_info",
    "void_receipt",
    "send_data",
    # Taxpayer information
    "get_taxpayer_info",
    "get_tin_by_regno",
    "verify_tin",
    # Barcode & Product
    "lookup_barcode",
    "get_district_codes",
    "get_tax_codes",
    # Consumer/Lottery
    "lookup_consumer_by_regno",
    "lookup_consumer_by_phone",
    "approve_receipt_qr",
    # Foreign Tourist
    "get_foreigner_info",
    "get_foreigner_by_username",
    "register_foreigner",
    # OAT - Excise Tax
    "get_oat_product_info",
    "get_oat_stock_by_qr",
    "get_available_stamps",
    # Company & POS
    "get_pos_info",
    "get_bank_accounts",
    # Sync
    "sync_districts",
    "sync_tax_codes",
    # Receipt logs
    "get_receipt_logs",
    "get_receipt_stats",
]
