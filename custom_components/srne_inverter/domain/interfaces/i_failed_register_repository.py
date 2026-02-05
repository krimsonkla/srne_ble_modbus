"""IFailedRegisterRepository interface for tracking failed register addresses.

Extracted from repository.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod
from typing import Set


class IFailedRegisterRepository(ABC):
    """Repository for tracking failed register addresses.

    The coordinator tracks which registers consistently fail to read.
    This allows:
    - Skipping known-bad registers in future reads
    - Reducing error log spam
    - Faster update cycles (don't retry known failures)
    - User visibility into problematic registers

    Storage format is a set of register addresses (integers).

    Example:
        >>> repo = HAFailedRegisterRepository(hass, entry_id)
        >>> await repo.save({0x0100, 0x0200})  # Save failed registers
        >>> failed = await repo.load()
        >>> assert 0x0100 in failed
    """

    @abstractmethod
    async def load(self) -> Set[int]:
        """Load set of failed register addresses from storage.

        Returns:
            Set of register addresses (0x0000 - 0xFFFF) that have failed.
            Returns empty set if no failures or storage not initialized.

        Example:
            >>> failed_registers = await repo.load()
            >>> if 0x0100 in failed_registers:
            ...     print("Register 0x0100 is known to fail")
        """

    @abstractmethod
    async def save(self, registers: Set[int]) -> None:
        """Save set of failed register addresses to storage.

        This replaces the entire failed register set (not incremental update).

        Args:
            registers: Set of register addresses that have failed

        Raises:
            RepositoryError: If storage operation fails

        Example:
            >>> failed = await repo.load()
            >>> failed.add(0x0300)  # Add newly failed register
            >>> await repo.save(failed)
        """

    @abstractmethod
    async def add_failed(self, address: int) -> None:
        """Add single register to failed set.

        This is a convenience method for incrementally adding failures
        without loading the entire set first.

        Args:
            address: Register address that failed (0x0000 - 0xFFFF)

        Example:
            >>> await repo.add_failed(0x0400)
        """

    @abstractmethod
    async def remove_failed(self, address: int) -> None:
        """Remove single register from failed set.

        Used when a previously-failed register succeeds, so we can
        retry it in future update cycles.

        Args:
            address: Register address to remove from failed set

        Example:
            >>> # Register succeeded after firmware update
            >>> await repo.remove_failed(0x0100)
        """

    @abstractmethod
    async def clear(self) -> None:
        """Clear all failed registers.

        Used to reset failure tracking (e.g., after device restart or
        firmware update when failures may no longer apply).

        Example:
            >>> await repo.clear()  # Fresh start
        """

    @abstractmethod
    async def is_failed(self, address: int) -> bool:
        """Check if register is in failed set.

        Args:
            address: Register address to check

        Returns:
            True if register is marked as failed, False otherwise

        Example:
            >>> if await repo.is_failed(0x0100):
            ...     print("Skipping known failed register")
            ... else:
            ...     result = await read_register(0x0100)
        """
