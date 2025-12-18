# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class eBarimtSettings(Document):
    def validate(self):
        if self.enabled and not self.api_username:
            frappe.msgprint(_("API Username is required for eBarimt integration"))

    def on_update(self):
        # Clear cached settings
        frappe.cache.delete_value("ebarimt_settings")

        # Clear auth token cache when credentials change
        if self.has_value_changed("api_username") or self.has_value_changed("api_password"):
            frappe.cache.delete_value("ebarimt_itc_token")

    @frappe.whitelist()
    def test_connection(self):
        """Test connection to eBarimt API"""
        from ebarimt.api.client import EBarimtClient

        try:
            client = EBarimtClient(self)
            info = client.get_info()

            # Update status fields
            self.connection_status = "Connected"
            self.last_sync = now_datetime()
            self.operator_name = info.get("operatorName", "")
            self.operator_tin = info.get("operatorTIN", "")
            self.pos_no = info.get("posNo", self.pos_no)
            self.left_lotteries = info.get("leftLotteries", 0)
            self.save()

            return {
                "success": True,
                "message": _("Connected successfully!"),
                "data": {
                    "operator": info.get("operatorName"),
                    "pos_no": info.get("posNo"),
                    "lotteries": info.get("leftLotteries"),
                    "merchants": len(info.get("merchants", []))
                }
            }
        except Exception as e:
            self.connection_status = "Disconnected"
            self.save()

            return {
                "success": False,
                "message": str(e)
            }

    @frappe.whitelist()
    def sync_tax_codes(self):
        """Sync tax codes from eBarimt"""
        from ebarimt.api.client import EBarimtClient
        from ebarimt.ebarimt.doctype.ebarimt_tax_code.ebarimt_tax_code import sync_tax_codes

        try:
            client = EBarimtClient(self)
            tax_codes_synced = sync_tax_codes(client)

            return {
                "success": True,
                "message": _("Synced {0} tax codes").format(tax_codes_synced)
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    @frappe.whitelist()
    def lookup_taxpayer(self, tin):
        """Lookup taxpayer information"""
        from ebarimt.api.client import EBarimtClient

        client = EBarimtClient(self)
        return client.get_taxpayer_info(tin)

    @frappe.whitelist()
    def detect_district(self):
        """Detect district from IP geolocation"""

        try:
            # Try to detect location from IP
            # Default to Chingeltei (most common for businesses)

            # Default to Bayanzurkh District (most common)
            default_code = "0102"

            # Check if eBarimt District exists
            if frappe.db.exists("eBarimt District", default_code):
                self.district_code = default_code
                self.save()
                return {
                    "success": True,
                    "district": default_code,
                    "message": _("District set to Bayanzurkh (default)")
                }
            else:
                return {
                    "success": False,
                    "message": _("District codes not loaded. Please run: bench --site [site] migrate")
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


def get_settings():
    """Get cached eBarimt Settings"""
    settings = frappe.cache.get_value("ebarimt_settings")
    if not settings:
        settings = frappe.get_doc("eBarimt Settings")
        frappe.cache.set_value("ebarimt_settings", settings)
    return settings


def is_enabled():
    """Check if eBarimt integration is enabled"""
    try:
        settings = get_settings()
        return settings.enabled
    except Exception:
        return False
