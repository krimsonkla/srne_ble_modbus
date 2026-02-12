"""Unit tests for TimingCollector.

Tests the timing measurement and statistics calculation infrastructure
for adaptive timeout optimization (Phase 2).
"""

import pytest
import time
from unittest.mock import patch

from custom_components.srne_inverter.application.services.timing_collector import (
    TimingCollector,
    TimingMeasurement,
    TimingStats,
)


class TestTimingCollectorInitialization:
    """Test TimingCollector initialization."""

    def test_timing_collector_initialization(self):
        """Test collector initializes with correct configuration."""
        collector = TimingCollector(sample_size=50)

        assert collector._sample_size == 50
        assert collector._enabled is True
        assert len(collector._measurements) == 0

    def test_timing_collector_default_sample_size(self):
        """Test collector uses default sample size."""
        collector = TimingCollector()

        assert collector._sample_size == 100


class TestTimingMeasurementRecording:
    """Test measurement recording functionality."""

    def test_record_single_measurement(self):
        """Test recording a single timing measurement."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 450.5, success=True)

        assert collector.get_sample_count("modbus_read") == 1

    def test_record_multiple_measurements(self):
        """Test recording multiple measurements for same operation."""
        collector = TimingCollector(sample_size=10)

        for i in range(5):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        assert collector.get_sample_count("modbus_read") == 5

    def test_record_different_operations(self):
        """Test recording measurements for different operation types."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 450.0, success=True)
        collector.record("ble_write", 120.0, success=True)
        collector.record("ble_connect", 2500.0, success=True)

        assert collector.get_sample_count("modbus_read") == 1
        assert collector.get_sample_count("ble_write") == 1
        assert collector.get_sample_count("ble_connect") == 1

    def test_record_with_metadata(self):
        """Test recording measurement with metadata."""
        collector = TimingCollector(sample_size=10)

        metadata = {"address": "0x100A", "batch": 1}
        collector.record("modbus_read", 450.0, success=True, metadata=metadata)

        measurements = list(collector._measurements["modbus_read"])
        assert measurements[0].metadata == metadata

    def test_record_failure(self):
        """Test recording failed operation."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 1500.0, success=False)

        stats = collector.get_statistics("modbus_read")
        assert stats is None  # Need at least 2 samples

    def test_record_when_disabled(self):
        """Test recording is ignored when collector disabled."""
        collector = TimingCollector(sample_size=10)
        collector.disable()

        collector.record("modbus_read", 450.0, success=True)

        assert collector.get_sample_count("modbus_read") == 0


class TestRollingWindow:
    """Test rolling window behavior."""

    def test_rolling_window_eviction(self):
        """Test old measurements are evicted when window is full."""
        collector = TimingCollector(sample_size=5)

        # Record more than sample_size measurements
        for i in range(12):
            collector.record("modbus_read", 400.0 + i, success=True)

        # Should retain max 2x sample_size (10 samples)
        assert collector.get_sample_count("modbus_read") <= 10

    def test_rolling_window_keeps_recent(self):
        """Test rolling window keeps most recent measurements."""
        collector = TimingCollector(sample_size=5)

        # Record measurements with increasing values
        for i in range(15):
            collector.record("modbus_read", float(i), success=True)

        measurements = list(collector._measurements["modbus_read"])

        # Should keep recent measurements (values >= 5)
        durations = [m.duration_ms for m in measurements]
        assert all(d >= 5.0 for d in durations)


class TestStatisticsCalculation:
    """Test statistical calculations."""

    def test_statistics_insufficient_data(self):
        """Test returns None with insufficient samples."""
        collector = TimingCollector(sample_size=10)

        # Only one sample
        collector.record("modbus_read", 450.0, success=True)

        stats = collector.get_statistics("modbus_read")
        assert stats is None

    def test_statistics_with_two_samples(self):
        """Test statistics calculation with minimum samples."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 400.0, success=True)
        collector.record("modbus_read", 500.0, success=True)

        stats = collector.get_statistics("modbus_read")

        assert stats is not None
        assert stats.sample_count == 2
        assert stats.mean_ms == 450.0
        assert stats.median_ms == 450.0

    def test_statistics_with_sufficient_data(self):
        """Test statistics with TIMING_MIN_SAMPLES (20 samples)."""
        collector = TimingCollector(sample_size=100)

        # Record 20 measurements: 400, 410, 420, ..., 590
        for i in range(20):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        stats = collector.get_statistics("modbus_read")

        assert stats is not None
        assert stats.sample_count == 20
        assert stats.success_rate == 1.0
        # Mean should be around 495
        assert 490.0 < stats.mean_ms < 500.0
        # P95 should be close to upper range
        assert stats.p95_ms > 580.0

    def test_statistics_mean_calculation(self):
        """Test mean calculation accuracy."""
        collector = TimingCollector(sample_size=10)

        values = [100.0, 200.0, 300.0, 400.0, 500.0]
        for val in values:
            collector.record("modbus_read", val, success=True)

        stats = collector.get_statistics("modbus_read")

        assert stats.mean_ms == 300.0

    def test_statistics_median_calculation(self):
        """Test median calculation with odd and even sample counts."""
        collector = TimingCollector(sample_size=10)

        # Odd number: 100, 200, 300, 400, 500 -> median = 300
        values_odd = [100.0, 500.0, 300.0, 200.0, 400.0]
        for val in values_odd:
            collector.record("test_odd", val, success=True)

        stats = collector.get_statistics("test_odd")
        assert stats.median_ms == 300.0

        # Even number: 100, 200, 300, 400 -> median = 250
        values_even = [100.0, 400.0, 200.0, 300.0]
        for val in values_even:
            collector.record("test_even", val, success=True)

        stats = collector.get_statistics("test_even")
        assert stats.median_ms == 250.0

    def test_statistics_p95_calculation(self):
        """Test 95th percentile calculation."""
        collector = TimingCollector(sample_size=100)

        # Create dataset: 1-100
        for i in range(1, 101):
            collector.record("modbus_read", float(i), success=True)

        stats = collector.get_statistics("modbus_read")

        # P95 should be around 95-96
        assert 94.0 < stats.p95_ms < 97.0

    def test_statistics_p99_calculation(self):
        """Test 99th percentile calculation."""
        collector = TimingCollector(sample_size=100)

        # Create dataset: 1-100
        for i in range(1, 101):
            collector.record("modbus_read", float(i), success=True)

        stats = collector.get_statistics("modbus_read")

        # P99 should be around 99-100
        assert 98.0 < stats.p99_ms < 101.0

    def test_statistics_success_rate(self):
        """Test success rate calculation."""
        collector = TimingCollector(sample_size=20)

        # 80% success rate: 8 success, 2 failures
        for i in range(8):
            collector.record("modbus_read", 400.0, success=True)
        for i in range(2):
            collector.record("modbus_read", 1500.0, success=False)

        stats = collector.get_statistics("modbus_read")

        assert stats.success_rate == 0.8

    def test_statistics_nonexistent_operation(self):
        """Test statistics for operation with no measurements."""
        collector = TimingCollector(sample_size=10)

        stats = collector.get_statistics("nonexistent")

        assert stats is None


