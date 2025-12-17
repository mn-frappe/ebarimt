# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Notification configuration for eBarimt
"""


def get_notification_config():
    """Return notification configuration for eBarimt"""
    return {
        "for_doctype": {
            "eBarimt Receipt Log": {
                "filters": [
                    {"status": "Failed"}
                ]
            }
        }
    }
