"""IRepository generic interface for entity persistence.

Extracted from repository.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Generic repository interface for entity persistence.

    This is a base interface for all repositories. Specific repositories
    can extend this with domain-specific methods.

    Type parameter T is the entity type being persisted.

    Example:
        >>> class DeviceRepository(IRepository[Device]):
        ...     async def find_by_address(self, address: str) -> Optional[Device]:
        ...         pass
    """

    @abstractmethod
    async def add(self, entity: T) -> None:
        """Add new entity to repository.

        Args:
            entity: Entity instance to add

        Raises:
            RepositoryError: If entity already exists or save fails

        Example:
            >>> device = Device(address="AA:BB:CC:DD:EE:FF", name="Inverter")
            >>> await repository.add(device)
        """

    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Retrieve entity by ID.

        Args:
            id: Unique identifier for entity

        Returns:
            Entity if found, None otherwise

        Example:
            >>> device = await repository.get("inverter_001")
            >>> if device is not None:
            ...     print(device.name)
        """

    @abstractmethod
    async def update(self, entity: T) -> None:
        """Update existing entity.

        Args:
            entity: Entity with updated values

        Raises:
            RepositoryError: If entity doesn't exist or update fails

        Example:
            >>> device.name = "New Name"
            >>> await repository.update(device)
        """

    @abstractmethod
    async def remove(self, id: str) -> None:
        """Remove entity from repository.

        This method should be idempotent (safe to call if entity doesn't exist).

        Args:
            id: Unique identifier for entity to remove

        Example:
            >>> await repository.remove("inverter_001")
        """

    @abstractmethod
    async def list_all(self) -> List[T]:
        """Retrieve all entities.

        Returns:
            List of all entities in repository (may be empty)

        Example:
            >>> devices = await repository.list_all()
            >>> for device in devices:
            ...     print(device.name)
        """
