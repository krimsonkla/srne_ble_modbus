"""Timing measurement data structure.

Single measurement record for operation timing tracking.
Part of Phase 2 adaptive timing infrastructure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TimingMeasurement:
    """Single timing measurement for an operation.

    Attributes:
        operation: Operation type (e.g., 'modbus_read', 'ble_write')
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
        timestamp: Unix timestamp when measurement was taken
        metadata: Additional context (register address, error type, etc.)
    """

    operation: str
    duration_ms: float
    success: bool
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
