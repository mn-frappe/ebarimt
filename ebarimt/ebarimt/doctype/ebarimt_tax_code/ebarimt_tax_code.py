# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Tax Code
VAT exempt/zero-rate product codes from Article 12/13

Tax Type Codes:
1 = VAT_ABLE (10% standard VAT)
2 = VAT_FREE (Article 13 exempt)
3 = VAT_ZERO (Article 12 zero-rate)
5 = NO_VAT (Not subject to VAT)
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class eBarimtTaxCode(Document):
	pass


def sync_tax_codes(client=None):
	"""
	Sync tax codes from eBarimt API
	Endpoint: /api/receipt/receipt/getProductTaxCode

	Returns:
		dict: {success: bool, count: int, message: str}
	"""
	if not client:
		from ebarimt.api.client import EBarimtClient
		client = EBarimtClient()

	try:
		tax_codes = client.get_tax_codes()
		count = 0

		for tc in tax_codes:
			code = str(tc.get("taxProductCode", ""))

			if not code:
				continue

			if not frappe.db.exists("eBarimt Tax Code", code):
				doc = frappe.new_doc("eBarimt Tax Code")
				doc.tax_product_code = code
				doc.tax_product_name = tc.get("taxProductName", "")
				doc.tax_type_code = tc.get("taxTypeCode", 0)
				doc.tax_type_name = tc.get("taxTypeName", "")
				doc.start_date = getdate(tc.get("startDate")) if tc.get("startDate") else None
				doc.end_date = getdate(tc.get("endDate")) if tc.get("endDate") else None
				doc.is_default = 0  # API-synced codes are not defaults
				doc.insert(ignore_permissions=True)
				count += 1
			else:
				# Update existing
				doc = frappe.get_doc("eBarimt Tax Code", code)
				doc.tax_product_name = tc.get("taxProductName", "")
				doc.tax_type_code = tc.get("taxTypeCode", 0)
				doc.tax_type_name = tc.get("taxTypeName", "")
				doc.end_date = getdate(tc.get("endDate")) if tc.get("endDate") else None
				doc.save(ignore_permissions=True)

		frappe.db.commit()
		return {"success": True, "count": count, "message": _("{0} tax codes synced").format(count)}

	except Exception as e:
		frappe.log_error(message=str(e), title="eBarimt Tax Code Sync Error")
		return {"success": False, "count": 0, "message": str(e)}


def get_tax_type_for_item(item_code):
	"""
	Get tax type for an item based on its tax code

	Returns:
		str: Tax type name (VAT_ABLE, VAT_FREE, VAT_ZERO, NOT_VAT)
	"""
	item = frappe.get_cached_doc("Item", item_code)

	if item.get("custom_ebarimt_tax_code"):
		tax_code = frappe.get_cached_doc("eBarimt Tax Code", item.custom_ebarimt_tax_code)
		return tax_code.tax_type_name or "VAT_ABLE"

	return "VAT_ABLE"  # Default: Standard VAT


def get_valid_tax_codes(tax_type=None):
	"""
	Get list of currently valid tax codes

	Args:
		tax_type: Filter by tax type (VAT_FREE, VAT_ZERO, NOT_VAT)

	Returns:
		list: Tax codes that are currently valid
	"""
	from frappe.utils import today

	filters = [
		["start_date", "<=", today()],
		["end_date", ">=", today()]
	]

	if tax_type:
		filters.append(["tax_type_name", "=", tax_type])

	return frappe.get_all(
		"eBarimt Tax Code",
		filters=filters,
		fields=["tax_product_code", "tax_product_name", "tax_type_name"]
	)
