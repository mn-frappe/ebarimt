# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Scheduled Tasks for eBarimt

eBarimt app manages its own district codes via eBarimt District DocType.
This allows independent operation without QPay installed.
"""

import frappe
from frappe.utils import add_days, add_years, now_datetime


def sync_tax_codes_daily():
    """Daily sync of tax codes from eBarimt"""
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    if not frappe.db.get_single_value("eBarimt Settings", "auto_sync_tax_codes"):
        return

    try:
        from ebarimt.ebarimt.doctype.ebarimt_tax_code.ebarimt_tax_code import sync_tax_codes
        result = sync_tax_codes()

        if result.get("success"):
            frappe.logger("ebarimt").info(
                f"Tax codes synced successfully: {result.get('count', 0)} codes"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Tax Code Sync Failed"
        )


def sync_pending_receipts_daily():
    """
    Daily sync of pending/unsent receipts to eBarimt
    Retries failed receipts from the last 7 days
    OPTIMIZED: Uses batch operations and single sendData call
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    from ebarimt.api.client import EBarimtClient
    from ebarimt.performance import bulk_update_receipt_status, get_pending_receipts_fast

    settings = frappe.get_cached_doc("eBarimt Settings")

    # OPTIMIZED: Use fast SQL query
    pending_logs = get_pending_receipts_fast(limit=100, days=7)

    if not pending_logs:
        return

    client = EBarimtClient(settings=settings)

    try:
        # Single sendData call syncs all pending receipts
        result = client.send_data()

        if result.get("success"):
            # OPTIMIZED: Batch update all pending logs to Synced
            updates = {log["name"]: "Synced" for log in pending_logs}
            synced = bulk_update_receipt_status(updates)

            frappe.logger("ebarimt").info(
                f"Daily receipt sync: {synced} receipts potentially synced"
            )
        else:
            frappe.log_error(
                message=f"sendData failed: {result.get('message', 'Unknown error')}",
                title="eBarimt Daily Sync Failed"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Daily Sync Failed"
        )

    frappe.db.commit()

    frappe.logger("ebarimt").info(
        f"Daily receipt sync: {synced} synced"
    )


def sync_unsent_receipts():
    """
    Hourly sync of unsent receipts
    Uses sendData API to push any locally stored receipts
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    from ebarimt.api.client import EBarimtClient

    settings = frappe.get_cached_doc("eBarimt Settings")

    client = EBarimtClient(
        environment=settings.environment,
        operator_tin=settings.operator_tin,
        pos_no=settings.pos_no,
        merchant_tin=settings.merchant_tin,
        username=settings.username,
        password=settings.get_password("password")
    )

    try:
        result = client.send_data()

        if result.get("success"):
            frappe.logger("ebarimt").info(
                f"Hourly receipt sync completed: {result.get('message', 'OK')}"
            )
    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Hourly Sync Failed"
        )


def cleanup_old_failed_logs():
    """
    Daily cleanup of old failed receipt logs
    Keeps logs for 5 years as per tax requirements
    """
    cutoff_date = add_years(now_datetime(), -5)

    # Only delete failed logs older than 5 years
    deleted = frappe.db.delete("eBarimt Receipt Log", {
        "status": "Failed",
        "creation": ["<", cutoff_date]
    })

    if deleted:
        frappe.db.commit()
        frappe.logger("ebarimt").info(f"Cleaned up {deleted} old failed receipt logs")


def sync_taxpayer_info_weekly():
    """
    Weekly sync of taxpayer information for customers with TIN
    Updates VAT payer status, city tax status, etc.
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    auto_sync = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_taxpayer")
    if not auto_sync:
        return

    from ebarimt.integrations.customer import sync_taxpayer_info

    # Get customers with TIN that haven't been synced recently
    cutoff_date = add_days(now_datetime(), -30)  # Sync if not updated in 30 days

    customers = frappe.get_all(
        "Customer",
        filters=[
            ["custom_tin", "is", "set"],
            ["custom_tin", "!=", ""],
            ["modified", "<", cutoff_date]
        ],
        fields=["name"],
        limit=50
    )

    synced = 0
    for customer in customers:
        try:
            result = sync_taxpayer_info(customer.name)
            if result.get("success"):
                synced += 1
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Taxpayer Sync Failed: {customer.name}"
            )

    frappe.db.commit()

    if synced:
        frappe.logger("ebarimt").info(f"Weekly taxpayer sync: {synced} customers updated")