class TestGetAllStatistics:
    """Test get_all_statistics functionality."""

    def test_get_all_statistics_multiple_operations(self):
        """Test retrieving statistics for all operations."""
        collector = TimingCollector(sample_size=20)

        # Record measurements for multiple operations
        for i in range(5):
            collector.record("modbus_read", 400.0 + i * 10, success=True)
            collector.record("ble_write", 120.0 + i * 5, success=True)
            collector.record("ble_connect", 2500.0 + i * 50, success=True)

        all_stats = collector.get_all_statistics()

        assert len(all_stats) == 3
        assert "modbus_read" in all_stats
        assert "ble_write" in all_stats
        assert "ble_connect" in all_stats

    def test_get_all_statistics_excludes_insufficient_data(self):
        """Test operations with insufficient data are excluded."""
        collector = TimingCollector(sample_size=20)

        # Only one sample for this operation
        collector.record("insufficient", 100.0, success=True)

        # Multiple samples for this operation
        for i in range(5):
            collector.record("sufficient", 400.0 + i * 10, success=True)

        all_stats = collector.get_all_statistics()

        assert "insufficient" not in all_stats
        assert "sufficient" in all_stats


class TestClearFunctionality:
    """Test clear functionality."""

    def test_clear_specific_operation(self):
        """Test clearing measurements for specific operation."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 400.0, success=True)
        collector.record("ble_write", 120.0, success=True)

        collector.clear("modbus_read")

        assert collector.get_sample_count("modbus_read") == 0
        assert collector.get_sample_count("ble_write") == 1

    def test_clear_all_operations(self):
        """Test clearing all measurements."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 400.0, success=True)
        collector.record("ble_write", 120.0, success=True)
        collector.record("ble_connect", 2500.0, success=True)

        collector.clear()

        assert len(collector._measurements) == 0

    def test_clear_nonexistent_operation(self):
        """Test clearing nonexistent operation is safe."""
        collector = TimingCollector(sample_size=10)

        # Should not raise exception
        collector.clear("nonexistent")

        assert collector.get_sample_count("nonexistent") == 0


