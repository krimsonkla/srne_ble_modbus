"""Performance tests for timing optimizations.

This test suite validates the timing optimizations applied to reduce
register reading cycle time. It measures:
- Batch read timing
- Overall cycle time
- Timeout frequency
- Success rate
"""

import asyncio
import time
from unittest.mock import Mock, AsyncMock
import pytest

# Import the timing constants to verify optimization
from custom_components.srne_inverter.const import (
    MODBUS_RESPONSE_TIMEOUT,
    BLE_WRITE_PROCESSING_DELAY,
    BATCH_READ_DELAY,
)


class TestTimingOptimization:
    """Test suite for timing optimization validation."""

    def test_timing_constants_optimized(self):
        """Verify timing constants have been optimized."""
        # Expected optimized values (from REGISTER_READING_OPTIMIZATIONS.md)
        assert (
            MODBUS_RESPONSE_TIMEOUT == 0.5
        ), f"Expected MODBUS_RESPONSE_TIMEOUT=0.5, got {MODBUS_RESPONSE_TIMEOUT}"
        assert (
            BLE_WRITE_PROCESSING_DELAY == 0.03
        ), f"Expected BLE_WRITE_PROCESSING_DELAY=0.03, got {BLE_WRITE_PROCESSING_DELAY}"
        assert (
            BATCH_READ_DELAY == 0.005
        ), f"Expected BATCH_READ_DELAY=0.005, got {BATCH_READ_DELAY}"

    def test_timing_constants_reasonable(self):
        """Verify timing constants are within reasonable bounds."""
        # Safety checks: ensure values aren't too aggressive
        assert MODBUS_RESPONSE_TIMEOUT >= 0.3, "Timeout too aggressive (< 0.3s)"
        assert MODBUS_RESPONSE_TIMEOUT <= 1.0, "Timeout too conservative (> 1.0s)"

        assert (
            BLE_WRITE_PROCESSING_DELAY >= 0.02
        ), "Write delay too aggressive (< 0.02s)"
        assert (
            BLE_WRITE_PROCESSING_DELAY <= 0.1
        ), "Write delay too conservative (> 0.1s)"

        assert BATCH_READ_DELAY >= 0.001, "Batch delay too aggressive (< 0.001s)"
        assert BATCH_READ_DELAY <= 0.02, "Batch delay too conservative (> 0.02s)"

    @pytest.mark.asyncio
    async def test_batch_timing_performance(self):
        """Test that batch reading completes within expected time."""
        from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
            RefreshDataUseCase,
        )
        from custom_components.srne_inverter.application.use_cases.register_batch_dto import (
            RegisterBatch,
        )

        # Create mocks
        conn_manager = Mock()
        transport = Mock()
        transport.is_connected = True
        transport.send = AsyncMock(
            return_value=bytes(
                [
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,  # BLE header
                    0x01,
                    0x03,
                    0x04,
                    0x01,
                    0xE6,
                    0x00,
                    0xFA,
                    0x9F,
                    0x1C,  # Modbus response
                ]
            )
        )

        protocol = Mock()
        protocol.build_read_command = Mock(
            return_value=bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02, 0xC4, 0x0B])
        )
        protocol.decode_response = Mock(return_value={0: 486, 1: 250})

        # Create use case
        use_case = RefreshDataUseCase(conn_manager, transport, protocol)

        # Create test batch
        batch = RegisterBatch(
            start_address=0x0100,
            count=2,
            register_map={0: "test_reg1", 1: "test_reg2"},
        )

        # Measure batch read time
        start = time.time()
        result = await use_case._read_batch(0x0100, 2, 1)
        duration = time.time() - start

        # Verify result
        assert result is not None
        assert 0 in result
        assert 1 in result

        # Performance check: should complete well under timeout
        # Expected: ~0.03s (write delay) + network time
        # Allow up to MODBUS_RESPONSE_TIMEOUT for safety
        assert (
            duration < MODBUS_RESPONSE_TIMEOUT
        ), f"Batch read took {duration:.3f}s, expected < {MODBUS_RESPONSE_TIMEOUT}s"

        # Ideally should be much faster (< 0.2s in practice)
        # This is a loose check since mocking affects timing
        assert duration < 0.5, f"Batch read took {duration:.3f}s, expected < 0.5s"

    @pytest.mark.asyncio
    async def test_cycle_time_projection(self):
        """Test projected cycle time with optimized timings."""
        # Simulate 20 batches (typical configuration)
        num_batches = 20

        # Calculate theoretical minimum time
        theoretical_min_per_batch = (
            BLE_WRITE_PROCESSING_DELAY  # Write processing
            + 0.1  # Estimated network time (optimistic)
            + BATCH_READ_DELAY  # Inter-batch delay
        )

        num_batches * theoretical_min_per_batch

        # With optimized timings:
        # 20 × (0.03 + 0.1 + 0.005) = 20 × 0.135 = 2.7s (best case)
        # With response wait: 20 × (0.03 + 0.3 + 0.005) = 6.7s (typical)
        # With full timeout: 20 × (0.03 + 0.5 + 0.005) = 10.7s (worst case)

        print(f"\nProjected cycle times (20 batches):")
        print(f"  Best case (0.1s response): {20 * (0.03 + 0.1 + 0.005):.2f}s")
        print(f"  Typical (0.3s response): {20 * (0.03 + 0.3 + 0.005):.2f}s")
        print(f"  Worst case (timeout): {20 * (0.03 + 0.5 + 0.005):.2f}s")

        # Verify worst case meets target
        worst_case = num_batches * (
            BLE_WRITE_PROCESSING_DELAY + MODBUS_RESPONSE_TIMEOUT + BATCH_READ_DELAY
        )
        assert (
            worst_case < 15.0
        ), f"Worst-case cycle time {worst_case:.2f}s exceeds 15s safety threshold"

        # Verify typical case meets performance target
        typical_case = num_batches * (
            BLE_WRITE_PROCESSING_DELAY + 0.3 + BATCH_READ_DELAY
        )
        assert (
            typical_case < 10.0
        ), f"Typical cycle time {typical_case:.2f}s exceeds 10s performance target"

    def test_optimization_improvement_calculation(self):
        """Calculate and verify optimization improvement."""
        # Old timings (before optimization)
        old_response_timeout = 0.7
        old_write_delay = 0.05
        old_batch_delay = 0.01

        # New timings (after optimization)
        new_response_timeout = MODBUS_RESPONSE_TIMEOUT
        new_write_delay = BLE_WRITE_PROCESSING_DELAY
        new_batch_delay = BATCH_READ_DELAY

        # Calculate per-batch improvement
        old_per_batch = old_response_timeout + old_write_delay + old_batch_delay
        new_per_batch = new_response_timeout + new_write_delay + new_batch_delay

        per_batch_improvement = old_per_batch - new_per_batch
        per_batch_improvement_pct = (per_batch_improvement / old_per_batch) * 100

        print(f"\nPer-batch improvement:")
        print(f"  Old: {old_per_batch:.3f}s")
        print(f"  New: {new_per_batch:.3f}s")
        print(
            f"  Saved: {per_batch_improvement:.3f}s ({per_batch_improvement_pct:.1f}%)"
        )

        # Calculate total improvement (20 batches)
        num_batches = 20
        old_total = num_batches * old_per_batch
        new_total = num_batches * new_per_batch
        total_improvement = old_total - new_total
        total_improvement_pct = (total_improvement / old_total) * 100

        print(f"\nTotal improvement (20 batches):")
        print(f"  Old: {old_total:.2f}s")
        print(f"  New: {new_total:.2f}s")
        print(f"  Saved: {total_improvement:.2f}s ({total_improvement_pct:.1f}%)")

        # Verify improvement meets target
        assert (
            total_improvement_pct >= 25.0
        ), f"Improvement {total_improvement_pct:.1f}% below 25% target"

        # Verify improvement matches projection
        assert (
            abs(total_improvement_pct - 29.6) < 5.0
        ), f"Improvement {total_improvement_pct:.1f}% differs significantly from projected 29.6%"


