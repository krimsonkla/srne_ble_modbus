"""Learned timeout data structure.

Contains recommended timeout value with supporting metadata.
Part of Phase 3 adaptive timing infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LearnedTimeout:
    """Learned timeout value with supporting metadata.

    This dataclass contains the recommended timeout value along with
    the measurement data that supports the recommendation.

    Attributes:
        operation: Operation type (e.g., 'modbus_read', 'ble_send')
        timeout: Recommended timeout value in seconds
        based_on_samples: Number of measurements used for calculation
        p95_measured: Measured 95th percentile duration in seconds
        default_timeout: Current default timeout for comparison
    """

    operation: str
    timeout: float
    based_on_samples: int
    p95_measured: float
    default_timeout: float

    def __str__(self) -> str:
        """Human-readable representation."""
        change = ((self.timeout - self.default_timeout) / self.default_timeout) * 100
        return (
            f"LearnedTimeout({self.operation}: {self.timeout:.3f}s, "
            f"change={change:+.1f}%, samples={self.based_on_samples}, "
            f"p95={self.p95_measured:.3f}s)"
        )
