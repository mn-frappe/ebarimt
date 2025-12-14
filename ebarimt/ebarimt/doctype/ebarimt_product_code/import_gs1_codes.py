# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Import GS1 Product Codes from QPayAPIv2.xlsx

This script parses the GS1 sheet and VAT codes sheet from the QPay API documentation
and imports them into the eBarimt Product Code DocType.
"""

import frappe
from frappe.utils import cint, flt


# VAT Zero Codes (0% VAT) - from QPayAPIv2.xlsx "Vat Free, Zero" sheet
VAT_ZERO_CODES = {
    "501": "Монгол Улсын нутаг дэвсгэрээс экспортод гаргасан бараа",
    "502": "Олон улсын зорчигч болон ачаа тээврийн үйлчилгээ",
    "503": "Монгол Улсын нутаг дэвсгэрээс гадна үзүүлсэн үйлчилгээ",
    "504": "Монгол Улсад оршин суугч бус этгээдэд үзүүлсэн үйлчилгээ",
    "505": "Олон улсын нислэгт үзүүлэх үйлчилгээ",
    "506": "Төрийн одон медаль, мөнгөн тэмдэгт, зоос",
    "507": "Ашигт малтмалын эцсийн бүтээгдэхүүн",
}

# VAT Exempt Codes (exempt from VAT) - from QPayAPIv2.xlsx "Vat Free, Zero" sheet
VAT_EXEMPT_CODES = {
    "305": "Хөгжлийн бэрхшээлтэй иргэний тусгай хэрэгсэл",
    "307": "Иргэний агаарын хөлөг, хөдөлгүүр, эд анги",
    "308": "Орон сууц борлуулалтын орлого",
    "310": "Эмчилгээний цус, цусан бүтээгдэхүүн, эд эрхтэн",
    "311": "Хийн түлш, тоног төхөөрөмж",
    "313": "Борлуулсан алт",
    "315": "Эрдэм шинжилгээний туршилтын бүтээгдэхүүн",
    "316": "Хөрөнгөөр баталгаажсан үнэт цаас",
    "318": "Газар тариалангийн үр тариа, төмс, хүнсний ногоо, гурил",
    "319": "Дотоодод боловсруулсан мах, дотор эрхтэн",
    "320": "Дотоодын сүү, сүүн бүтээгдэхүүн",
    "401": "Валют солих үйлчилгээ",
    "402": "Банкны үйлчилгээ",
    "403": "Даатгал, давхар даатгал",
    "404": "Үнэт цаас, хувьцаа үйлчилгээ",
    "405": "Зээл олгох үйлчилгээ",
    "406": "Нийгмийн даатгалын сангийн хүү",
    "407": "Банкны зээлийн хүү, ногдол ашиг",
    "408": "Орон сууц хөлслүүлэх үйлчилгээ",
    "409": "Боловсрол, мэргэжил олгох үйлчилгээ",
    "410": "Эрүүл мэндийн үйлчилгээ",
    "411": "Шашны байгууллагын үйлчилгээ",
    "412": "Төрийн байгууллагын үйлчилгээ",
    "413": "Нийтийн тээврийн үйлчилгээ",
    "414": "Гадаадын жуулчинд үзүүлсэн үйлчилгээ",
    "419": "ЖДҮ тоног төхөөрөмж, сэлбэг",
    "421": "Экспортын ашигт малтмал",
    "423": "Инновацийн түүхий эд, материал",
    "425": "Экспортын ноолуур, арьс шир",
    "426": "Соёлын өв судалгааны материал",
    "428": "Газрын тос, дээж",
    "429": "Чөлөөт бүсийн бараа (3 сая хүртэл)",
    "430": "Соёлын өв сэргээн засварлах үйлчилгээ",
    "431": "Оршуулгын үйлчилгээ",
    "433": "Сэргээгдэх эрчим хүчний тоног төхөөрөмж",
    "434": "ХАА трактор, комбайн, бордоо",
    "436": "Мал эмнэлэгийн үйлчилгээ",
    "437": "Нотариатын үйлчилгээ",
    "438": "Санхүүгийн хэрэгсэл арилжих үйлчилгээ",
    "439": "Таван толгой сайжруулсан түлш",
    "443": "Ирээдүйн өв сангийн орлого",
    "444": "Инновацийн бүтээгдэхүүн",
    "445": "Виртуал хөрөнгийн үйлчилгээ",
    "447": "Малчны мал, мах, сүү, арьс, ноолуур",
}


def import_gs1_codes_from_excel(file_path=None):
    """
    Import GS1 codes from QPayAPIv2.xlsx file.
    
    Args:
        file_path: Path to Excel file. Defaults to /opt/docs/QPayAPIv2.xlsx
    """
    try:
        import pandas as pd
    except ImportError:
        frappe.throw("pandas is required for Excel import. Install with: pip install pandas openpyxl")
    
    if not file_path:
        file_path = "/opt/docs/QPayAPIv2.xlsx"
    
    # Read GS1 sheet
    df = pd.read_excel(file_path, sheet_name="GS1")
    
    # Parse the hierarchical structure
    current_segment = None
    current_segment_name = None
    current_family = None
    current_family_name = None
    current_class = None
    current_class_name = None
    
    imported = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        try:
            # Skip header rows
            if idx < 2:
                continue
            
            # Get values from columns
            col1 = row.get("Unnamed: 1")  # Segment number
            col2 = row.get("Unnamed: 2")  # Family code (3 digits)
            col3 = row.get("Unnamed: 3")  # Class code (4 digits)
            col4 = row.get("Unnamed: 4")  # Brick code (5-6 digits)
            col5 = row.get("Unnamed: 5")  # Full brick code (6 digits)
            col6 = row.get("Unnamed: 6")  # Name
            
            # Determine what type of row this is
            name = str(col6).strip() if pd.notna(col6) else None
            if not name or name == "nan":
                continue
            
            classification_code = None
            code_level = None
            
            # Check if it's a segment (column 1 has number)
            if pd.notna(col1) and str(col1).replace(".", "").isdigit():
                segment_num = int(float(col1))
                current_segment = str(segment_num).zfill(2)
                current_segment_name = name
                # Don't create segment records, they're categories
                continue
            
            # Check if it's a family (column 2 has 3-digit code)
            if pd.notna(col2) and str(col2).replace(".", "").isdigit():
                code = str(int(float(col2))).zfill(3)
                if len(code) == 3:
                    classification_code = code
                    code_level = "Family"
                    current_family = code
                    current_family_name = name
                    current_class = None
                    current_class_name = None
            
            # Check if it's a class (column 3 has 4-digit code)
            elif pd.notna(col3) and str(col3).replace(".", "").isdigit():
                code = str(int(float(col3))).zfill(4)
                if len(code) == 4:
                    classification_code = code
                    code_level = "Class"
                    current_class = code
                    current_class_name = name
            
            # Check if it's a brick (column 4 or 5 has 6-digit code)
            elif pd.notna(col5) and str(col5).replace(".", "").isdigit():
                code = str(int(float(col5))).zfill(6)
                if len(code) == 6:
                    classification_code = code
                    code_level = "Brick"
            elif pd.notna(col4) and str(col4).replace(".", "").isdigit():
                code = str(int(float(col4)))
                if len(code) >= 4:
                    classification_code = code.zfill(6)
                    code_level = "Brick"
            
            if not classification_code:
                continue
            
            # Check if already exists
            if frappe.db.exists("eBarimt Product Code", classification_code):
                skipped += 1
                continue
            
            # Create product code
            doc = frappe.new_doc("eBarimt Product Code")
            doc.classification_code = classification_code
            doc.name_mn = name
            doc.code_level = code_level
            doc.enabled = 1
            doc.vat_type = "STANDARD"
            
            # Set hierarchy
            if current_segment:
                doc.segment_code = current_segment
                doc.segment_name = current_segment_name
            if current_family:
                doc.family_code = current_family
                doc.family_name = current_family_name
            if current_class:
                doc.class_code = current_class
                doc.class_name = current_class_name
            if code_level == "Brick":
                doc.brick_code = classification_code
                doc.brick_name = name
            
            # Auto-detect excise and city tax (done in before_save)
            doc.insert(ignore_permissions=True)
            imported += 1
            
            if imported % 500 == 0:
                frappe.db.commit()
                frappe.publish_progress(
                    percent=int(idx / len(df) * 100),
                    title="Importing GS1 Codes",
                    description=f"Imported {imported} codes..."
                )
        
        except Exception as e:
            frappe.log_error(f"Error importing row {idx}: {str(e)}", "GS1 Import Error")
            continue
    
    frappe.db.commit()
    return {"imported": imported, "skipped": skipped}


def import_vat_codes():
    """Import VAT Zero and Exempt code definitions."""
    imported = 0
    
    # Import VAT Zero codes
    for code, name in VAT_ZERO_CODES.items():
        if not frappe.db.exists("eBarimt Product Code", f"VAT_{code}"):
            doc = frappe.new_doc("eBarimt Product Code")
            doc.classification_code = f"VAT_{code}"
            doc.name_mn = name
            doc.name_en = f"VAT Zero - Code {code}"
            doc.code_level = "Brick"
            doc.vat_type = "ZERO"
            doc.vat_code = code
            doc.vat_code_name = name
            doc.enabled = 1
            doc.insert(ignore_permissions=True)
            imported += 1
    
    # Import VAT Exempt codes
    for code, name in VAT_EXEMPT_CODES.items():
        if not frappe.db.exists("eBarimt Product Code", f"VAT_{code}"):
            doc = frappe.new_doc("eBarimt Product Code")
            doc.classification_code = f"VAT_{code}"
            doc.name_mn = name
            doc.name_en = f"VAT Exempt - Code {code}"
            doc.code_level = "Brick"
            doc.vat_type = "EXEMPT"
            doc.vat_code = code
            doc.vat_code_name = name
            doc.enabled = 1
            doc.insert(ignore_permissions=True)
            imported += 1
    
    frappe.db.commit()
    return imported


@frappe.whitelist()
def sync_product_codes(file_path=None):
    """
    Sync product codes from Excel file.
    
    This is the main entry point for importing/syncing codes.
    """
    frappe.only_for("System Manager")
    
    # Import VAT codes first
    vat_imported = import_vat_codes()
    frappe.msgprint(f"Imported {vat_imported} VAT codes")
    
    # Import GS1 codes
    if file_path or frappe.os.path.exists("/opt/docs/QPayAPIv2.xlsx"):
        result = import_gs1_codes_from_excel(file_path)
        frappe.msgprint(f"GS1 Import: {result['imported']} imported, {result['skipped']} skipped")
        return result
    else:
        frappe.msgprint("QPayAPIv2.xlsx not found. Only VAT codes imported.")
        return {"imported": vat_imported, "skipped": 0}


def load_default_product_codes():
    """Load commonly used product codes with correct tax settings."""
    defaults = [
        # General merchandise - Standard VAT
        {"code": "999999", "name_mn": "Бусад бараа бүтээгдэхүүн", "name_en": "Other Products", 
         "vat_type": "STANDARD", "city_tax": 0, "excise": None},
        
        # Alcohol - City Tax + Excise
        {"code": "500100", "name_mn": "Архи, спиртлэг ундаа", "name_en": "Alcoholic Beverages",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Alcohol"},
        {"code": "500101", "name_mn": "Цагаан архи", "name_en": "Vodka",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Alcohol"},
        {"code": "500102", "name_mn": "Пиво", "name_en": "Beer",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Alcohol"},
        {"code": "500103", "name_mn": "Дарс", "name_en": "Wine",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Alcohol"},
        
        # Tobacco - City Tax + Excise
        {"code": "500200", "name_mn": "Тамхи", "name_en": "Tobacco Products",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Tobacco"},
        {"code": "500201", "name_mn": "Янжуур тамхи", "name_en": "Cigarettes",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Tobacco"},
        
        # Fuel - City Tax + Excise
        {"code": "500300", "name_mn": "Шатахуун", "name_en": "Fuel",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Fuel"},
        {"code": "500301", "name_mn": "Автобензин", "name_en": "Gasoline",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Fuel"},
        {"code": "500302", "name_mn": "Дизель түлш", "name_en": "Diesel",
         "vat_type": "STANDARD", "city_tax": 1, "excise": "Fuel"},
        
        # Healthcare - VAT Exempt
        {"code": "410001", "name_mn": "Эрүүл мэндийн үйлчилгээ", "name_en": "Healthcare Services",
         "vat_type": "EXEMPT", "vat_code": "410", "city_tax": 0, "excise": None},
        {"code": "410002", "name_mn": "Эм", "name_en": "Medicine/Drugs",
         "vat_type": "EXEMPT", "vat_code": "410", "city_tax": 0, "excise": None},
        
        # Education - VAT Exempt
        {"code": "409001", "name_mn": "Боловсролын үйлчилгээ", "name_en": "Education Services",
         "vat_type": "EXEMPT", "vat_code": "409", "city_tax": 0, "excise": None},
        
        # Food (domestic agriculture) - VAT Exempt
        {"code": "318001", "name_mn": "Үр тариа (дотоодын)", "name_en": "Grains (Domestic)",
         "vat_type": "EXEMPT", "vat_code": "318", "city_tax": 0, "excise": None},
        {"code": "319001", "name_mn": "Мах (дотоодын)", "name_en": "Meat (Domestic)",
         "vat_type": "EXEMPT", "vat_code": "319", "city_tax": 0, "excise": None},
        {"code": "320001", "name_mn": "Сүү (дотоодын)", "name_en": "Milk (Domestic)",
         "vat_type": "EXEMPT", "vat_code": "320", "city_tax": 0, "excise": None},
    ]
    
    imported = 0
    for d in defaults:
        if not frappe.db.exists("eBarimt Product Code", d["code"]):
            doc = frappe.new_doc("eBarimt Product Code")
            doc.classification_code = d["code"]
            doc.name_mn = d["name_mn"]
            doc.name_en = d["name_en"]
            doc.code_level = "Brick"
            doc.vat_type = d["vat_type"]
            doc.vat_code = d.get("vat_code")
            doc.city_tax_applicable = d["city_tax"]
            doc.excise_type = d["excise"]
            doc.enabled = 1
            doc.insert(ignore_permissions=True)
            imported += 1
    
    frappe.db.commit()
    return imported


def create_items_from_product_codes(force=False):
    """
    Create ERPNext Items from eBarimt Product Codes.
    
    AVOIDS DUPLICATES: Checks if Item already exists before creating.
    Links Items to eBarimt Product Code via custom field.
    
    Args:
        force: If True, update existing items
    
    Returns:
        dict: Import statistics
    """
    if not frappe.db.exists("DocType", "Item"):
        return {"status": "skipped", "message": "ERPNext not installed"}
    
    # Create Item Group if needed
    gs1_group = "GS1 Products"
    if not frappe.db.exists("Item Group", gs1_group):
        parent_group = "All Item Groups"
        if not frappe.db.exists("Item Group", parent_group):
            return {"status": "skipped", "message": "ERPNext setup not complete"}
        
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": gs1_group,
            "parent_item_group": parent_group,
            "is_group": 0
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    
    # Get all eBarimt Product Codes
    product_codes = frappe.get_all(
        "eBarimt Product Code",
        filters={"enabled": 1},
        fields=["classification_code", "name_mn", "name_en"]
    )
    
    # Get ALL existing items (not just GS1 group) to avoid duplicates
    all_existing_items = set(frappe.get_all("Item", pluck="item_code"))
    
    # Check for custom field
    has_product_code_field = frappe.db.exists(
        "Custom Field",
        {"dt": "Item", "fieldname": "custom_ebarimt_product_code"}
    )
    
    created = 0
    updated = 0
    skipped = 0
    
    for pc in product_codes:
        code = pc.classification_code
        name = pc.name_mn or pc.name_en or code
        
        if code in all_existing_items:
            if force:
                # Update existing item
                update_data = {"item_name": name[:140], "description": name}
                if has_product_code_field:
                    update_data["custom_ebarimt_product_code"] = code
                frappe.db.set_value("Item", code, update_data)
                updated += 1
            else:
                skipped += 1
        else:
            # Create new item
            item_data = {
                "doctype": "Item",
                "item_code": code,
                "item_name": name[:140],
                "item_group": gs1_group,
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_sales_item": 1,
                "is_purchase_item": 0,
                "description": name,
                "disabled": 0,
            }
            
            if has_product_code_field:
                item_data["custom_ebarimt_product_code"] = code
            
            try:
                item = frappe.get_doc(item_data)
                item.flags.ignore_permissions = True
                item.flags.ignore_mandatory = True
                item.insert()
                created += 1
                all_existing_items.add(code)
            except Exception:
                skipped += 1
        
        if (created + updated) % 500 == 0:
            frappe.db.commit()
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(product_codes)
    }


def sync_to_qpay():
    """
    Sync eBarimt Product Codes to QPay Product Code.
    
    This ensures QPay has the same codes with tax info from eBarimt.
    Maps eBarimt VAT types to QPay VAT types:
    - STANDARD -> Standard
    - ZERO -> Zero Rate
    - EXEMPT -> VAT Free
    """
    if not frappe.db.exists("DocType", "QPay Product Code"):
        return {"status": "skipped", "message": "QPay not installed"}
    
    # VAT type mapping: eBarimt -> QPay
    vat_type_map = {
        "STANDARD": "Standard",
        "ZERO": "Zero Rate",
        "EXEMPT": "VAT Free"
    }
    
    # Get all eBarimt codes
    ebarimt_codes = frappe.get_all(
        "eBarimt Product Code",
        filters={"enabled": 1},
        fields=["classification_code", "name_mn", "code_level", "vat_type"]
    )
    
    # Get existing QPay codes
    existing_qpay = set(frappe.get_all("QPay Product Code", pluck="product_code"))
    
    created = 0
    updated = 0
    
    for ec in ebarimt_codes:
        code = ec.classification_code
        qpay_vat_type = vat_type_map.get(ec.vat_type, "Standard")
        
        if code in existing_qpay:
            frappe.db.set_value("QPay Product Code", code, {
                "description": ec.name_mn,
                "code_level": ec.code_level,
                "vat_type": qpay_vat_type
            })
            updated += 1
        else:
            try:
                frappe.get_doc({
                    "doctype": "QPay Product Code",
                    "product_code": code,
                    "description": ec.name_mn,
                    "code_level": ec.code_level or "Brick",
                    "vat_type": qpay_vat_type,
                    "enabled": 1
                }).insert(ignore_permissions=True)
                created += 1
            except Exception:
                pass
        
        if (created + updated) % 500 == 0:
            frappe.db.commit()
    
    frappe.db.commit()
    
    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "total": len(ebarimt_codes)
    }
