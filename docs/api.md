# API Reference

## Whitelisted Methods

### Receipt Operations

#### `ebarimt.api.send_receipt`

Send a VAT receipt to eBarimt.

```python
import frappe

result = frappe.call(
    "ebarimt.api.send_receipt",
    sales_invoice="INV-001"
)
```

---

#### `ebarimt.api.check_receipt`

Check receipt status.

```python
result = frappe.call(
    "ebarimt.api.check_receipt",
    receipt_id="ebarimt_receipt_id"
)
```

---

#### `ebarimt.api.get_tin_info`

Get taxpayer information by TIN.

```python
result = frappe.call(
    "ebarimt.api.get_tin_info",
    tin="1234567"
)
```

## JavaScript API

```javascript
frappe.call({
    method: "ebarimt.api.send_receipt",
    args: {
        sales_invoice: "INV-001"
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```
