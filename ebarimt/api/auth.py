# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
"""
ITC OAuth2 Authentication for eBarimt APIs
Handles token acquisition and caching for all ITC services
"""

from urllib.parse import urljoin

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime


class ITCAuth:
    """ITC OAuth2 Authentication Handler"""

    # Token cache key
    CACHE_KEY = "ebarimt_itc_token"
    TOKEN_EXPIRY_BUFFER = 60  # seconds before expiry to refresh

    def __init__(self, settings=None):
        """Initialize with eBarimt Settings"""
        self.settings = settings or frappe.get_cached_doc("eBarimt Settings")
        self._setup_urls()

    def _setup_urls(self):
        """Setup API URLs based on environment"""
        # Primary: api.frappe.mn proxy
        # Fallback: Direct IP or government URLs

        if self.settings.environment == "Staging":
            self.auth_url = "https://api.frappe.mn/auth/itc-staging/"
            self.auth_url_fallback = "https://st.auth.itc.gov.mn/auth/"
            self.realm = "Staging"
        else:
            self.auth_url = "https://api.frappe.mn/auth/itc/"
            self.auth_url_fallback = "https://auth.itc.gov.mn/auth/"
            self.realm = "ITC"

        # IP fallback for api.frappe.mn
        self.ip_fallback = "http://103.153.141.167"

    def get_token_url(self, use_fallback=False, use_ip=False):
        """Get the token endpoint URL"""
        if use_ip:
            base = f"{self.ip_fallback}/auth/itc-staging/" if self.settings.environment == "Staging" else f"{self.ip_fallback}/auth/itc/"
        elif use_fallback:
            base = self.auth_url_fallback
        else:
            base = self.auth_url

        return urljoin(base, f"realms/{self.realm}/protocol/openid-connect/token")

    def get_token(self, force_refresh=False):
        """
        Get a valid access token, using cache when possible

        Args:
            force_refresh: Force token refresh even if cached

        Returns:
            str: Valid access token
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_token()
            if cached:
                return cached

        # Get new token
        return self._acquire_token()

    def _get_cached_token(self):
        """Get token from cache if still valid"""
        cache_data = frappe.cache.get_value(self.CACHE_KEY)
        if not cache_data:
            return None

        # Check expiry
        expiry = get_datetime(cache_data.get("expires_at"))
        if now_datetime() >= add_to_date(expiry, seconds=-self.TOKEN_EXPIRY_BUFFER):
            return None

        return cache_data.get("access_token")

    def _acquire_token(self):
        """Acquire new token from ITC OAuth server"""
        # Credentials
        username = self.settings.get_password("api_username") if self.settings.api_username else ""
        password = self.settings.get_password("api_password") if self.settings.api_password else ""

        if not username or not password:
            frappe.throw(_("eBarimt API credentials not configured. Please set username and password in eBarimt Settings."))

        payload = {
            "grant_type": "password",
            "client_id": "vatps",
            "username": username,
            "password": password
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Try primary URL first, then fallbacks
        urls_to_try = [
            (self.get_token_url(), "api.frappe.mn proxy"),
            (self.get_token_url(use_ip=True), "IP fallback"),
            (self.get_token_url(use_fallback=True), "Direct ITC")
        ]

        last_error = None
        for url, desc in urls_to_try:
            try:
                response = requests.post(
                    url,
                    data=payload,
                    headers=headers,
                    timeout=30,
                    verify=True
                )

                if response.status_code == 200:
                    token_data = response.json()
                    self._cache_token(token_data)

                    frappe.logger("ebarimt").debug(f"Token acquired via {desc}")
                    return token_data.get("access_token")

                elif response.status_code == 401:
                    frappe.throw(_("Invalid eBarimt credentials. Please check username and password."))

                else:
                    last_error = f"{desc}: HTTP {response.status_code}"

            except requests.exceptions.Timeout:
                last_error = f"{desc}: Connection timeout"
                continue
            except requests.exceptions.ConnectionError:
                last_error = f"{desc}: Connection failed"
                continue
            except Exception as e:
                last_error = f"{desc}: {e!s}"
                continue

        frappe.throw(_("Failed to acquire eBarimt token. {0}").format(last_error))

    def _cache_token(self, token_data):
        """Cache the token with expiry"""
        expires_in = token_data.get("expires_in", 300)  # Default 5 min
        expires_at = add_to_date(now_datetime(), seconds=expires_in)

        cache_data = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": str(expires_at),
            "token_type": token_data.get("token_type", "Bearer")
        }

        frappe.cache.set_value(
            self.CACHE_KEY,
            cache_data,
            expires_in_sec=expires_in
        )

    def clear_cache(self):
        """Clear cached token"""
        frappe.cache.delete_value(self.CACHE_KEY)

    def get_auth_header(self):
        """Get Authorization header dict"""
        token = self.get_token()
        return {"Authorization": f"Bearer {token}"}


def get_auth():
    """Get ITCAuth instance with current settings"""
    return ITCAuth()
