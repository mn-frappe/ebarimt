"""
Battle Tests for eBarimt Utility Infrastructure
Run with: bench run-tests --app ebarimt --module ebarimt.tests.test_battle_utilities
"""

import time
import frappe
from frappe.tests.utils import FrappeTestCase


class TestResilienceModule(FrappeTestCase):
    """Test resilience utilities."""

    def test_circuit_breaker_import(self):
        """Circuit breaker should be importable."""
        from ebarimt.utils.resilience import CircuitBreaker, CircuitState
        self.assertIsNotNone(CircuitBreaker)
        self.assertIsNotNone(CircuitState)
    
    def test_circuit_breaker_as_decorator(self):
        """Circuit breaker should work as decorator."""
        from ebarimt.utils.resilience import CircuitBreaker
        
        cb = CircuitBreaker(name="test_decorator_eb")
        
        @cb
        def test_func():
            return "success"
        
        result = test_func()
        self.assertEqual(result, "success")
    
    def test_circuit_breaker_state(self):
        """Circuit breaker should track state."""
        from ebarimt.utils.resilience import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test_state_eb", failure_threshold=3)
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_circuit_breaker_opens_on_failures(self):
        """Circuit breaker should open after failures."""
        from ebarimt.utils.resilience import CircuitBreaker, CircuitState, CircuitBreakerOpen
        
        cb = CircuitBreaker(name="test_open_eb", failure_threshold=2, recovery_timeout=1)
        
        @cb
        def failing_func():
            raise ValueError("test error")
        
        for _ in range(2):
            try:
                failing_func()
            except ValueError:
                pass
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        with self.assertRaises(CircuitBreakerOpen):
            failing_func()
    
    def test_circuit_breaker_reset(self):
        """Circuit breaker should support reset."""
        from ebarimt.utils.resilience import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="test_reset_eb", failure_threshold=1)
        
        @cb
        def failing_func():
            raise ValueError("error")
        
        try:
            failing_func()
        except ValueError:
            pass
        
        self.assertEqual(cb.state, CircuitState.OPEN)
        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)
    
    def test_rate_limiter(self):
        """Rate limiter should be importable and work as decorator."""
        from ebarimt.utils.resilience import RateLimiter, RateLimitExceeded
        
        limiter = RateLimiter(name="test_limiter_eb", calls=10, period=60)
        
        @limiter
        def rate_limited_func():
            return "ok"
        
        # Should work within limit
        result = rate_limited_func()
        self.assertEqual(result, "ok")
        
        # RateLimitExceeded should be available
        self.assertIsNotNone(RateLimitExceeded)
    
    def test_retry_decorator(self):
        """Retry decorator should retry on failure."""
        from ebarimt.utils.resilience import retry_with_backoff
        
        attempts = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def flaky_func():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("fail")
            return "success"
        
        result = flaky_func()
        self.assertEqual(result, "success")
        self.assertEqual(attempts, 2)


class TestValidatorsModule(FrappeTestCase):
    """Test validators."""

    def test_tin_validation(self):
        """Should validate TIN format."""
        from ebarimt.utils.validators import validate_tin
        
        self.assertTrue(validate_tin("1234567").is_valid)
        self.assertFalse(validate_tin("123").is_valid)
    
    def test_receipt_type_validation(self):
        """Should validate receipt types."""
        from ebarimt.utils.validators import validate_receipt_type
        
        self.assertTrue(validate_receipt_type("B2C_RECEIPT").is_valid)
        self.assertTrue(validate_receipt_type("B2B_RECEIPT").is_valid)
    
    def test_receipt_data_validation(self):
        """Should validate receipt data."""
        from ebarimt.utils.validators import validate_receipt_data
        
        data = {
            "amount": 1000, "vat": 100, "cityTax": 10,
            "branchNo": "001", "districtCode": "01",
            "stocks": [{"code": "1234567890123", "name": "Test", "qty": 1,
                       "unitPrice": 1000, "totalAmount": 1000,
                       "measureUnit": "шт", "vat": 100, "cityTax": 10}]
        }
        result = validate_receipt_data(data)
        self.assertIsNotNone(result)


class TestIdempotencyModule(FrappeTestCase):
    """Test idempotency utilities."""

    def test_idempotency_manager(self):
        """IdempotencyManager should be available."""
        from ebarimt.utils.idempotency import IdempotencyManager
        self.assertIsNotNone(IdempotencyManager())
    
    def test_idempotency_key_generation(self):
        """Should generate consistent keys."""
        from ebarimt.utils.idempotency import get_receipt_idempotency_key
        
        key1 = get_receipt_idempotency_key("Sales Invoice", "SINV-00001", "2024-01-01")
        key2 = get_receipt_idempotency_key("Sales Invoice", "SINV-00001", "2024-01-01")
        self.assertEqual(key1, key2)
    
    def test_different_inputs_different_keys(self):
        """Different inputs should give different keys."""
        from ebarimt.utils.idempotency import get_receipt_idempotency_key
        
        key1 = get_receipt_idempotency_key("Sales Invoice", "SINV-00001", "2024-01-01")
        key2 = get_receipt_idempotency_key("Sales Invoice", "SINV-00002", "2024-01-01")
        self.assertNotEqual(key1, key2)


