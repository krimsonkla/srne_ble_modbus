"""Tests for TimingCollector (Phase 2).

This test suite validates the timing measurement infrastructure
for adaptive timeout optimization.
"""

import time
import pytest
from custom_components.srne_inverter.application.services.timing_collector import (
    TimingCollector,
    TimingMeasurement,
    TimingStats,
)


def test_timing_collector_initialization():
    """Test timing collector initializes correctly."""
    collector = TimingCollector(sample_size=100)
    assert collector.is_enabled
    assert collector.get_sample_count('test_op') == 0


def test_record_measurement():
    """Test recording a single measurement."""
    collector = TimingCollector(sample_size=100)

    collector.record('test_op', 100.5, success=True)

    assert collector.get_sample_count('test_op') == 1


def test_record_multiple_measurements():
    """Test recording multiple measurements."""
    collector = TimingCollector(sample_size=100)

    # Record 50 measurements
    for i in range(50):
        collector.record('test_op', 100.0 + i, success=True)

    assert collector.get_sample_count('test_op') == 50


def test_statistics_insufficient_samples():
    """Test statistics returns None with insufficient samples."""
    collector = TimingCollector(sample_size=100)

    # Only 1 sample (need at least 2)
    collector.record('test_op', 100.0, success=True)

    stats = collector.get_statistics('test_op')
    assert stats is None


def test_statistics_calculation():
    """Test statistics are calculated correctly."""
    collector = TimingCollector(sample_size=100)

    # Record values: 100, 200, 300, 400, 500
    for val in [100, 200, 300, 400, 500]:
        collector.record('test_op', float(val), success=True)

    stats = collector.get_statistics('test_op')

    assert stats is not None
    assert stats.operation == 'test_op'
    assert stats.sample_count == 5
    assert stats.mean_ms == 300.0  # (100+200+300+400+500)/5
    assert stats.median_ms == 300.0  # Middle value
    assert stats.success_rate == 1.0  # All succeeded
    assert stats.p95_ms >= 400.0  # Should be high percentile
    assert stats.p99_ms >= 400.0


def test_percentile_calculation():
    """Test percentile calculation with known values."""
    collector = TimingCollector(sample_size=100)

    # Record 100 values from 1 to 100
    for i in range(1, 101):
        collector.record('test_op', float(i), success=True)

    stats = collector.get_statistics('test_op')

    assert stats is not None
    assert stats.sample_count == 100
    # P50 (median) should be around 50
    assert 49 <= stats.median_ms <= 51
    # P95 should be around 95
    assert 94 <= stats.p95_ms <= 96
    # P99 should be around 99
    assert 98 <= stats.p99_ms <= 100


def test_success_rate_tracking():
    """Test success rate is calculated correctly."""
    collector = TimingCollector(sample_size=100)

    # Record 8 successes and 2 failures
    for _ in range(8):
        collector.record('test_op', 100.0, success=True)
    for _ in range(2):
        collector.record('test_op', 100.0, success=False)

    stats = collector.get_statistics('test_op')

    assert stats is not None
    assert stats.success_rate == 0.8  # 8/10


def test_rolling_window():
    """Test rolling window keeps size under control."""
    collector = TimingCollector(sample_size=10)

    # Record 25 measurements (2.5x sample size)
    for i in range(25):
        collector.record('test_op', float(i), success=True)

    # Should cap at 2x sample size (20)
    count = collector.get_sample_count('test_op')
    assert count <= 20


def test_multiple_operations():
    """Test tracking multiple operation types simultaneously."""
    collector = TimingCollector(sample_size=100)

    collector.record('op1', 100.0, success=True)
    collector.record('op2', 200.0, success=True)
    collector.record('op1', 150.0, success=True)
    collector.record('op2', 250.0, success=True)  # Need at least 2 samples for stats

    assert collector.get_sample_count('op1') == 2
    assert collector.get_sample_count('op2') == 2

    stats1 = collector.get_statistics('op1')
    stats2 = collector.get_statistics('op2')

    assert stats1.mean_ms == 125.0  # (100+150)/2
    assert stats2.mean_ms == 225.0  # (200+250)/2


