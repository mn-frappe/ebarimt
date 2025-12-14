# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe.model.document import Document


class eBarimtPaymentType(Document):
	pass


def load_default_payment_types():
	"""Load default payment types"""
	defaults = [
		{"code": "CASH", "name_mn": "Бэлэнээр", "name_en": "Cash", "is_cash": 1},
		{"code": "PAYMENT_CARD", "name_mn": "Төлбөрийн карт", "name_en": "Payment Card", "is_cash": 0},
		{"code": "BANK_TRANSFER", "name_mn": "Банкны шилжүүлэг", "name_en": "Bank Transfer", "is_cash": 0},
		{"code": "MOBILE_PAYMENT", "name_mn": "Мобайл төлбөр", "name_en": "Mobile Payment", "is_cash": 0},
		{"code": "QPAY", "name_mn": "QPay", "name_en": "QPay", "is_cash": 0},
		{"code": "SOCIAL_PAY", "name_mn": "SocialPay", "name_en": "SocialPay", "is_cash": 0},
		{"code": "MONPAY", "name_mn": "MonPay", "name_en": "MonPay", "is_cash": 0},
		{"code": "MOST_MONEY", "name_mn": "Most Money", "name_en": "Most Money", "is_cash": 0},
	]
	
	for d in defaults:
		if not frappe.db.exists("eBarimt Payment Type", d["code"]):
			doc = frappe.new_doc("eBarimt Payment Type")
			doc.update(d)
			doc.insert(ignore_permissions=True)
	
	frappe.db.commit()