class TestMetricsModule(FrappeTestCase):
    """Test metrics collection."""

    def test_metrics_collector(self):
        """MetricsCollector should be available."""
        from ebarimt.utils.metrics import MetricsCollector
        self.assertIsNotNone(MetricsCollector())
    
    def test_record_receipt_creation(self):
        """Should record receipt metrics."""
        from ebarimt.utils.metrics import record_receipt_creation
        record_receipt_creation("B2C_RECEIPT", True, 150.0)
    
    def test_record_api_call(self):
        """Should record API metrics."""
        from ebarimt.utils.metrics import record_api_call
        record_api_call("/api/put", True, 200.0)
    
    def test_get_metrics_summary(self):
        """Should get metrics summary."""
        from ebarimt.utils.metrics import get_metrics_summary
        summary = get_metrics_summary()
        self.assertIsInstance(summary, dict)


class TestHealthModule(FrappeTestCase):
    """Test health check endpoints."""

    def test_health_endpoint(self):
        """Health endpoint should return status."""
        from ebarimt.api.health import health
        self.assertIn("status", health())
    
    def test_detailed_health(self):
        """Detailed health should work."""
        from ebarimt.api.health import detailed_health
        self.assertIsNotNone(detailed_health())
    
    def test_liveness(self):
        """Liveness probe should return alive."""
        from ebarimt.api.health import liveness
        self.assertIn("alive", liveness())
    
    def test_readiness(self):
        """Readiness probe should return ready status."""
        from ebarimt.api.health import readiness
        self.assertIn("ready", readiness())
    
    def test_check_database(self):
        """Should check database."""
        from ebarimt.api.health import check_database
        self.assertIn("status", check_database())
    
    def test_check_cache(self):
        """Should check cache."""
        from ebarimt.api.health import check_cache
        self.assertIn("status", check_cache())


class TestBackgroundModule(FrappeTestCase):
    """Test background job utilities."""

    def test_enqueue_function(self):
        """Should have enqueue function."""
        from ebarimt.utils.background import enqueue_with_retry
        self.assertIsNotNone(enqueue_with_retry)
    
    def test_job_status_function(self):
        """Should have job status function."""
        from ebarimt.utils.background import get_job_status
        self.assertIsNotNone(get_job_status)


class TestLoggingModule(FrappeTestCase):
    """Test logging utilities."""

    def test_logger_available(self):
        """Logger should be available."""
        from ebarimt.utils.logging import get_logger
        self.assertIsNotNone(get_logger())
    
    def test_structured_logger(self):
        """StructuredLogger should be available."""
        from ebarimt.utils.logging import StructuredLogger
        self.assertIsNotNone(StructuredLogger)


class TestOfflineQueueModule(FrappeTestCase):
    """Test offline queue."""

    def test_offline_queue_class(self):
        """OfflineReceiptQueue should be available."""
        from ebarimt.utils.offline_queue import OfflineReceiptQueue
        self.assertIsNotNone(OfflineReceiptQueue)
    
    def test_queue_instance(self):
        """Should have queue instance."""
        from ebarimt.utils.offline_queue import offline_queue
        self.assertIsNotNone(offline_queue)


class TestIntegration(FrappeTestCase):
    """Integration tests."""

    def test_full_validation_flow(self):
        """Test complete validation flow."""
        from ebarimt.utils.validators import validate_tin, validate_receipt_data
        from ebarimt.utils.idempotency import get_receipt_idempotency_key
        
        self.assertTrue(validate_tin("1234567").is_valid)
        
        data = {
            "amount": 1000, "vat": 100, "cityTax": 10,
            "branchNo": "001", "districtCode": "01",
            "stocks": [{"code": "1234567890123", "name": "Test", "qty": 1,
                       "unitPrice": 1000, "totalAmount": 1000,
                       "measureUnit": "шт", "vat": 100, "cityTax": 10}]
        }
        self.assertIsNotNone(validate_receipt_data(data))
        
        key = get_receipt_idempotency_key("Sales Invoice", "SINV-00001", "2024-01-01")
        self.assertIsNotNone(key)
    
    def test_circuit_breaker_integration(self):
        """Test circuit breaker with real function."""
        from ebarimt.utils.resilience import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker(name="integration_cb_eb", failure_threshold=5)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        
        @cb
        def success_func():
            return "ok"
        
        self.assertEqual(success_func(), "ok")
        self.assertEqual(cb.state, CircuitState.CLOSED)
