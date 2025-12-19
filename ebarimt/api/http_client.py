# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
"""
eBarimt HTTP Client with Connection Pooling

Provides efficient HTTP client with:
- Connection pooling (reuse TCP connections)
- Automatic retry with exponential backoff
- Request timeout handling
- Thread-safe session management
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import frappe
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class EBarimtHTTPError(Exception):
    """HTTP error for eBarimt API.
    
    Attributes:
        message: Error message
        status_code: HTTP status code (if available)
        response_data: Response body (if available)
    """
    
    def __init__(self, message: str, status_code: int | None = None, response_data: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
    
    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


# Global session cache (per site)
_sessions: dict[str, requests.Session] = {}


def get_session(base_url: str) -> requests.Session:
    """
    Get or create a connection-pooled session.

    Sessions are cached per site and base URL for optimal connection reuse.

    Args:
        base_url: Base URL for the session (e.g., https://api.ebarimt.mn)

    Returns:
        requests.Session: Configured session with connection pooling
    """
    site = getattr(frappe.local, "site", "default")
    cache_key = f"{site}:{base_url}"

    if cache_key not in _sessions:
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,       # Connections per pool
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        _sessions[cache_key] = session

    return _sessions[cache_key]


def make_request(
    method: str,
    url: str,
    timeout: int = 30,
    **kwargs
) -> requests.Response:
    """
    Make HTTP request with connection pooling.

    Uses cached session for efficient connection reuse.

    Args:
        method: HTTP method (GET, POST, DELETE, etc.)
        url: Full URL to request
        timeout: Request timeout in seconds
        **kwargs: Additional requests parameters (json, headers, etc.)

    Returns:
        requests.Response: Response object

    Example:
        response = make_request("POST", "https://api.ebarimt.mn/api/v1/receipts",
                               json=receipt_data, headers=auth_headers)
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    session = get_session(base_url)

    kwargs.setdefault("timeout", timeout)
    kwargs.setdefault("verify", True)

    return session.request(method=method, url=url, **kwargs)


def close_sessions():
    """
    Close all cached sessions.

    Call this during cleanup or worker recycling.
    """
    global _sessions
    for session in _sessions.values():
        try:
            session.close()
        except Exception:
            pass
    _sessions.clear()


class HTTPClient:
    """
    eBarimt HTTP Client with advanced features.

    Provides:
    - Connection pooling
    - Automatic URL fallback
    - Request/response logging
    - Metrics collection

    Example:
        client = HTTPClient(base_url="https://api.ebarimt.mn")
        response = client.post("/api/v1/receipts", json=data)
    """

    def __init__(
        self,
        base_url: str,
        fallback_urls: list[str] | None = None,
        timeout: int = 30,
        debug: bool = False
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Primary API base URL
            fallback_urls: Alternative URLs to try on failure
            timeout: Default request timeout
            debug: Enable debug logging
        """
        self.base_url = base_url.rstrip("/")
        self.fallback_urls = [u.rstrip("/") for u in (fallback_urls or [])]
        self.timeout = timeout
        self.debug = debug
        self._session = get_session(base_url)

    def request(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        try_fallbacks: bool = True,
        **kwargs
    ) -> requests.Response:
        """
        Make request with automatic fallback.

        Args:
            method: HTTP method
            path: URL path (appended to base_url)
            headers: Request headers
            try_fallbacks: Whether to try fallback URLs on failure
            **kwargs: Additional requests parameters

        Returns:
            requests.Response
        """
        urls = [f"{self.base_url}{path}"]
        if try_fallbacks:
            urls.extend(f"{fb}{path}" for fb in self.fallback_urls)

        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", True)

        if headers:
            kwargs["headers"] = headers

        last_error = None

        for url in urls:
            try:
                response = self._session.request(method, url, **kwargs)

                if self.debug:
                    self._log_request(method, url, response.status_code, kwargs.get("json"))

                return response

            except requests.exceptions.Timeout:
                last_error = f"Timeout: {url}"
                continue
            except requests.exceptions.ConnectionError:
                last_error = f"Connection failed: {url}"
                continue
            except Exception as e:
                last_error = f"{url}: {e!s}"
                continue

        # All URLs failed
        raise ConnectionError(f"All endpoints failed. Last error: {last_error}")

    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """POST request."""
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request."""
        return self.request("DELETE", path, **kwargs)

    def _log_request(self, method: str, url: str, status: int, payload: Any = None):
        """Log request for debugging."""
        frappe.logger("ebarimt.http").info(
            f"{method} {url} -> {status}"
        )


# =============================================================================
# SINGLETON CLIENT FACTORY
# =============================================================================

_client_cache: dict[str, HTTPClient] = {}


def get_client(
    base_url: str = "https://api.frappe.mn",
    fallback_urls: list[str] | None = None,
    **kwargs
) -> HTTPClient:
    """
    Get or create a cached HTTP client instance.

    Clients are cached per base_url for connection reuse.

    Args:
        base_url: Primary API base URL
        fallback_urls: Alternative URLs
        **kwargs: Additional HTTPClient parameters

    Returns:
        HTTPClient: Cached client instance
    """
    site = getattr(frappe.local, "site", "default")
    cache_key = f"{site}:{base_url}"

    if cache_key not in _client_cache:
        _client_cache[cache_key] = HTTPClient(
            base_url=base_url,
            fallback_urls=fallback_urls,
            **kwargs
        )

    return _client_cache[cache_key]
