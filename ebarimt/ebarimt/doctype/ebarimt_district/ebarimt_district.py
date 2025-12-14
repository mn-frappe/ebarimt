# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe.model.document import Document


class eBarimtDistrict(Document):
	pass


def sync_districts(client=None):
	"""
	Sync district codes from eBarimt API
	
	Returns:
		int: Number of districts synced
	"""
	if not client:
		from ebarimt.api.client import EBarimtClient
		client = EBarimtClient()
	
	districts = client.get_district_codes()
	count = 0
	
	for district in districts:
		branch_code = district.get("branchCode", "")
		sub_branch_code = district.get("subBranchCode", "")
		code = f"{branch_code}{sub_branch_code}"
		
		if not frappe.db.exists("eBarimt District", code):
			doc = frappe.new_doc("eBarimt District")
			doc.code = code
			doc.branch_code = branch_code
			doc.branch_name = district.get("branchName", "")
			doc.sub_branch_code = sub_branch_code
			doc.sub_branch_name = district.get("subBranchName", "")
			doc.insert(ignore_permissions=True)
			count += 1
		else:
			# Update existing
			doc = frappe.get_doc("eBarimt District", code)
			doc.branch_name = district.get("branchName", "")
			doc.sub_branch_name = district.get("subBranchName", "")
			doc.save(ignore_permissions=True)
	
	frappe.db.commit()
	return count


def load_default_districts():
	"""Load default Mongolian districts"""
	# Major districts for initial setup
	defaults = [
		{"code": "2301", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "01", "sub_branch_name": "Баянгол"},
		{"code": "2302", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "02", "sub_branch_name": "Баянзүрх"},
		{"code": "2303", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "03", "sub_branch_name": "Сүхбаатар"},
		{"code": "2304", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "04", "sub_branch_name": "Чингэлтэй"},
		{"code": "2305", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "05", "sub_branch_name": "Хан-Уул"},
		{"code": "2306", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "06", "sub_branch_name": "Сонгинохайрхан"},
		{"code": "2307", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "07", "sub_branch_name": "Налайх"},
		{"code": "2308", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "08", "sub_branch_name": "Багануур"},
		{"code": "2309", "branch_code": "23", "branch_name": "Улаанбаатар", "sub_branch_code": "09", "sub_branch_name": "Багахангай"},
	]
	
	for d in defaults:
		if not frappe.db.exists("eBarimt District", d["code"]):
			doc = frappe.new_doc("eBarimt District")
			doc.update(d)
			doc.insert(ignore_permissions=True)
	
	frappe.db.commit()