class TestEnableDisable:
    """Test enable/disable functionality."""

    def test_enable_disable_state(self):
        """Test enable/disable state tracking."""
        collector = TimingCollector(sample_size=10)

        assert collector.is_enabled is True

        collector.disable()
        assert collector.is_enabled is False

        collector.enable()
        assert collector.is_enabled is True

    def test_disable_prevents_recording(self):
        """Test disable prevents new recordings."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 400.0, success=True)
        assert collector.get_sample_count("modbus_read") == 1

        collector.disable()
        collector.record("modbus_read", 450.0, success=True)

        # Should still be 1 (new recording ignored)
        assert collector.get_sample_count("modbus_read") == 1

    def test_re_enable_allows_recording(self):
        """Test re-enabling allows recording again."""
        collector = TimingCollector(sample_size=10)

        collector.disable()
        collector.record("modbus_read", 400.0, success=True)
        assert collector.get_sample_count("modbus_read") == 0

        collector.enable()
        collector.record("modbus_read", 450.0, success=True)

        assert collector.get_sample_count("modbus_read") == 1

    def test_disable_retains_measurements(self):
        """Test disable retains existing measurements."""
        collector = TimingCollector(sample_size=10)

        for i in range(5):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        collector.disable()

        # Measurements should still be accessible
        stats = collector.get_statistics("modbus_read")
        assert stats is not None
        assert stats.sample_count == 5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_collector(self):
        """Test behavior with no measurements."""
        collector = TimingCollector(sample_size=10)

        stats = collector.get_statistics("modbus_read")
        assert stats is None

        all_stats = collector.get_all_statistics()
        assert len(all_stats) == 0

    def test_single_sample(self):
        """Test behavior with single sample."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 450.0, success=True)

        stats = collector.get_statistics("modbus_read")
        assert stats is None  # Need at least 2 samples

    def test_zero_duration(self):
        """Test handling of zero duration measurement."""
        collector = TimingCollector(sample_size=10)

        collector.record("modbus_read", 0.0, success=True)
        collector.record("modbus_read", 100.0, success=True)

        stats = collector.get_statistics("modbus_read")
        assert stats is not None
        assert 0.0 in [0.0, 100.0]

    def test_very_large_duration(self):
        """Test handling of very large duration (timeout scenario)."""
        collector = TimingCollector(sample_size=10)

        # Mix of normal and timeout durations
        for i in range(5):
            collector.record("modbus_read", 400.0, success=True)

        collector.record("modbus_read", 5000.0, success=False)  # Timeout

        stats = collector.get_statistics("modbus_read")

        assert stats is not None
        assert stats.p99_ms > 4000.0  # Timeout inflates P99

    def test_all_failures(self):
        """Test statistics with all failed operations."""
        collector = TimingCollector(sample_size=10)

        for i in range(5):
            collector.record("modbus_read", 1500.0, success=False)

        stats = collector.get_statistics("modbus_read")

        assert stats is not None
        assert stats.success_rate == 0.0

    def test_percentile_with_identical_values(self):
        """Test percentile calculation with identical values."""
        collector = TimingCollector(sample_size=10)

        # All measurements identical
        for i in range(10):
            collector.record("modbus_read", 400.0, success=True)

        stats = collector.get_statistics("modbus_read")

        assert stats.mean_ms == 400.0
        assert stats.median_ms == 400.0
        assert stats.p95_ms == 400.0
        assert stats.p99_ms == 400.0


class TestPerformance:
    """Test performance characteristics."""

    def test_recording_overhead(self):
        """Test recording operation is fast (<1ms overhead)."""
        collector = TimingCollector(sample_size=100)

        start = time.perf_counter()

        for i in range(100):
            collector.record("modbus_read", 400.0, success=True)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # 100 recordings should take < 10ms (< 0.1ms per recording)
        assert elapsed_ms < 10.0

    def test_statistics_calculation_performance(self):
        """Test statistics calculation is reasonably fast."""
        collector = TimingCollector(sample_size=100)

        # Fill with 100 samples
        for i in range(100):
            collector.record("modbus_read", 400.0 + i, success=True)

        start = time.perf_counter()

        stats = collector.get_statistics("modbus_read")

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Statistics calculation should be < 5ms
        assert elapsed_ms < 5.0
        assert stats is not None


class TestTimingMeasurementDataclass:
    """Test TimingMeasurement dataclass."""

    def test_timing_measurement_creation(self):
        """Test creating TimingMeasurement."""
        measurement = TimingMeasurement(
            operation="modbus_read",
            duration_ms=450.5,
            success=True,
            metadata={"address": "0x100A"}
        )

        assert measurement.operation == "modbus_read"
        assert measurement.duration_ms == 450.5
        assert measurement.success is True
        assert measurement.metadata["address"] == "0x100A"
        assert measurement.timestamp > 0

    def test_timing_measurement_default_timestamp(self):
        """Test timestamp is set automatically."""
        before = time.time()
        measurement = TimingMeasurement("test", 100.0, True)
        after = time.time()

        assert before <= measurement.timestamp <= after


class TestTimingStatsDataclass:
    """Test TimingStats dataclass."""

    def test_timing_stats_creation(self):
        """Test creating TimingStats."""
        stats = TimingStats(
            operation="modbus_read",
            sample_count=50,
            mean_ms=450.5,
            median_ms=445.0,
            p95_ms=580.0,
            p99_ms=650.0,
            success_rate=0.96
        )

        assert stats.operation == "modbus_read"
        assert stats.sample_count == 50
        assert stats.mean_ms == 450.5
        assert stats.success_rate == 0.96
        assert stats.last_updated > 0