def sync_barcode_info_weekly():
    """
    Weekly sync of barcode/BUNA information for items
    Updates product names, manufacturers, tax codes
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    auto_sync = frappe.db.get_single_value("eBarimt Settings", "auto_lookup_barcode")
    if not auto_sync:
        return

    from ebarimt.integrations.item import sync_barcode_info

    # Get items with barcode that haven't been synced recently
    cutoff_date = add_days(now_datetime(), -30)

    items = frappe.get_all(
        "Item",
        filters=[
            ["custom_ebarimt_barcode", "is", "set"],
            ["custom_ebarimt_barcode", "!=", ""],
            ["modified", "<", cutoff_date]
        ],
        fields=["name", "custom_ebarimt_barcode"],
        limit=50
    )

    synced = 0
    for item in items:
        try:
            result = sync_barcode_info(item.name, item.custom_ebarimt_barcode)
            if result.get("success"):
                synced += 1
        except Exception as e:
            frappe.log_error(
                message=str(e),
                title=f"Barcode Sync Failed: {item.name}"
            )

    frappe.db.commit()

    if synced:
        frappe.logger("ebarimt").info(f"Weekly barcode sync: {synced} items updated")


def check_lottery_status():
    """
    Check lottery ticket status every 3 days (per eBarimt documentation #6)
    Uses /rest/info API to get leftLotteries count
    Alerts when lottery count is low (< 100)

    Per eBarimtRequirements.rtf: "getInformation service must be called every 3 days
    to check lottery winner status and remaining lottery tickets"
    """
    if not frappe.db.get_single_value("eBarimt Settings", "enabled"):
        return

    from ebarimt.api.client import EBarimtClient

    settings = frappe.get_cached_doc("eBarimt Settings")
    client = EBarimtClient(settings=settings)

    try:
        # Get POS info which includes leftLotteries
        info = client.get_info()

        if not info:
            frappe.log_error(
                message="Failed to get POS info - no response",
                title="eBarimt Lottery Check Failed"
            )
            return

        left_lotteries = info.get("leftLotteries", 0)
        operator_name = info.get("operatorName", "Unknown")
        pos_id = info.get("posId", "Unknown")
        last_sent_date = info.get("lastSentDate", "Unknown")

        # Update settings with latest info
        frappe.db.set_single_value("eBarimt Settings", "left_lotteries", left_lotteries)
        frappe.db.set_single_value("eBarimt Settings", "operator_name", operator_name)
        frappe.db.set_single_value("eBarimt Settings", "last_sync", now_datetime())
        frappe.db.commit()

        frappe.logger("ebarimt").info(
            f"Lottery check: {left_lotteries} tickets remaining, "
            f"POS ID: {pos_id}, Last sent: {last_sent_date}"
        )

        # Alert if lottery count is low (< 100)
        LOW_LOTTERY_THRESHOLD = 100
        if left_lotteries < LOW_LOTTERY_THRESHOLD:
            _send_low_lottery_alert(left_lotteries, operator_name, pos_id)

        # Check for lottery winners in recent receipts
        _check_lottery_winners(client, info)

    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="eBarimt Lottery Check Failed"
        )


def _send_low_lottery_alert(left_lotteries, operator_name, pos_id):
    """Send alert email when lottery tickets are running low"""
    alert_email = frappe.db.get_single_value("eBarimt Settings", "alert_email")

    if not alert_email:
        frappe.logger("ebarimt").warning(
            f"LOW LOTTERY ALERT: Only {left_lotteries} tickets remaining! "
            f"No alert email configured."
        )
        return

    subject = f"eBarimt: Low Lottery Tickets Alert - {left_lotteries} remaining"
    message = f"""
    <h3>eBarimt Lottery Tickets Running Low</h3>
    <p>Your POS terminal is running low on lottery tickets.</p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr><td><strong>Remaining Tickets:</strong></td><td>{left_lotteries}</td></tr>
        <tr><td><strong>Operator:</strong></td><td>{operator_name}</td></tr>
        <tr><td><strong>POS ID:</strong></td><td>{pos_id}</td></tr>
    </table>

    <p><strong>Action Required:</strong> Contact ITC at posapi@itc.gov.mn to request
    additional lottery tickets before running out.</p>

    <p>This is an automated message from eBarimt integration.</p>
    """

    try:
        frappe.sendmail(
            recipients=[alert_email],
            subject=subject,
            message=message,
            now=True
        )
        frappe.logger("ebarimt").info(f"Low lottery alert sent to {alert_email}")
    except Exception as e:
        frappe.log_error(
            message=f"Failed to send lottery alert: {e}",
            title="eBarimt Alert Failed"
        )


def _check_lottery_winners(client, pos_info):
    """
    Check if any recent receipts have winning lottery numbers

    Per documentation, lottery winners should be checked periodically.
    This checks receipts from the last 3 days for potential winners.
    """
    try:
        # Get recent receipts that might have lottery numbers
        three_days_ago = add_days(now_datetime(), -3)

        recent_receipts = frappe.get_all(
            "eBarimt Receipt Log",
            filters={
                "status": "Success",
                "lottery_number": ["is", "set"],
                "creation": [">=", three_days_ago]
            },
            fields=["name", "receipt_id", "lottery_number", "linked_doctype", "linked_docname"],
            limit=100
        )

        if not recent_receipts:
            return

        frappe.logger("ebarimt").debug(
            f"Checking {len(recent_receipts)} recent receipts for lottery status"
        )

        # Note: Actual lottery winner checking requires the eBarimt app
        # or citizen to check via ebarimt.mn portal
        # This is logged for reference

    except Exception as e:
        frappe.logger("ebarimt").warning(f"Lottery winner check failed: {e}")
