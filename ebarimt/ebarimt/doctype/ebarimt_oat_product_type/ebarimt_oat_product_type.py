# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt OAT (Excise Tax) Product Type
Онцгой албан татварын барааны төрөл

From eBarimtOntsgoi.yaml documentation:
Product type codes for alcohol, tobacco, and fuel products
"""

import frappe
from frappe.model.document import Document


class eBarimtOATProductType(Document):
	pass


def load_default_oat_product_types():
	"""
	Load default OAT product types from documentation
	
	Based on eBarimtOntsgoi.yaml:
	- Codes 4-9: Domestic alcohol/tobacco/wine
	- Codes 13-17: Import alcohol/tobacco/wine
	- Codes 22-25: Domestic/Import beer/spirit
	- Codes 27-33: Domestic/Import fuel products
	"""
	defaults = [
		# Domestic Alcohol
		{"code": 4, "name_mn": "Цагаан архи, ликёр, кордиал ба спиртлэг бусад ундаа", "name_en": "Vodka, Liqueur, Cordial (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		{"code": 5, "name_mn": "Коньяк, виски, ром, джин", "name_en": "Cognac, Whisky, Rum, Gin (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		{"code": 6, "name_mn": "Шимийн архи", "name_en": "Fermented Alcohol (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		
		# Domestic Tobacco
		{"code": 7, "name_mn": "Янжуур тамхи", "name_en": "Cigarettes (Domestic)", "category": "Tobacco", "origin": "Domestic", "is_default": 1},
		{"code": 8, "name_mn": "Дүнсэн тамхи", "name_en": "Pipe Tobacco (Domestic)", "category": "Tobacco", "origin": "Domestic", "is_default": 1},
		
		# Domestic Wine
		{"code": 9, "name_mn": "Дарс", "name_en": "Wine (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		
		# Import Alcohol
		{"code": 13, "name_mn": "Цагаан архи, ликёр, кордиал ба спиртлэг бусад ундаа", "name_en": "Vodka, Liqueur, Cordial (Import)", "category": "Alcohol", "origin": "Import", "is_default": 1},
		{"code": 14, "name_mn": "Коньяк, виски, ром, джин", "name_en": "Cognac, Whisky, Rum, Gin (Import)", "category": "Alcohol", "origin": "Import", "is_default": 1},
		
		# Import Tobacco
		{"code": 15, "name_mn": "Дүнсэн тамхи", "name_en": "Pipe Tobacco (Import)", "category": "Tobacco", "origin": "Import", "is_default": 1},
		{"code": 16, "name_mn": "Янжуур тамхи", "name_en": "Cigarettes (Import)", "category": "Tobacco", "origin": "Import", "is_default": 1},
		
		# Import Wine
		{"code": 17, "name_mn": "Дарс", "name_en": "Wine (Import)", "category": "Alcohol", "origin": "Import", "is_default": 1},
		
		# Beer
		{"code": 22, "name_mn": "Пиво", "name_en": "Beer (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		{"code": 24, "name_mn": "Пиво", "name_en": "Beer (Import)", "category": "Alcohol", "origin": "Import", "is_default": 1},
		
		# Spirit
		{"code": 23, "name_mn": "Спирт", "name_en": "Spirit (Domestic)", "category": "Alcohol", "origin": "Domestic", "is_default": 1},
		{"code": 25, "name_mn": "Спирт", "name_en": "Spirit (Import)", "category": "Alcohol", "origin": "Import", "is_default": 1},
		
		# Domestic Fuel
		{"code": 27, "name_mn": "Автобензин", "name_en": "Gasoline (Domestic)", "category": "Fuel", "origin": "Domestic", "is_default": 1},
		{"code": 28, "name_mn": "Дизелийн түлш", "name_en": "Diesel (Domestic)", "category": "Fuel", "origin": "Domestic", "is_default": 1},
		{"code": 29, "name_mn": "Газрын тосны үйлдвэрлэлийн дайвар бүтээгдэхүүн, керосин", "name_en": "Petroleum Products, Kerosene (Domestic)", "category": "Fuel", "origin": "Domestic", "is_default": 1},
		
		# Import Fuel
		{"code": 31, "name_mn": "Автобензин", "name_en": "Gasoline (Import)", "category": "Fuel", "origin": "Import", "is_default": 1},
		{"code": 32, "name_mn": "Дизелийн түлш", "name_en": "Diesel (Import)", "category": "Fuel", "origin": "Import", "is_default": 1},
		{"code": 33, "name_mn": "Газрын тосны үйлдвэрлэлийн дайвар бүтээгдэхүүн, керосин", "name_en": "Petroleum Products, Kerosene (Import)", "category": "Fuel", "origin": "Import", "is_default": 1},
	]
	
	for d in defaults:
		if not frappe.db.exists("eBarimt OAT Product Type", d["code"]):
			doc = frappe.new_doc("eBarimt OAT Product Type")
			doc.update(d)
			doc.insert(ignore_permissions=True)
	
	frappe.db.commit()


# OAT Stamp Type codes
OAT_STAMP_TYPES = {
	3: {"name_mn": "Дотоодын зах зээл", "name_en": "Domestic Market"},
	4: {"name_mn": "Чөлөөт бүс", "name_en": "Free Zone"},
	5: {"name_mn": "Duty Free", "name_en": "Duty Free"},
	6: {"name_mn": "Экспортын бүтээгдэхүүн", "name_en": "Export Product"},
}
