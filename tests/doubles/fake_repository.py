"""Fake repository for testing without storage.

This fake implements IFailedRegisterRepository interface for testing.
"""

from typing import Set
from custom_components.srne_inverter.domain.interfaces import IFailedRegisterRepository


class FakeFailedRegisterRepository(IFailedRegisterRepository):
    """Fake repository for tracking failed registers.

    This fake uses in-memory storage instead of Home Assistant Store.
    Perfect for testing without actual storage dependencies.

    Attributes:
        _data: In-memory set of failed register addresses

    Example:
        >>> repo = FakeFailedRegisterRepository()
        >>> await repo.add_failed(0x0100)
        >>> assert await repo.is_failed(0x0100)
        >>> await repo.clear()
        >>> assert not await repo.is_failed(0x0100)
    """

    def __init__(self):
        """Initialize fake repository."""
        self._data: Set[int] = set()

    async def load(self) -> Set[int]:
        """Load set of failed register addresses.

        Returns:
            Copy of failed register set
        """
        return self._data.copy()

    async def save(self, registers: Set[int]) -> None:
        """Save set of failed register addresses.

        Args:
            registers: Set of failed register addresses
        """
        self._data = registers.copy()

    async def add_failed(self, address: int) -> None:
        """Add register to failed set.

        Args:
            address: Register address that failed
        """
        self._data.add(address)

    async def remove_failed(self, address: int) -> None:
        """Remove register from failed set.

        Args:
            address: Register address to remove
        """
        self._data.discard(address)

    async def clear(self) -> None:
        """Clear all failed registers."""
        self._data.clear()

    async def is_failed(self, address: int) -> bool:
        """Check if register is in failed set.

        Args:
            address: Register address to check

        Returns:
            True if register is marked as failed
        """
        return address in self._data

    # Test helper methods

    def get_failed_count(self) -> int:
        """Get count of failed registers.

        Returns:
            Number of failed registers

        Example:
            >>> repo = FakeFailedRegisterRepository()
            >>> await repo.add_failed(0x0100)
            >>> await repo.add_failed(0x0200)
            >>> assert repo.get_failed_count() == 2
        """
        return len(self._data)

    def get_all_failed(self) -> Set[int]:
        """Get all failed register addresses.

        Returns:
            Set of all failed addresses (copy)

        Example:
            >>> repo = FakeFailedRegisterRepository()
            >>> await repo.add_failed(0x0100)
            >>> failed = repo.get_all_failed()
            >>> assert 0x0100 in failed
        """
        return self._data.copy()

    def reset(self) -> None:
        """Reset repository to empty state.

        Example:
            >>> repo = FakeFailedRegisterRepository()
            >>> await repo.add_failed(0x0100)
            >>> repo.reset()
            >>> assert repo.get_failed_count() == 0
        """
        self._data.clear()
