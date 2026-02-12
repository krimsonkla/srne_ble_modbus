"""Timing statistics data structure.

Statistical summary of timing measurements.
Part of Phase 2 adaptive timing infrastructure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TimingStats:
    """Statistical summary of timing measurements.

    Attributes:
        operation: Operation type
        sample_count: Number of measurements
        mean_ms: Mean duration in milliseconds
        median_ms: Median duration in milliseconds
        p95_ms: 95th percentile duration
        p99_ms: 99th percentile duration
        success_rate: Ratio of successful operations (0.0-1.0)
        last_updated: Timestamp of last statistics update
    """

    operation: str
    sample_count: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    success_rate: float
    last_updated: float = field(default_factory=time.time)
