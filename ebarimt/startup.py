# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Startup hooks for eBarimt
"""

import frappe


def boot_session(bootinfo):
    """Add eBarimt info to boot session"""
    if frappe.session.user == "Guest":
        return
    
    bootinfo.ebarimt = {}
    
    try:
        # Check if eBarimt is enabled
        settings = frappe.db.get_single_value("eBarimt Settings", ["enabled", "environment"], as_dict=True)
        
        if settings:
            bootinfo.ebarimt["enabled"] = settings.get("enabled")
            bootinfo.ebarimt["environment"] = settings.get("environment")
        else:
            bootinfo.ebarimt["enabled"] = False
            bootinfo.ebarimt["environment"] = None
    except:
        bootinfo.ebarimt["enabled"] = False
        bootinfo.ebarimt["environment"] = None
