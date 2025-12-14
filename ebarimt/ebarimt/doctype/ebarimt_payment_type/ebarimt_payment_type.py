# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe.model.document import Document


class eBarimtPaymentType(Document):
	pass


def load_default_payment_types():
	"""Load default payment types from PosAPI documentation"""
	# eBarimt POS API payment codes
	# CASH and PAYMENT_CARD are the official codes
	# Others are extended for ERPNext integration
	defaults = [
		# Official PosAPI payment codes
		{"code": "CASH", "name_mn": "Бэлэнээр", "name_en": "Cash", "is_cash": 1, "is_default": 1},
		{"code": "PAYMENT_CARD", "name_mn": "Төлбөрийн карт", "name_en": "Payment Card", "is_cash": 0, "is_default": 1},
		
		# Extended payment types for ERPNext
		{"code": "BANK_TRANSFER", "name_mn": "Банкны шилжүүлэг", "name_en": "Bank Transfer", "is_cash": 0, "is_default": 1},
		{"code": "MOBILE_PAYMENT", "name_mn": "Мобайл төлбөр", "name_en": "Mobile Payment", "is_cash": 0, "is_default": 1},
		
		# Popular payment apps in Mongolia
		{"code": "QPAY", "name_mn": "QPay", "name_en": "QPay", "is_cash": 0, "is_default": 1},
		{"code": "SOCIAL_PAY", "name_mn": "SocialPay", "name_en": "SocialPay", "is_cash": 0, "is_default": 1},
		{"code": "MONPAY", "name_mn": "MonPay", "name_en": "MonPay", "is_cash": 0, "is_default": 1},
		{"code": "MOST_MONEY", "name_mn": "Most Money", "name_en": "Most Money", "is_cash": 0, "is_default": 1},
		{"code": "POCKET", "name_mn": "Pocket", "name_en": "Pocket", "is_cash": 0, "is_default": 1},
		{"code": "TOKI", "name_mn": "Toki", "name_en": "Toki", "is_cash": 0, "is_default": 1},
		
		# Other payment types
		{"code": "PREPAID", "name_mn": "Урьдчилсан төлбөр", "name_en": "Prepaid/Credit", "is_cash": 0, "is_default": 1},
		{"code": "VOUCHER", "name_mn": "Ваучер", "name_en": "Voucher/Coupon", "is_cash": 0, "is_default": 1},
	]
	
	for d in defaults:
		if not frappe.db.exists("eBarimt Payment Type", d["code"]):
			doc = frappe.new_doc("eBarimt Payment Type")
			doc.update(d)
			doc.insert(ignore_permissions=True)
		else:
			# Update is_default for existing records
			frappe.db.set_value("eBarimt Payment Type", d["code"], "is_default", d.get("is_default", 0))
	
	frappe.db.commit()


def get_payment_type_code(payment_method):
	"""
	Map ERPNext payment method to eBarimt payment code
	
	Args:
		payment_method: Mode of payment from Payment Entry
		
	Returns:
		str: eBarimt payment code (CASH or PAYMENT_CARD)
	"""
	if not payment_method:
		return "CASH"
	
	method_lower = payment_method.lower()
	
	# Cash payments
	cash_keywords = ["cash", "бэлэн", "бэлнээр"]
	if any(kw in method_lower for kw in cash_keywords):
		return "CASH"
	
	# Default to PAYMENT_CARD for all non-cash
	return "PAYMENT_CARD"
