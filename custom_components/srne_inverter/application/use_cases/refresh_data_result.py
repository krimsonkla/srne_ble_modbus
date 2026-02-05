"""Refresh Data Result DTO.

Data Transfer Object representing the result of a data refresh operation.
Extracted from refresh_data_use_case.py for one-class-per-file compliance.
Application Layer Cleanup
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Set


@dataclass
class RefreshDataResult:
    """Result of data refresh operation.

    Attributes:
        data: Dictionary of register name -> value
        success: Whether refresh was successful
        error: Error message if failed
        duration: Time taken for refresh (seconds)
        failed_reads: Number of failed read attempts
        failed_registers: Set of register addresses that are permanently unsupported
    """

    data: Dict[str, Any]
    success: bool
    error: str = ""
    duration: float = 0.0
    failed_reads: int = 0
    failed_registers: Set[int] = field(default_factory=set)
