"""Timing collector for adaptive timeout optimization.

Collects and analyzes timing measurements for BLE Modbus operations.
Part of Phase 2 adaptive timing infrastructure.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Optional

from .timing_measurement import TimingMeasurement
from .timing_stats import TimingStats

_LOGGER = logging.getLogger(__name__)


class TimingCollector:
    """Collects and analyzes timing measurements for BLE operations.

    This class maintains a rolling window of timing measurements and provides
    statistical analysis to support adaptive timeout optimization.

    Features:
    - Rolling window with configurable sample size
    - Separate tracking for different operation types
    - Success/failure tracking
    - Percentile calculations (P95, P99)
    - Low overhead (<1ms per measurement)

    Example:
        >>> collector = TimingCollector(sample_size=100)
        >>> collector.record('modbus_read', 450.2, success=True)
        >>> stats = collector.get_statistics('modbus_read')
        >>> print(f"P95: {stats.p95_ms}ms")
    """

    def __init__(self, sample_size: int = 100):
        """Initialize timing collector.

        Args:
            sample_size: Maximum number of samples to retain (rolling window).
                        Actual memory will be 2x for smooth rollover.
        """
        self._sample_size = sample_size
        # Use deque for efficient O(1) append and popleft operations
        # Max size is 2x sample_size to allow smooth rollover
        self._measurements: dict[str, deque[TimingMeasurement]] = {}
        self._enabled = True

        _LOGGER.debug(
            "Initialized TimingCollector with sample_size=%d (max_size=%d)",
            sample_size,
            sample_size * 2,
        )

    def record(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a timing measurement.

        This method is designed to be very fast (<1ms overhead) to avoid
        impacting the actual operation timing.

        Args:
            operation: Operation type identifier (e.g., 'modbus_read')
            duration_ms: Operation duration in milliseconds
            success: Whether operation completed successfully
            metadata: Optional additional context

        Example:
            >>> start = time.time()
            >>> await transport.send(data)
            >>> collector.record('ble_send', (time.time() - start) * 1000, True)
        """
        if not self._enabled:
            return

        # Create measurement
        measurement = TimingMeasurement(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
        )

        # Initialize deque for this operation if needed
        if operation not in self._measurements:
            # Use maxlen for automatic size management
            self._measurements[operation] = deque(maxlen=self._sample_size * 2)

        # Add measurement (automatic eviction if full)
        self._measurements[operation].append(measurement)

        # Log at debug level if enabled
        if _LOGGER.isEnabledFor(logging.DEBUG):
            status = "SUCCESS" if success else "FAILURE"
            _LOGGER.debug(
                "Timing: %s %s in %.2fms (total samples: %d)",
                operation,
                status,
                duration_ms,
                len(self._measurements[operation]),
            )

    def get_statistics(self, operation: str) -> Optional[TimingStats]:
        """Calculate statistics for an operation type.

        Returns None if insufficient samples available (< 2 samples needed
        for meaningful statistics).

        Args:
            operation: Operation type to analyze

        Returns:
            TimingStats object with calculated statistics, or None

        Example:
            >>> stats = collector.get_statistics('modbus_read')
            >>> if stats and stats.sample_count >= 20:
            ...     recommended_timeout = stats.p99_ms * 1.2  # 20% margin
        """
        if operation not in self._measurements:
            return None

        measurements = list(self._measurements[operation])

        # Need at least 2 samples for statistics
        if len(measurements) < 2:
            return None

        # Extract durations and success flags
        durations = [m.duration_ms for m in measurements]
        successes = [m.success for m in measurements]

        # Sort for percentile calculations
        sorted_durations = sorted(durations)
        count = len(sorted_durations)

        # Calculate statistics
        mean_ms = sum(durations) / count
        median_ms = self._calculate_percentile(sorted_durations, 50)
        p95_ms = self._calculate_percentile(sorted_durations, 95)
        p99_ms = self._calculate_percentile(sorted_durations, 99)
        success_rate = sum(successes) / len(successes)

        return TimingStats(
            operation=operation,
            sample_count=count,
            mean_ms=round(mean_ms, 2),
            median_ms=round(median_ms, 2),
            p95_ms=round(p95_ms, 2),
            p99_ms=round(p99_ms, 2),
            success_rate=round(success_rate, 3),
        )

    def _calculate_percentile(self, sorted_values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted list.

        Uses linear interpolation between values when percentile falls
        between samples (standard numpy behavior).

        Args:
            sorted_values: Pre-sorted list of values
            percentile: Percentile to calculate (0-100)

        Returns:
            Interpolated percentile value
        """
        if not sorted_values:
            return 0.0

        if len(sorted_values) == 1:
            return sorted_values[0]

        # Calculate rank (0-indexed)
        rank = (percentile / 100.0) * (len(sorted_values) - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, len(sorted_values) - 1)

        # Linear interpolation
        fraction = rank - lower_idx
        lower_val = sorted_values[lower_idx]
        upper_val = sorted_values[upper_idx]

        return lower_val + fraction * (upper_val - lower_val)

    def get_all_statistics(self) -> dict[str, TimingStats]:
        """Get statistics for all tracked operations.

        Returns:
            Dictionary mapping operation names to their statistics.
            Operations with insufficient samples are excluded.

        Example:
            >>> all_stats = collector.get_all_statistics()
            >>> for op, stats in all_stats.items():
            ...     print(f"{op}: P95={stats.p95_ms}ms")
        """
        result = {}
        for operation in self._measurements:
            stats = self.get_statistics(operation)
            if stats:
                result[operation] = stats
        return result

    def clear(self, operation: Optional[str] = None) -> None:
        """Clear measurements for specific operation or all operations.

        Args:
            operation: Operation to clear, or None to clear all

        Example:
            >>> collector.clear('modbus_read')  # Clear one operation
            >>> collector.clear()  # Clear all operations
        """
        if operation:
            if operation in self._measurements:
                self._measurements[operation].clear()
                _LOGGER.debug("Cleared measurements for operation: %s", operation)
        else:
            self._measurements.clear()
            _LOGGER.debug("Cleared all measurements")

    def enable(self) -> None:
        """Enable timing collection."""
        self._enabled = True
        _LOGGER.debug("Timing collection enabled")

    def disable(self) -> None:
        """Disable timing collection.

        Measurements are retained but new recordings are ignored.
        Useful for reducing overhead during critical operations.
        """
        self._enabled = False
        _LOGGER.debug("Timing collection disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if timing collection is enabled."""
        return self._enabled

    def get_sample_count(self, operation: str) -> int:
        """Get number of samples for an operation.

        Args:
            operation: Operation name

        Returns:
            Number of samples collected, or 0 if operation not tracked
        """
        if operation not in self._measurements:
            return 0
        return len(self._measurements[operation])
