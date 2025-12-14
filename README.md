# eBarimt - Mongolian VAT Receipt System for ERPNext

Full integration with Mongolia's eBarimt (баримт.мн) tax receipt system for ERPNext v15.

![Version](https://img.shields.io/badge/Version-v1.4.0-brightgreen)
![Frappe](https://img.shields.io/badge/Frappe-v15-blue)
![ERPNext](https://img.shields.io/badge/ERPNext-v15-green)
![Tests](https://img.shields.io/badge/Tests-171%2F171-success)
![License](https://img.shields.io/badge/License-GPL--3.0-red)

## 🎯 Overview

eBarimt is Mongolia's mandatory electronic VAT receipt system. This app provides:

- **100% API Coverage** - All 26 eBarimt ITC endpoints implemented
- **100% ERPNext Integration** - Sales Invoice, POS, Items, Customers
- **5,500+ Product Codes** - GS1 Mongolia classification with tax mapping
- **Automatic Tax Calculation** - VAT, City Tax, Excise based on product codes

## 🚀 Key Features

### ERPNext DocType Integration

| DocType | Integration | Features |
|---------|-------------|----------|
| **Sales Invoice** | ✅ Full | Auto receipt, return receipts, credit notes |
| **POS Invoice** | ✅ Full | Real-time receipt, lottery, QR code |
| **Customer** | ✅ Full | B2B taxpayer lookup, foreigner registration |
| **Item** | ✅ Full | GS1 codes, barcode lookup, tax mapping |
| **Payment Entry** | ✅ Full | Payment type mapping, multi-payment |
| **Company** | ✅ Full | Multi-company, per-company settings |
| **Mode of Payment** | ✅ Full | eBarimt payment type mapping |

### eBarimt API v2 (26/26 Endpoints)

| Category | Methods | Description |
|----------|---------|-------------|
| **Receipt** | 5 | Create, void, delete, get info, send data |
| **Taxpayer** | 4 | TIN lookup, registration number, bank accounts |
| **Consumer** | 4 | Phone lookup, QR approval, return confirmation |
| **Foreigner** | 3 | Passport lookup, registration, VAT refund |
| **OAT/Excise** | 6 | Stamp lookup, sales recording, excise receipts |
| **Reference** | 4 | District codes, tax codes, barcode lookup |

### Product Classification (GS1 Mongolia)

| Level | Count | Example |
|-------|-------|---------|
| Segment | 70 | Agriculture, Food, Electronics |
| Family | 289 | Grains, Dairy, Computers |
| Class | 462 | Wheat, Milk, Laptops |
| Brick | 3,910+ | Specific products |
| **Total** | **5,541** | Full GS1 hierarchy |

### Tax Configuration

| Tax Type | Rate | Products |
|----------|------|----------|
| **STANDARD** | 10% VAT | 5,484 general products |
| **ZERO** | 0% VAT | 7 export/mining codes |
| **EXEMPT** | VAT Free | 50 healthcare/education codes |
| **City Tax** | 2% | Alcohol, tobacco, fuel (UB only) |
| **Excise (OAT)** | Varies | Alcohol, tobacco, fuel |

## 📦 Installation

```bash
# Get the app
bench get-app https://github.com/mn-frappe/ebarimt --branch develop

# Install on your site
bench --site your-site.local install-app ebarimt
bench --site your-site.local migrate
```

## ⚙️ Configuration

### 1. eBarimt Settings

Go to **eBarimt Settings** and configure:

```
✅ Enable eBarimt
📍 POS API URL: https://ebarimt.mn/rest/api
🔑 Merchant TIN: Your company TIN
🏪 Branch Code: Your branch code
🖥️ POS Number: Your POS terminal number
```

### 2. Company Configuration

For each company using eBarimt:
- Set company TIN
- Configure branch codes
- Map to eBarimt settings

### 3. Item Configuration

Link items to GS1 product codes:
- Go to Item > eBarimt section
- Set **eBarimt Product Code** 
- Tax info auto-calculated based on code

## 🎯 Quick Start

### Create Receipt from Sales Invoice

```python
import frappe
from ebarimt.api.api import create_receipt

# Auto-creates eBarimt receipt when invoice submitted
result = create_receipt("Sales Invoice", "SINV-00001")

# Returns receipt ID and lottery number
print(f"Receipt: {result['id']}, Lottery: {result['lottery']}")
```

### Lookup Taxpayer Info

```python
from ebarimt.api.api import get_taxpayer_info

# Get company info by TIN
info = get_taxpayer_info("5000000")
print(f"Company: {info['name']}, Active: {info['found']}")
```

### Get Product Tax Info

```python
from ebarimt.api.api import get_product_tax_info

# Get tax configuration for product code
tax = get_product_tax_info("500101")
# Returns: vat_type, vat_rate, city_tax_applicable, excise_type
```

## 📊 DocTypes

| DocType | Description |
|---------|-------------|
| **eBarimt Settings** | Global configuration |
| **eBarimt Receipt Log** | Receipt history and status |
| **eBarimt Product Code** | 5,500+ GS1 codes with tax mapping |
| **eBarimt Tax Code** | VAT Zero/Exempt codes |
| **eBarimt District** | City/district codes |
| **eBarimt Payment Type** | Payment method mapping |
| **eBarimt OAT Product Type** | Excise product types |

## 🔌 API Reference

### Receipt Operations

| Method | Description |
|--------|-------------|
| `create_receipt(doctype, docname)` | Create receipt for document |
| `get_receipt_info(receipt_id)` | Get receipt details |
| `void_receipt(receipt_id)` | Void/cancel receipt |

### Taxpayer Operations

| Method | Description |
|--------|-------------|
| `get_taxpayer_info(tin)` | Lookup by TIN |
| `get_tin_by_regno(reg_no)` | Get TIN from registration |
| `get_bank_accounts(tin)` | Get registered bank accounts |

### Consumer Operations

| Method | Description |
|--------|-------------|
| `lookup_consumer_by_phone(phone)` | Find consumer by phone |
| `approve_receipt_qr(customer_no, qr)` | Approve via QR |

### Product Code Operations

| Method | Description |
|--------|-------------|
| `get_product_tax_info(code)` | Get tax config for product |
| `import_all_gs1_codes()` | Import all 5,500+ codes |
| `sync_product_codes_to_qpay()` | Sync to QPay app |

### Foreigner Operations

| Method | Description |
|--------|-------------|
| `get_foreigner_info(passport)` | Lookup tourist |
| `register_foreigner(...)` | Register for VAT refund |

### OAT/Excise Operations

| Method | Description |
|--------|-------------|
| `get_oat_product_info(barcode)` | Get excise product info |
| `get_available_stamps(...)` | Check stamp inventory |

## 🔗 QPay Integration

eBarimt and QPay apps work together:

```python
# Both apps use same product codes (5,541 codes)
# eBarimt is master (has tax info), QPay syncs from it

from ebarimt.api.api import sync_product_codes_to_qpay
result = sync_product_codes_to_qpay()  # Syncs all codes

# Both apps use same VAT types: STANDARD, ZERO, EXEMPT
```

## 🧪 Testing

```bash
# Run all tests (171 tests)
bench --site your-site.local run-tests --app ebarimt

# Test coverage: 100%
# - Unit tests for all API methods
# - Integration tests for ERPNext DocTypes
# - Tax calculation tests
```

## 📁 Project Structure

```
ebarimt/
├── ebarimt/
│   ├── api/
│   │   ├── api.py           # 36 whitelisted API endpoints
│   │   ├── client.py        # eBarimt ITC client (26 methods)
│   │   └── auth.py          # Authentication
│   ├── integrations/
│   │   ├── sales_invoice.py # Sales Invoice integration
│   │   ├── pos_invoice.py   # POS Invoice integration
│   │   ├── customer.py      # Customer integration
│   │   ├── item.py          # Item integration
│   │   ├── payment_entry.py # Payment Entry integration
│   │   ├── company.py       # Company integration
│   │   ├── mode_of_payment.py
│   │   ├── custom_fields.py # Custom field definitions
│   │   └── unified_product_codes.py  # QPay sync
│   ├── doctype/
│   │   ├── ebarimt_settings/
│   │   ├── ebarimt_receipt_log/
│   │   ├── ebarimt_product_code/  # 5,541 codes
│   │   ├── ebarimt_tax_code/
│   │   ├── ebarimt_district/
│   │   ├── ebarimt_payment_type/
│   │   └── ebarimt_oat_product_type/
│   └── tests/               # 171 tests
├── hooks.py
└── setup.py
```

## 📝 Changelog

### v1.4.0 (Current)
- eBarimt Product Code DocType with 5,541 GS1 codes
- Unified product code sync with QPay
- Full tax configuration (VAT, City Tax, Excise)
- 100% test coverage (171/171 tests)

### v1.3.0
- Full eBarimt API v2 implementation (26 endpoints)
- OAT/Excise stamp support
- Foreigner VAT refund support

### v1.2.0
- POS Invoice real-time integration
- Return receipt support
- Multi-company support

### v1.1.0
- Sales Invoice integration
- Customer B2B lookup
- Payment Entry mapping

### v1.0.0
- Initial release
- Basic receipt creation

## 🤝 Contributing

1. Fork the repository
2. Install pre-commit: `pre-commit install`
3. Run tests: `bench run-tests --app ebarimt`
4. Submit PR

## 📄 License

GNU General Public License v3.0

## 🔗 Links

- [eBarimt Official](https://ebarimt.mn/)
- [QPay App](https://github.com/mn-frappe/qpay) - Payment gateway integration
- [Report Issues](https://github.com/mn-frappe/ebarimt/issues)

---

Developed by [mn-frappe](https://github.com/mn-frappe) for the Mongolian ERPNext community 🇲🇳
