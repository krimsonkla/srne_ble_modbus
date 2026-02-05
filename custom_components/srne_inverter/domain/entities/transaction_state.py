"""Transaction state enum for write operations.

Extracted from write_transaction.py for one-class-per-file compliance.
"""

from enum import Enum


class TransactionState(Enum):
    """Write transaction states."""

    PENDING = "pending"  # Created but not yet executed
    IN_PROGRESS = "in_progress"  # Currently being executed
    COMMITTED = "committed"  # Successfully written
    FAILED = "failed"  # Write failed
    ROLLED_BACK = "rolled_back"  # Rolled back to previous value