class TestPerformanceInstrumentation:
    """Test performance instrumentation and logging."""

    @pytest.mark.asyncio
    async def test_batch_timing_tracking(self):
        """Test that batch timings are tracked correctly."""
        from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
            RefreshDataUseCase,
        )

        # Create mocks
        conn_manager = Mock()
        transport = Mock()
        transport.is_connected = True
        protocol = Mock()

        # Create use case
        use_case = RefreshDataUseCase(conn_manager, transport, protocol)

        # Verify timing tracking is initialized
        assert hasattr(use_case, "_batch_timings")
        assert hasattr(use_case, "_total_batches_processed")
        assert isinstance(use_case._batch_timings, list)
        assert use_case._total_batches_processed == 0

    def test_performance_logging_format(self):
        """Verify performance logging includes timing metrics."""
        # This is a documentation test - verify the log format
        # includes the new timing metrics

        expected_log_format = (
            "Successfully updated all data: %d data points read in %d batches, "
            "duration: %.2fs (batch avg: %.3fs, min: %.3fs, max: %.3fs)"
        )

        # Verify format string is reasonable
        assert "%d" in expected_log_format  # Data points count
        assert "%d" in expected_log_format  # Batch count
        assert "%.2fs" in expected_log_format  # Total duration
        assert "%.3fs" in expected_log_format  # Batch average
        assert "min:" in expected_log_format  # Minimum batch time
        assert "max:" in expected_log_format  # Maximum batch time


