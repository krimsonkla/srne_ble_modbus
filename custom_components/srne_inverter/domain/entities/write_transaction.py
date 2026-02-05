"""WriteTransaction entity for managing register writes.

A WriteTransaction represents a single register write operation with
state tracking and rollback capability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..value_objects import RegisterAddress
from .transaction_state import TransactionState


@dataclass
class WriteTransaction:
    """Domain entity representing a register write transaction.

    A WriteTransaction tracks a single register write with:
    - State management (pending → in_progress → committed/failed)
    - Rollback capability (restore previous value on failure)
    - Audit trail (timestamps, error messages)

    Attributes:
        register_address: Address being written to
        new_value: New value to write
        previous_value: Previous value (for rollback)
        state: Current transaction state
        created_at: When transaction was created
        completed_at: When transaction completed (success or failure)
        error_message: Error message if failed
        retry_count: Number of retry attempts
        max_retries: Maximum retry attempts allowed

    Example:
        >>> transaction = WriteTransaction(
        ...     register_address=RegisterAddress(0x0100),
        ...     new_value=500,
        ...     previous_value=486,
        ... )
        >>> assert transaction.can_execute()
        >>> transaction.mark_in_progress()
        >>> # ... perform write ...
        >>> transaction.mark_committed()
        >>> assert transaction.is_completed()
    """

    register_address: RegisterAddress
    new_value: int
    previous_value: Optional[int] = None
    state: TransactionState = TransactionState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate transaction after initialization."""
        if not isinstance(self.register_address, RegisterAddress):
            raise TypeError(
                f"register_address must be RegisterAddress, "
                f"got {type(self.register_address).__name__}"
            )

        if not isinstance(self.new_value, int):
            raise TypeError(
                f"new_value must be int, got {type(self.new_value).__name__}"
            )

        if self.new_value < 0 or self.new_value > 0xFFFF:
            raise ValueError(f"new_value must be 0-65535, got {self.new_value}")

    @property
    def is_pending(self) -> bool:
        """Check if transaction is pending execution.

        Returns:
            True if state is PENDING
        """
        return self.state == TransactionState.PENDING

    @property
    def is_in_progress(self) -> bool:
        """Check if transaction is currently executing.

        Returns:
            True if state is IN_PROGRESS
        """
        return self.state == TransactionState.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """Check if transaction has completed (success or failure).

        Returns:
            True if state is COMMITTED, FAILED, or ROLLED_BACK
        """
        return self.state in (
            TransactionState.COMMITTED,
            TransactionState.FAILED,
            TransactionState.ROLLED_BACK,
        )

    @property
    def is_success(self) -> bool:
        """Check if transaction completed successfully.

        Returns:
            True if state is COMMITTED
        """
        return self.state == TransactionState.COMMITTED

    @property
    def is_failure(self) -> bool:
        """Check if transaction failed.

        Returns:
            True if state is FAILED or ROLLED_BACK
        """
        return self.state in (TransactionState.FAILED, TransactionState.ROLLED_BACK)

    @property
    def can_retry(self) -> bool:
        """Check if transaction can be retried.

        Returns:
            True if retry count < max retries and not yet succeeded
        """
        return (
            self.retry_count < self.max_retries
            and not self.is_success
            and self.state != TransactionState.IN_PROGRESS
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get transaction duration in seconds.

        Returns:
            Duration if completed, None if still in progress
        """
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()

    def can_execute(self) -> bool:
        """Check if transaction can be executed.

        Returns:
            True if transaction is in PENDING state

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ... )
            >>> assert tx.can_execute()
            >>> tx.mark_in_progress()
            >>> assert not tx.can_execute()
        """
        return self.state == TransactionState.PENDING

    def mark_in_progress(self) -> None:
        """Mark transaction as in progress.

        Raises:
            ValueError: If transaction is not in PENDING state

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ... )
            >>> tx.mark_in_progress()
            >>> assert tx.is_in_progress
        """
        if not self.can_execute():
            raise ValueError(f"Cannot start transaction in {self.state.value} state")
        self.state = TransactionState.IN_PROGRESS

    def mark_committed(self) -> None:
        """Mark transaction as successfully committed.

        Raises:
            ValueError: If transaction is not IN_PROGRESS

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ... )
            >>> tx.mark_in_progress()
            >>> tx.mark_committed()
            >>> assert tx.is_success
        """
        if not self.is_in_progress:
            raise ValueError(f"Cannot commit transaction in {self.state.value} state")
        self.state = TransactionState.COMMITTED
        self.completed_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """Mark transaction as failed.

        Args:
            error_message: Description of failure

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ... )
            >>> tx.mark_in_progress()
            >>> tx.mark_failed("Timeout")
            >>> assert tx.is_failure
            >>> assert tx.error_message == "Timeout"
        """
        if not self.is_in_progress:
            raise ValueError(f"Cannot fail transaction in {self.state.value} state")
        self.state = TransactionState.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

    def mark_rolled_back(self) -> None:
        """Mark transaction as rolled back.

        Used after restoring previous value following a failure.

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ...     previous_value=486,
            ... )
            >>> tx.mark_in_progress()
            >>> tx.mark_failed("Write error")
            >>> # Restore previous value...
            >>> tx.mark_rolled_back()
            >>> assert tx.state == TransactionState.ROLLED_BACK
        """
        if self.state != TransactionState.FAILED:
            raise ValueError(f"Cannot rollback transaction in {self.state.value} state")
        self.state = TransactionState.ROLLED_BACK
        self.completed_at = datetime.now()

    def increment_retry(self) -> None:
        """Increment retry counter and reset to PENDING.

        Raises:
            ValueError: If cannot retry (max retries exceeded)

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ... )
            >>> tx.mark_in_progress()
            >>> tx.mark_failed("Timeout")
            >>> assert tx.can_retry
            >>> tx.increment_retry()
            >>> assert tx.is_pending
            >>> assert tx.retry_count == 1
        """
        if not self.can_retry:
            raise ValueError(
                f"Cannot retry: retry_count ({self.retry_count}) >= "
                f"max_retries ({self.max_retries})"
            )
        self.retry_count += 1
        self.state = TransactionState.PENDING
        self.error_message = None

    def to_dict(self) -> dict:
        """Convert transaction to dictionary representation.

        Returns:
            Dictionary with transaction attributes

        Example:
            >>> tx = WriteTransaction(
            ...     register_address=RegisterAddress(0x0100),
            ...     new_value=500,
            ...     previous_value=486,
            ... )
            >>> data = tx.to_dict()
            >>> assert data["register_address"] == 0x0100
            >>> assert data["new_value"] == 500
        """
        return {
            "register_address": int(self.register_address),
            "register_address_hex": self.register_address.to_hex(),
            "new_value": self.new_value,
            "previous_value": self.previous_value,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry,
            "is_success": self.is_success,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"WriteTransaction({self.register_address.to_hex()}: "
            f"{self.previous_value} → {self.new_value}, "
            f"state={self.state.value})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"WriteTransaction(register_address={self.register_address!r}, "
            f"new_value={self.new_value}, state={self.state!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on address and created_at (entity identity).

        Two transactions are the same if they target the same register
        and were created at the same time.

        Args:
            other: Object to compare with

        Returns:
            True if same register and creation time
        """
        if not isinstance(other, WriteTransaction):
            return False
        return (
            self.register_address == other.register_address
            and self.created_at == other.created_at
        )

    def __hash__(self) -> int:
        """Hash based on register address and creation time."""
        return hash((self.register_address, self.created_at))
