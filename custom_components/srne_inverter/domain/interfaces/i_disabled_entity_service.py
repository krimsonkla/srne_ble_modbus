"""Interface for disabled entity detection service."""

from abc import ABC, abstractmethod
from typing import Callable, Set


class IDisabledEntityService(ABC):
    """Interface for detecting and tracking user-disabled entities.

    This service is responsible for:
    - Querying the entity registry for disabled entities
    - Mapping entity IDs to register addresses
    - Providing real-time updates when entities are enabled/disabled
    - Calculating excluded register sets for batch optimization

    Example:
        >>> service = DisabledEntityService(hass, config_entry, register_definitions)
        >>> disabled_addresses = service.get_disabled_addresses()
        >>> service.subscribe_to_updates(callback)
    """

    @abstractmethod
    def get_disabled_addresses(self) -> Set[int]:
        """Get set of register addresses for currently disabled entities.

        Returns:
            Set of register addresses that should be excluded from polling

        Example:
            >>> addresses = service.get_disabled_addresses()
            >>> assert isinstance(addresses, set)
            >>> # Returns {0x0100, 0x0200} if those entities are disabled
        """

    @abstractmethod
    def subscribe_to_updates(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to entity enable/disable events.

        Args:
            callback: Function to call when entities are enabled/disabled

        Returns:
            Unsubscribe function to call for cleanup

        Example:
            >>> def on_change():
            ...     print("Entity state changed")
            >>> unsubscribe = service.subscribe_to_updates(on_change)
            >>> # Later...
            >>> unsubscribe()
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources and unsubscribe from events.

        Example:
            >>> service.shutdown()
        """