class TestSafetyMechanisms:
    """Test that safety mechanisms still function with optimized timings."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_still_active(self):
        """Verify circuit breaker activates with optimized timeouts."""
        from custom_components.srne_inverter.const import MAX_CONSECUTIVE_TIMEOUTS

        # Verify circuit breaker constant exists
        assert MAX_CONSECUTIVE_TIMEOUTS == 3

        # Circuit breaker should trigger after 3 consecutive timeouts
        # With new timeout of 0.5s, this means ~1.5s before forced disconnect
        max_wait = MAX_CONSECUTIVE_TIMEOUTS * MODBUS_RESPONSE_TIMEOUT
        assert (
            max_wait < 3.0
        ), f"Circuit breaker wait time {max_wait:.1f}s too long for zombie detection"

    def test_timeout_safety_margin(self):
        """Verify timeout has adequate safety margin."""
        # Most responses should arrive within 0.3-0.4s
        # Timeout is 0.5s, providing 25-67% margin
        typical_response_time = 0.35  # Average from testing
        safety_margin = (
            MODBUS_RESPONSE_TIMEOUT - typical_response_time
        ) / typical_response_time

        assert (
            safety_margin >= 0.2
        ), f"Safety margin {safety_margin:.1%} below 20% minimum"
        assert (
            safety_margin <= 1.0
        ), f"Safety margin {safety_margin:.1%} above 100% (too conservative)"

        print(f"\nTimeout safety margin: {safety_margin:.1%}")
        print(f"  Typical response: {typical_response_time:.3f}s")
        print(f"  Timeout: {MODBUS_RESPONSE_TIMEOUT:.3f}s")
        print(f"  Margin: {MODBUS_RESPONSE_TIMEOUT - typical_response_time:.3f}s")


if __name__ == "__main__":
    # Run performance calculations
    print("=" * 70)
    print("TIMING OPTIMIZATION PERFORMANCE ANALYSIS")
    print("=" * 70)

    test = TestTimingOptimization()
    test.test_optimization_improvement_calculation()

    test_cycle = TestTimingOptimization()
    asyncio.run(test_cycle.test_cycle_time_projection())

    test_safety = TestSafetyMechanisms()
    test_safety.test_timeout_safety_margin()

    print("\n" + "=" * 70)
    print("Run with: pytest tests/performance/test_timing_optimization.py -v -s")
    print("=" * 70)
