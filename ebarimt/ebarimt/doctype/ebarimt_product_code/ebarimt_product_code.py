# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBarimt Product Code - GS1 Classification with Tax Mapping

This DocType stores the GS1 Mongolia product classification codes
with associated tax configurations (VAT, City Tax, Excise).

Classification Hierarchy:
- Segment (2 digits): Major category
- Family (3 digits): Sub-category  
- Class (4 digits): Product group
- Brick (6 digits): Specific product

Tax Types:
- STANDARD: 10% VAT (most products)
- ZERO: 0% VAT (export, mining, etc. - codes 501-507)
- EXEMPT: VAT exempt (healthcare, education, etc. - codes 305-447)

City Tax: 2% applies to alcohol, tobacco, fuel in Ulaanbaatar
Excise: Requires OAT stamp for alcohol, tobacco, fuel products
"""

import frappe
from frappe.model.document import Document


class eBarimtProductCode(Document):
    def before_save(self):
        """Auto-fill hierarchy codes based on classification_code"""
        code = self.classification_code
        if not code:
            return
        
        # Parse hierarchy from code
        code_str = str(code).zfill(6)
        
        if len(code_str) >= 2:
            self.segment_code = code_str[:2]
        if len(code_str) >= 3:
            self.family_code = code_str[:3]
        if len(code_str) >= 4:
            self.class_code = code_str[:4]
        if len(code_str) >= 6:
            self.brick_code = code_str[:6]
        
        # Auto-detect excise type and city tax
        self._detect_excise_and_city_tax()
    
    def _detect_excise_and_city_tax(self):
        """Auto-detect excise type and city tax based on product category"""
        name_lower = (self.name_mn or "").lower()
        
        # Alcohol detection
        alcohol_keywords = ["архи", "виски", "пиво", "дарс", "ром", "джин", 
                          "коньяк", "ликёр", "спирт", "vodka", "wine", "beer"]
        for kw in alcohol_keywords:
            if kw in name_lower:
                self.excise_type = "Alcohol"
                self.city_tax_applicable = 1
                return
        
        # Tobacco detection
        tobacco_keywords = ["тамхи", "сигарет", "tobacco", "cigarette"]
        for kw in tobacco_keywords:
            if kw in name_lower:
                self.excise_type = "Tobacco"
                self.city_tax_applicable = 1
                return
        
        # Fuel detection
        fuel_keywords = ["бензин", "дизель", "түлш", "керосин", "газолин",
                        "gasoline", "diesel", "fuel", "kerosene"]
        for kw in fuel_keywords:
            if kw in name_lower:
                self.excise_type = "Fuel"
                self.city_tax_applicable = 1
                return


def get_product_tax_info(classification_code):
    """
    Get tax information for a product by classification code.
    
    Returns:
        dict: {
            "vat_type": "STANDARD|ZERO|EXEMPT",
            "vat_rate": 10|0,
            "city_tax_applicable": True|False,
            "city_tax_rate": 0.02|0,
            "excise_type": "Alcohol|Tobacco|Fuel"|None,
            "requires_oat_stamp": True|False
        }
    """
    product = frappe.db.get_value(
        "eBarimt Product Code",
        classification_code,
        ["vat_type", "city_tax_applicable", "excise_type", "oat_product_code"],
        as_dict=True
    )
    
    if not product:
        # Default to standard VAT
        return {
            "vat_type": "STANDARD",
            "vat_rate": 10,
            "city_tax_applicable": False,
            "city_tax_rate": 0,
            "excise_type": None,
            "requires_oat_stamp": False
        }
    
    vat_rate = 10 if product.vat_type == "STANDARD" else 0
    city_tax_rate = 0.02 if product.city_tax_applicable else 0
    requires_oat_stamp = bool(product.excise_type and product.oat_product_code)
    
    return {
        "vat_type": product.vat_type,
        "vat_rate": vat_rate,
        "city_tax_applicable": bool(product.city_tax_applicable),
        "city_tax_rate": city_tax_rate,
        "excise_type": product.excise_type,
        "requires_oat_stamp": requires_oat_stamp
    }


def calculate_item_taxes(amount, classification_code=None, include_vat=True):
    """
    Calculate taxes for an item amount based on product classification.
    
    Args:
        amount: Item amount (with or without VAT)
        classification_code: GS1 product code
        include_vat: Whether amount includes VAT (True for Mongolia)
    
    Returns:
        dict: {
            "net_amount": amount without taxes,
            "vat_amount": VAT amount,
            "city_tax_amount": City tax amount,
            "total_amount": Total with all taxes
        }
    """
    tax_info = get_product_tax_info(classification_code)
    
    if include_vat and tax_info["vat_rate"] > 0:
        # VAT is included in price (Mongolia standard)
        net_amount = amount * 100 / (100 + tax_info["vat_rate"])
        vat_amount = amount - net_amount
    else:
        net_amount = amount
        vat_amount = 0
    
    # City tax is calculated on net amount
    city_tax_amount = 0
    if tax_info["city_tax_applicable"]:
        city_tax_amount = net_amount * tax_info["city_tax_rate"]
    
    return {
        "net_amount": round(net_amount, 2),
        "vat_amount": round(vat_amount, 2),
        "city_tax_amount": round(city_tax_amount, 2),
        "total_amount": round(amount + city_tax_amount, 2),
        "tax_info": tax_info
    }
