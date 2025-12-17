## [1.10.0](https://github.com/mn-frappe/ebarimt/compare/v1.9.0...v1.10.0) (2025-12-17)

### 🚀 Features

* add CodeQL, CODEOWNERS, MkDocs documentation ([74d9213](https://github.com/mn-frappe/ebarimt/commit/74d9213baef8b7084568d486b5ff4a1852d5c555))
* add mypy type checking, matrix testing, enhanced VS Code ([5b3a73b](https://github.com/mn-frappe/ebarimt/commit/5b3a73baf170be56f2eada735f0a3ebbb3b20387))
* add semantic-release for automatic versioning ([439e51d](https://github.com/mn-frappe/ebarimt/commit/439e51d02bcd411fa51bec292085b01977d90ba3))
* add telemetry for GitHub issue auto-creation ([dcca0cb](https://github.com/mn-frappe/ebarimt/commit/dcca0cb791490a4965116ec8bc5ce93b9d33d5b4))

### 🐛 Bug Fixes

* resolve type errors in telemetry module ([584dd28](https://github.com/mn-frappe/ebarimt/commit/584dd28b194fdf521c0a483c848b0b022d94446b))
* semantic-release auth and missing npm package ([1630991](https://github.com/mn-frappe/ebarimt/commit/1630991e261ad67e23ef3dd1ba5ca308f918750c))

# Changelog

All notable changes to eBarimt will be documented in this file.

## [1.9.0] - 2024-12-17

### Added
- Multi-company entity support
- Enhanced ERPNext app compatibility
- Local mn_entity.py for CI compatibility
- Comprehensive test suite (37 tests)

### Changed
- Improved type checking compatibility
- Better import handling for CI environments

### Fixed
- Linting issues for CI compliance
- Type annotation compatibility

## [1.8.2] - 2024-12-16

### Added
- Route all API calls through api.frappe.mn gateway
- eBarimt Public API gateway integration

### Changed
- Improved API routing for reliability

## [1.8.0] - 2024-12-15

### Added
- ERP purchase API integration
- Customs declaration APIs
- 100% API coverage (26/26 endpoints)

## [1.7.0] - 2024-12-14

### Added
- 100% Frappe Framework Integration
- Full ERPNext DocType integration
- Sales Invoice, POS, Customer, Item integration

## [1.4.0] - 2024-12-14

### Added
- eBarimt Product Code DocType (5,541 GS1 codes)
- Unified product code sync with QPay
- Full tax configuration (VAT, City Tax, Excise)
- 100% test coverage

## [1.0.0] - 2024-12-13

### Added
- Initial release
- Basic eBarimt API integration
- Receipt creation and management
- Taxpayer lookup
