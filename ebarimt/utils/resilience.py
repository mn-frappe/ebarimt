# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Resilience Utilities for eBarimt

Provides circuit breaker, rate limiting, and retry logic for API calls.
Keeps the app resilient against government API failures.
"""

import functools
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Callable, TypeVar

import frappe
from frappe import _

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to a failing service.
    
    Usage:
        breaker = CircuitBreaker(name="ebarimt_api")
        
        @breaker
        def call_api():
            return requests.get(url)
    """
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3
    
    # Internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def __post_init__(self):
        self._load_state()
    
    def _load_state(self):
        """Load circuit state from cache"""
        cache_key = f"circuit_breaker:{self.name}"
        cached = frappe.cache().get_value(cache_key)
        if cached:
            self._state = CircuitState(cached.get("state", "closed"))
            self._failure_count = cached.get("failure_count", 0)
            last_failure = cached.get("last_failure_time")
            if last_failure:
                self._last_failure_time = datetime.fromisoformat(last_failure)
    
    def _save_state(self):
        """Save circuit state to cache"""
        cache_key = f"circuit_breaker:{self.name}"
        frappe.cache().set_value(cache_key, {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
        }, expires_in_sec=3600)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed through"""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    time_since_failure = datetime.now() - self._last_failure_time
                    if time_since_failure > timedelta(seconds=self.recovery_timeout):
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        self._save_state()
                        return True
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return False
    
    def _on_success(self):
        """Handle successful request"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._save_state()
                frappe.logger("ebarimt").info(
                    f"Circuit breaker '{self.name}' recovered, state: CLOSED"
                )
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def _on_failure(self, error: Exception):
        """Handle failed request"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._save_state()
                frappe.logger("ebarimt").warning(
                    f"Circuit breaker '{self.name}' re-opened after failure in half-open state"
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._save_state()
                    frappe.logger("ebarimt").warning(
                        f"Circuit breaker '{self.name}' opened after {self._failure_count} failures"
                    )
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not self._should_allow_request():
                raise CircuitBreakerOpen(
                    f"Circuit breaker '{self.name}' is open. "
                    f"Service unavailable, retry after {self.recovery_timeout}s"
                )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure(e)
                raise
        
        return wrapper
    
    def reset(self):
        """Manually reset the circuit breaker"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            self._save_state()


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


@dataclass
class RateLimiter:
    """
    Token bucket rate limiter.
    
    Prevents hitting government API rate limits.
    """
    name: str
    calls: int = 100
    period: int = 60
    
    _tokens: float = field(default=0, init=False)
    _last_update: float = field(default=0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    
    def __post_init__(self):
        self._tokens = float(self.calls)
        self._last_update = time.time()
    
    def _refill(self):
        """Refill tokens based on time passed"""
        now = time.time()
        time_passed = now - self._last_update
        self._tokens = min(
            self.calls,
            self._tokens + time_passed * (self.calls / self.period)
        )
        self._last_update = now
    
    def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        """Acquire a token"""
        start_time = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
            
            if not blocking:
                return False
            
            if timeout is not None:
                if time.time() - start_time >= timeout:
                    return False
            
            time.sleep(0.1)
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with rate limiting"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not self.acquire(blocking=True, timeout=30):
                raise RateLimitExceeded(
                    f"Rate limit exceeded for '{self.name}'. "
                    f"Max {self.calls} calls per {self.period}s"
                )
            return func(*args, **kwargs)
        
        return wrapper


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None
):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    frappe.logger("ebarimt").warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            if last_exception is not None:
                raise last_exception
            raise RuntimeError(f"Retry failed for {func.__name__} with no exception captured")
        
        return wrapper
    
    return decorator


# Pre-configured instances for eBarimt
# POS API - higher rate limit (local terminal)
ebarimt_pos_circuit_breaker = CircuitBreaker(
    name="ebarimt_pos_api",
    failure_threshold=3,
    recovery_timeout=30
)

ebarimt_pos_rate_limiter = RateLimiter(
    name="ebarimt_pos_api",
    calls=200,
    period=60
)

# Public API - lower rate limit
ebarimt_public_circuit_breaker = CircuitBreaker(
    name="ebarimt_public_api",
    failure_threshold=5,
    recovery_timeout=60
)

ebarimt_public_rate_limiter = RateLimiter(
    name="ebarimt_public_api",
    calls=100,
    period=60
)


def resilient_pos_call(func: Callable[..., T], *args, **kwargs) -> T:
    """Make a resilient POS API call"""
    @ebarimt_pos_circuit_breaker
    @ebarimt_pos_rate_limiter
    @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()


def resilient_public_call(func: Callable[..., T], *args, **kwargs) -> T:
    """Make a resilient Public API call"""
    @ebarimt_public_circuit_breaker
    @ebarimt_public_rate_limiter
    @retry_with_backoff(max_retries=3, exceptions=(ConnectionError, TimeoutError))
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()
