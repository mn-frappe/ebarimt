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
            "fieldname": "creation",
            "label": _("Date/Time"),
            "fieldtype": "Datetime",
            "width": 160,
        },
        {
            "fieldname": "name",
            "label": _("Log ID"),
            "fieldtype": "Link",
            "options": "eBarimt Receipt Log",
            "width": 120,
        },
        {
            "fieldname": "reference_name",
            "label": _("Invoice"),
            "fieldtype": "Dynamic Link",
            "options": "reference_type",
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
            "fieldname": "total_amount",
            "label": _("Amount"),
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "fieldname": "error_message",
            "label": _("Error Message"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "retry_count",
            "label": _("Retries"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "last_retry",
            "label": _("Last Retry"),
            "fieldtype": "Datetime",
            "width": 160,
        },
    ]


def get_data(filters):
    conditions = ["erl.status = 'Failed'"]
    values = {}

    if filters.get("from_date"):
        conditions.append("erl.creation >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("erl.creation <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("customer"):
        conditions.append("erl.customer = %(customer)s")
        values["customer"] = filters.get("customer")

    if filters.get("company"):
        conditions.append("erl.company = %(company)s")
        values["company"] = filters.get("company")

    if filters.get("error_type"):
        conditions.append("erl.error_message LIKE %(error_type)s")
        values["error_type"] = f"%{filters.get('error_type')}%"

    where_clause = " AND ".join(conditions)

    data = frappe.db.sql(
        f"""
        SELECT
            erl.creation,
            erl.name,
            erl.reference_type,
            erl.reference_name,
            erl.customer,
            erl.total_amount,
            erl.error_message,
            erl.retry_count,
            erl.last_retry
        FROM `tabeBarimt Receipt Log` erl
        WHERE {where_clause}
        ORDER BY erl.creation DESC
    """,
        values,
        as_dict=True,
    )

    return data


def get_chart_data(data):
    # Group errors by type
    error_types = {}
    for row in data:
        error_msg = row.get("error_message") or "Unknown"
        # Truncate for grouping
        error_key = error_msg[:50] if len(error_msg) > 50 else error_msg
        error_types[error_key] = error_types.get(error_key, 0) + 1

    # Top 10 error types
    sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "data": {
            "labels": [e[0] for e in sorted_errors],
            "datasets": [{"name": _("Count"), "values": [e[1] for e in sorted_errors]}],
        },
        "type": "bar",
        "colors": ["#ff5858"],
    }


def get_summary(data):
    total_failed = len(data)
    total_amount = sum(row.get("total_amount") or 0 for row in data)
    high_retry = len([r for r in data if (r.get("retry_count") or 0) >= 3])
    recent_24h = len(
        [
            r
            for r in data
            if r.get("creation")
            and (
                frappe.utils.now_datetime() - r.get("creation")  # pyright: ignore[reportAttributeAccessIssue]
            ).total_seconds()
            < 86400
        ]
    )

    return [
        {
            "value": total_failed,
            "indicator": "Red",
            "label": _("Total Failed"),
            "datatype": "Int",
        },
        {
            "value": recent_24h,
            "indicator": "Orange",
            "label": _("Failed (24h)"),
            "datatype": "Int",
        },
        {
            "value": high_retry,
            "indicator": "Red",
            "label": _("High Retry Count"),
            "datatype": "Int",
        },
        {
            "value": total_amount,
            "indicator": "Red",
            "label": _("Amount at Risk"),
            "datatype": "Currency",
        },
    ]
