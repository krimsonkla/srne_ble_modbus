"""Timeout learning algorithm for adaptive timeout optimization.

Calculates optimal timeout values from timing measurements.
Part of Phase 3 adaptive timing infrastructure.

Algorithm:
    1. Collect timing measurements via TimingCollector (Phase 2)
    2. Calculate P95 (95th percentile) from samples
    3. Apply safety margin: timeout = P95 * 1.5
    4. Clamp to reasonable bounds: [0.5s, 5.0s]
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from .learned_timeout import LearnedTimeout
from .timing_collector import TimingCollector
from ...const import (
    BLE_COMMAND_TIMEOUT,
    MODBUS_RESPONSE_TIMEOUT,
    TIMING_MAX_TIMEOUT,
    TIMING_MIN_SAMPLES,
    TIMING_MIN_TIMEOUT,
    TIMING_SAFETY_MARGIN,
)

_LOGGER = logging.getLogger(__name__)


class TimeoutLearner:
    """Calculates optimal timeout values from timing measurements.

    This class implements the learning algorithm that transforms raw timing
    measurements into recommended timeout values. The algorithm is conservative,
    prioritizing reliability over speed.

    Algorithm details:
        1. Require minimum samples (20) for statistical reliability
        2. Use P95 (95th percentile) to handle outliers gracefully
        3. Apply 50% safety margin (1.5x multiplier) for reliability
        4. Clamp to [0.5s, 5.0s] to prevent extreme values

    Example:
        >>> collector = TimingCollector()
        >>> learner = TimeoutLearner(collector)
        >>>
        >>> # After operation completes...
        >>> learned = learner.calculate_timeout('modbus_read')
        >>> if learned:
        ...     print(f"Use timeout: {learned.timeout}s")
        ... else:
        ...     print("Insufficient data, using defaults")
    """

    # Default timeout values for comparison
    _DEFAULT_TIMEOUTS = {
        "modbus_read": MODBUS_RESPONSE_TIMEOUT,
        "ble_send": BLE_COMMAND_TIMEOUT,
    }

    def __init__(self, collector: TimingCollector):
        """Initialize timeout learner.

        Args:
            collector: TimingCollector instance with measurement data
        """
        self._collector = collector
        _LOGGER.debug("TimeoutLearner initialized")

    def calculate_timeout(self, operation: str) -> Optional[LearnedTimeout]:
        """Calculate optimal timeout for a specific operation.

        This method implements the core learning algorithm:
            timeout = P95 * TIMING_SAFETY_MARGIN
            timeout = clamp(timeout, TIMING_MIN_TIMEOUT, TIMING_MAX_TIMEOUT)

        Returns None if insufficient data is available (<20 samples).

        Args:
            operation: Operation type to calculate timeout for

        Returns:
            LearnedTimeout with recommendation, or None if insufficient data

        Example:
            >>> learned = learner.calculate_timeout('modbus_read')
            >>> if learned:
            ...     # P95 was 400ms, so: 0.4s * 1.5 = 0.6s timeout
            ...     assert learned.timeout == 0.6
            ...     assert learned.based_on_samples >= 20
        """
        # Get timing statistics from collector
        stats = self._collector.get_statistics(operation)

        # Check if we have sufficient data
        if stats is None or stats.sample_count < TIMING_MIN_SAMPLES:
            if stats:
                _LOGGER.debug(
                    "Insufficient samples for %s: %d < %d required",
                    operation,
                    stats.sample_count,
                    TIMING_MIN_SAMPLES,
                )
            else:
                _LOGGER.debug("No measurements available for %s", operation)
            return None

        # Convert P95 from milliseconds to seconds
        p95_seconds = stats.p95_ms / 1000.0

        # Apply learning algorithm: P95 * safety margin
        calculated_timeout = p95_seconds * TIMING_SAFETY_MARGIN

        # Clamp to reasonable bounds
        clamped_timeout = max(
            TIMING_MIN_TIMEOUT, min(TIMING_MAX_TIMEOUT, calculated_timeout)
        )

        # Get default timeout for comparison
        default_timeout = self._DEFAULT_TIMEOUTS.get(operation, 1.0)

        # Create result
        learned = LearnedTimeout(
            operation=operation,
            timeout=round(clamped_timeout, 3),
            based_on_samples=stats.sample_count,
            p95_measured=round(p95_seconds, 3),
            default_timeout=default_timeout,
        )

        # Log the recommendation
        change_percent = (
            (learned.timeout - default_timeout) / default_timeout
        ) * 100

        _LOGGER.info(
            "Learned timeout for %s: %.3fs (P95=%.3fs * %.1fx = %.3fs, clamped to %.3fs) "
            "based on %d samples. Change from default: %+.1f%%",
            operation,
            learned.timeout,
            p95_seconds,
            TIMING_SAFETY_MARGIN,
            calculated_timeout,
            clamped_timeout,
            stats.sample_count,
            change_percent,
        )

        return learned

    def calculate_all_timeouts(self) -> Dict[str, LearnedTimeout]:
        """Calculate optimal timeouts for all tracked operations.

        This method attempts to calculate learned timeouts for all operations
        that have sufficient measurement data. Operations with insufficient
        data are excluded from the result.

        Returns:
            Dictionary mapping operation names to LearnedTimeout objects.
            Only includes operations with sufficient data (20+ samples).

        Example:
            >>> all_learned = learner.calculate_all_timeouts()
            >>> for operation, learned in all_learned.items():
            ...     print(f"{operation}: {learned.timeout}s")
            modbus_read: 0.627s
            ble_send: 0.523s
        """
        result = {}

        # Get all available statistics
        all_stats = self._collector.get_all_statistics()

        # Calculate timeout for each operation with sufficient data
        for operation in all_stats:
            learned = self.calculate_timeout(operation)
            if learned:
                result[operation] = learned

        _LOGGER.info(
            "Calculated timeouts for %d operations: %s",
            len(result),
            ", ".join(result.keys()),
        )

        return result

    def get_recommendation_summary(self) -> str:
        """Get a human-readable summary of all recommendations.

        Useful for diagnostics and debugging.

        Returns:
            Multi-line string with formatted recommendations

        Example:
            >>> print(learner.get_recommendation_summary())
            Timeout Learning Summary:
            - modbus_read: 0.627s (default: 1.500s, change: -58.2%)
              Based on 45 samples, P95: 0.418s
            - ble_send: 0.523s (default: 1.000s, change: -47.7%)
              Based on 38 samples, P95: 0.349s
        """
        all_learned = self.calculate_all_timeouts()

        if not all_learned:
            return "No learned timeouts available (insufficient data)"

        lines = ["Timeout Learning Summary:"]

        for operation, learned in sorted(all_learned.items()):
            change_percent = (
                (learned.timeout - learned.default_timeout) / learned.default_timeout
            ) * 100

            lines.append(
                f"- {operation}: {learned.timeout:.3f}s "
                f"(default: {learned.default_timeout:.3f}s, change: {change_percent:+.1f}%)"
            )
            lines.append(
                f"  Based on {learned.based_on_samples} samples, "
                f"P95: {learned.p95_measured:.3f}s"
            )

        return "\n".join(lines)