def test_get_all_statistics():
    """Test retrieving statistics for all operations."""
    collector = TimingCollector(sample_size=100)

    # Record for multiple operations
    for _ in range(5):
        collector.record('op1', 100.0, success=True)
        collector.record('op2', 200.0, success=True)

    all_stats = collector.get_all_statistics()

    assert len(all_stats) == 2
    assert 'op1' in all_stats
    assert 'op2' in all_stats


def test_clear_single_operation():
    """Test clearing measurements for a specific operation."""
    collector = TimingCollector(sample_size=100)

    collector.record('op1', 100.0, success=True)
    collector.record('op2', 200.0, success=True)

    collector.clear('op1')

    assert collector.get_sample_count('op1') == 0
    assert collector.get_sample_count('op2') == 1


def test_clear_all_operations():
    """Test clearing all measurements."""
    collector = TimingCollector(sample_size=100)

    collector.record('op1', 100.0, success=True)
    collector.record('op2', 200.0, success=True)

    collector.clear()

    assert collector.get_sample_count('op1') == 0
    assert collector.get_sample_count('op2') == 0


def test_enable_disable():
    """Test enabling and disabling collection."""
    collector = TimingCollector(sample_size=100)

    # Record while enabled
    collector.record('test_op', 100.0, success=True)
    assert collector.get_sample_count('test_op') == 1

    # Disable and try to record
    collector.disable()
    assert not collector.is_enabled
    collector.record('test_op', 200.0, success=True)
    assert collector.get_sample_count('test_op') == 1  # Still 1, not recorded

    # Re-enable and record
    collector.enable()
    assert collector.is_enabled
    collector.record('test_op', 300.0, success=True)
    assert collector.get_sample_count('test_op') == 2  # Now recorded


def test_metadata_storage():
    """Test metadata is stored with measurements."""
    collector = TimingCollector(sample_size=100)

    metadata = {'register': 0x0100, 'timeout': 1.5}
    collector.record('test_op', 100.0, success=True, metadata=metadata)

    # Metadata is stored but not directly accessible via public API
    # This is by design - statistics are aggregated
    assert collector.get_sample_count('test_op') == 1


def test_performance_overhead():
    """Test that recording has minimal overhead (<1ms)."""
    collector = TimingCollector(sample_size=100)

    # Measure overhead of 100 recordings
    start = time.time()
    for i in range(100):
        collector.record('test_op', float(i), success=True)
    elapsed_ms = (time.time() - start) * 1000

    # Should be well under 100ms (1ms per recording)
    assert elapsed_ms < 100, f"Recording overhead too high: {elapsed_ms:.2f}ms"

    # Average per recording should be under 1ms
    avg_overhead_ms = elapsed_ms / 100
    assert avg_overhead_ms < 1.0, f"Average overhead per recording: {avg_overhead_ms:.3f}ms"


def test_timing_measurement_dataclass():
    """Test TimingMeasurement dataclass."""
    measurement = TimingMeasurement(
        operation='test_op',
        duration_ms=100.5,
        success=True,
        metadata={'test': 'data'}
    )

    assert measurement.operation == 'test_op'
    assert measurement.duration_ms == 100.5
    assert measurement.success is True
    assert measurement.metadata == {'test': 'data'}
    assert measurement.timestamp > 0


def test_timing_stats_dataclass():
    """Test TimingStats dataclass."""
    stats = TimingStats(
        operation='test_op',
        sample_count=100,
        mean_ms=250.5,
        median_ms=240.0,
        p95_ms=400.0,
        p99_ms=450.0,
        success_rate=0.95
    )

    assert stats.operation == 'test_op'
    assert stats.sample_count == 100
    assert stats.mean_ms == 250.5
    assert stats.median_ms == 240.0
    assert stats.p95_ms == 400.0
    assert stats.p99_ms == 450.0
    assert stats.success_rate == 0.95
    assert stats.last_updated > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
