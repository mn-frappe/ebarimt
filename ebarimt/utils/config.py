# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Configuration Validation for eBarimt

Validates required settings on startup and provides configuration helpers.
"""

from dataclasses import dataclass

import frappe
from frappe import _


@dataclass
class ConfigIssue:
    """Configuration issue"""
    field: str
    message: str
    severity: str = "error"


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    issues: list[ConfigIssue]
    
    def get_errors(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "error"]
    
    def get_warnings(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class ConfigValidator:
    """Validates eBarimt configuration"""
    
    SETTINGS_DOCTYPE = "eBarimt Settings"
    
    def validate(self) -> ConfigValidationResult:
        """Validate all configuration"""
        issues: list[ConfigIssue] = []
        
        if not self._settings_exist():
            issues.append(ConfigIssue(
                field="settings",
                message=_("eBarimt Settings not found. Please configure the app."),
                severity="error"
            ))
            return ConfigValidationResult(is_valid=False, issues=issues)
        
        settings = frappe.get_single(self.SETTINGS_DOCTYPE)
        
        issues.extend(self._validate_api_config(settings))
        issues.extend(self._validate_pos_config(settings))
        issues.extend(self._validate_company_config(settings))
        issues.extend(self._validate_gs1_database())
        issues.extend(self._validate_environment())
        
        is_valid = len([i for i in issues if i.severity == "error"]) == 0
        return ConfigValidationResult(is_valid=is_valid, issues=issues)
    
    def _settings_exist(self) -> bool:
        try:
            frappe.get_single(self.SETTINGS_DOCTYPE)
            return True
        except Exception:
            return False
    
    def _validate_api_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            issues.append(ConfigIssue(
                field="enabled",
                message=_("eBarimt integration is disabled"),
                severity="info"
            ))
            return issues
        
        if not settings.api_url:
            issues.append(ConfigIssue(
                field="api_url",
                message=_("POS API URL is required"),
                severity="error"
            ))
        
        return issues
    
    def _validate_pos_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            return issues
        
        if not settings.pos_id:
            issues.append(ConfigIssue(
                field="pos_id",
                message=_("POS terminal ID is required. Register your POS first."),
                severity="error"
            ))
        
        if hasattr(settings, "district_code") and not settings.district_code:
            issues.append(ConfigIssue(
                field="district_code",
                message=_("District code should be configured for proper receipt generation"),
                severity="warning"
            ))
        
        return issues
    
    def _validate_company_config(self, settings) -> list[ConfigIssue]:
        issues = []
        
        if not settings.enabled:
            return issues
        
        # Check default TIN
        if hasattr(settings, "default_tin") and not settings.default_tin:
            issues.append(ConfigIssue(
                field="default_tin",
                message=_("Default TIN is recommended for single-company setups"),
                severity="info"
            ))
        
        return issues
    
    def _validate_gs1_database(self) -> list[ConfigIssue]:
        issues = []
        
        if frappe.db.table_exists("GS1 Product Code"):
            count = frappe.db.count("GS1 Product Code")
            if count == 0:
                issues.append(ConfigIssue(
                    field="gs1_database",
                    message=_("GS1 product codes database is empty. Import product codes for barcode support."),
                    severity="warning"
                ))
        else:
            issues.append(ConfigIssue(
                field="gs1_database",
                message=_("GS1 Product Code doctype not found"),
                severity="info"
            ))
        
        return issues
    
    def _validate_environment(self) -> list[ConfigIssue]:
        issues = []
        
        try:
            frappe.cache().set_value("ebarimt:config_test", "ok", expires_in_sec=5)
            frappe.cache().delete_value("ebarimt:config_test")
        except Exception as e:
            issues.append(ConfigIssue(
                field="redis",
                message=_("Redis connectivity issue: {0}").format(str(e)),
                severity="warning"
            ))
        
        return issues


def validate_config() -> ConfigValidationResult:
    return ConfigValidator().validate()


def validate_config_on_startup():
    """Hook for startup validation"""
    try:
        result = validate_config()
        
        if not result.is_valid:
            for issue in result.get_errors():
                frappe.logger("ebarimt").error(f"Config error - {issue.field}: {issue.message}")
        
        for issue in result.get_warnings():
            frappe.logger("ebarimt").warning(f"Config warning - {issue.field}: {issue.message}")
    except Exception as e:
        frappe.logger("ebarimt").error(f"Config validation failed: {e}")


def get_config_status() -> dict:
    result = validate_config()
    return {
        "valid": result.is_valid,
        "errors": [{"field": i.field, "message": i.message} for i in result.get_errors()],
        "warnings": [{"field": i.field, "message": i.message} for i in result.get_warnings()]
    }


@frappe.whitelist()
def check_configuration():
    """Check eBarimt configuration status"""
    frappe.only_for(["System Manager", "Administrator"])
    return get_config_status()
