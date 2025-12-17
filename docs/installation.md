# Installation

## Prerequisites

- Python 3.10+
- Frappe Bench v15
- ERPNext v15

## Install via Bench

```bash
# Get the app
bench get-app https://github.com/mn-frappe/ebarimt

# Install on your site
bench --site your-site.local install-app ebarimt

# Restart bench
bench restart
```

## Verify Installation

```bash
bench --site your-site.local list-apps
# Should show: ebarimt
```
