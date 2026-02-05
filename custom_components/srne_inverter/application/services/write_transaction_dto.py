"""Write Transaction DTO.

Data Transfer Object representing a pending write transaction.
Extracted from transaction_manager_service.py for one-class-per-file compliance.
Application Layer Cleanup
"""

from dataclasses import dataclass


@dataclass
class WriteTransaction:
    """Represents a pending write transaction.

    Attributes:
        register: Register address to write
        value: Value to write
        priority: Priority (lower = higher priority)
    """

    register: int
    value: int
    priority: int = 0
