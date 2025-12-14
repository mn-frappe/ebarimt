# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class eBarimtTaxCode(Document):
	pass


def sync_tax_codes(client=None):
	"""
	Sync tax codes from eBarimt API
	
	Returns:
		int: Number of tax codes synced
	"""
	if not client:
		from ebarimt.api.client import EBarimtClient
		client = EBarimtClient()
	
	tax_codes = client.get_tax_codes()
	count = 0
	
	for tc in tax_codes:
		code = tc.get("taxProductCode", "")
		
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
	return count


def get_tax_type_for_item(item_code):
	"""
	Get tax type for an item based on its tax code
	
	Returns:
		tuple: (tax_type_code, tax_type_name) or (1, "VAT") as default
	"""
	item = frappe.get_cached_doc("Item", item_code)
	
	if item.get("custom_ebarimt_tax_code"):
		tax_code = frappe.get_cached_doc("eBarimt Tax Code", item.custom_ebarimt_tax_code)
		return tax_code.tax_type_code, tax_code.tax_type_name
	
	return 1, "VAT"  # Default: Standard VAT
