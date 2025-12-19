# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt - Mongolian VAT Receipt System for ERPNext
Full integration with eBarimt (баримт.мн) tax receipt system

100% ERPNext Integration:
- Sales Invoice, POS Invoice (full lifecycle)
- Customer (B2B taxpayer, Foreigner support)
- Item (Barcodes, BUNA classification, Tax codes)
- Payment Entry (payment tracking, type mapping)
- Company (multi-company, per-company settings)
- Mode of Payment (eBarimt payment type mapping)

100% API Coverage:
- 28/28 eBarimt ITC endpoints implemented
- getSaleListERP (ERP subsidiary purchases)
- tpiDeclaration (Customs declarations)

Features (v1.9.0):
- Comprehensive logging utilities (logger.py)
- Autopilot mode for auto-retry, auto-sync, auto-void
- Performance indexes and batch processing
- Multi-company entity support
"""

__version__ = "1.11.0"
