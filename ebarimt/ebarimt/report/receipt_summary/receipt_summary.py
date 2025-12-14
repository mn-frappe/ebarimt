# Copyright (c) 2024, Orchlon and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    summary = get_summary(data)

    return columns, data, None, chart, summary


def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "fieldname": "invoice_name",
            "label": _("Invoice"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150,
        },
        {
            "fieldname": "customer",
            "label": _("Customer"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150,
        },
        {
            "fieldname": "receipt_id",
            "label": _("eBarimt ID"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "lottery_number",
            "label": _("Lottery"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "vat_amount",
            "label": _("VAT Amount"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "city_tax",
            "label": _("City Tax"),
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "fieldname": "total_amount",
            "label": _("Total"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "receipt_type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 80,
        },
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("erl.posting_date >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("erl.posting_date <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("customer"):
        conditions.append("erl.customer = %(customer)s")
        values["customer"] = filters.get("customer")

    if filters.get("status"):
        conditions.append("erl.status = %(status)s")
        values["status"] = filters.get("status")

    if filters.get("company"):
        conditions.append("erl.company = %(company)s")
        values["company"] = filters.get("company")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql(
        f"""
        SELECT
            erl.posting_date,
            erl.reference_name as invoice_name,
            erl.customer,
            erl.receipt_id,
            erl.lottery_number,
            erl.vat_amount,
            erl.city_tax,
            erl.total_amount,
            erl.status,
            erl.receipt_type
        FROM `tabeBarimt Receipt Log` erl
        WHERE {where_clause}
        ORDER BY erl.posting_date DESC, erl.creation DESC
    """,
        values,
        as_dict=True,
    )

    return data


def get_chart_data(data):
    # Group by date for chart
    date_totals = {}
    for row in data:
        date = str(row.get("posting_date"))
        if date not in date_totals:
            date_totals[date] = {"vat": 0, "total": 0, "count": 0}
        date_totals[date]["vat"] += row.get("vat_amount") or 0
        date_totals[date]["total"] += row.get("total_amount") or 0
        date_totals[date]["count"] += 1

    labels = sorted(date_totals.keys())[-30:]  # Last 30 days
    vat_values = [date_totals[d]["vat"] for d in labels]
    total_values = [date_totals[d]["total"] for d in labels]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("VAT Amount"), "values": vat_values},
                {"name": _("Total Amount"), "values": total_values},
            ],
        },
        "type": "line",
        "colors": ["#7575ff", "#ffa00a"],
    }


def get_summary(data):
    total_receipts = len(data)
    total_vat = sum(row.get("vat_amount") or 0 for row in data)
    total_city_tax = sum(row.get("city_tax") or 0 for row in data)
    total_amount = sum(row.get("total_amount") or 0 for row in data)
    success_count = len([r for r in data if r.get("status") == "Sent"])

    return [
        {
            "value": total_receipts,
            "indicator": "Blue",
            "label": _("Total Receipts"),
            "datatype": "Int",
        },
        {
            "value": success_count,
            "indicator": "Green",
            "label": _("Successful"),
            "datatype": "Int",
        },
        {
            "value": total_vat,
            "indicator": "Orange",
            "label": _("Total VAT"),
            "datatype": "Currency",
        },
        {
            "value": total_city_tax,
            "indicator": "Purple",
            "label": _("Total City Tax"),
            "datatype": "Currency",
        },
        {
            "value": total_amount,
            "indicator": "Green",
            "label": _("Total Revenue"),
            "datatype": "Currency",
        },
    ]
