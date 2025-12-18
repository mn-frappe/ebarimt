# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class eBarimtReceiptLog(Document):
    def before_insert(self):
        settings = frappe.get_cached_doc("eBarimt Settings")
        self.environment = settings.environment

    @frappe.whitelist()
    def void_receipt(self):
        """Void this receipt"""
        if self.status != "Success":
            frappe.throw(_("Can only void successful receipts"))

        if self.bill_type == "B2B_RECEIPT":
            frappe.throw(_("Cannot void B2B receipts. Please create a return invoice instead."))

        from ebarimt.api.client import EBarimtClient

        client = EBarimtClient()

        try:
            result = client.delete_receipt(
                self.receipt_id,
                self.receipt_date.strftime("%Y-%m-%d %H:%M:%S") if self.receipt_date else None
            )

            self.status = "Voided"
            self.response_data = json.dumps(result)
            self.save()

            frappe.msgprint(_("Receipt voided successfully"))
            return {"success": True}

        except Exception as e:
            self.error_message = str(e)
            self.save()
            frappe.throw(str(e))


def create_receipt_log(invoice_doc, receipt_response, bill_type="B2C_RECEIPT"):
    """
    Create eBarimt Receipt Log from API response

    Args:
        invoice_doc: Sales Invoice or POS Invoice document
        receipt_response: API response from create_receipt
        bill_type: B2C_RECEIPT or B2B_RECEIPT

    Returns:
        eBarimt Receipt Log document
    """
    settings = frappe.get_cached_doc("eBarimt Settings")

    log = frappe.new_doc("eBarimt Receipt Log")

    # Link to invoice
    if invoice_doc.doctype == "Sales Invoice":
        log.sales_invoice = invoice_doc.name
    elif invoice_doc.doctype == "POS Invoice":
        log.pos_invoice = invoice_doc.name

    # Receipt details
    log.bill_type = bill_type
    log.status = "Success" if receipt_response.get("success", True) else "Failed"
    log.environment = settings.environment

    # From response
    log.receipt_id = receipt_response.get("billId") or receipt_response.get("id")
    log.lottery_number = receipt_response.get("lottery")
    log.qr_data = receipt_response.get("qrData")
    log.internal_id = receipt_response.get("internalCode")
    log.receipt_date = now_datetime()

    # Amounts
    log.total_amount = flt(receipt_response.get("amount", invoice_doc.grand_total))
    log.vat_amount = flt(receipt_response.get("vat", 0))
    log.city_tax = flt(receipt_response.get("cityTax", 0))
    log.cash_amount = flt(receipt_response.get("cashAmount", 0))
    log.non_cash_amount = flt(receipt_response.get("nonCashAmount", 0))

    # Parties
    log.merchant_tin = settings.merchant_tin
    log.customer_tin = receipt_response.get("customerTin") or getattr(invoice_doc, "custom_customer_tin", "")
    log.district_code = settings.district_code
    log.pos_no = settings.pos_no

    # Store full response
    log.response_data = json.dumps(receipt_response)

    # Return info
    if receipt_response.get("returnBillId"):
        log.is_return = 1
        log.return_receipt_id = receipt_response.get("returnBillId")

    log.insert(ignore_permissions=True)
    frappe.db.commit()

    return log


def get_receipt_for_invoice(invoice_name, invoice_type="Sales Invoice"):
    """Get eBarimt Receipt Log for an invoice"""
    field = "sales_invoice" if invoice_type == "Sales Invoice" else "pos_invoice"

    logs = frappe.get_all(
        "eBarimt Receipt Log",
        filters={field: invoice_name},
        fields=["name", "receipt_id", "lottery_number", "status", "qr_data"],
        order_by="creation desc",
        limit=1
    )

    return logs[0] if logs else None
