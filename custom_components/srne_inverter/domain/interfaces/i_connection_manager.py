"""IConnectionManager interface for connection lifecycle management.

Extracted from transport.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod


class IConnectionManager(ABC):
    """Interface for connection lifecycle management.

    The connection manager adds higher-level connection management on top
    of the basic transport interface:
    - Automatic reconnection on failure
    - Connection state tracking and monitoring
    - Retry logic with exponential backoff
    - Connection health checks

    This separates connection policy from transport implementation.

    Example:
        >>> manager = ConnectionManager(transport=BLETransport())
        >>> await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        >>> # Use transport...
        >>> # Connection is automatically maintained
    """

    @abstractmethod
    async def ensure_connected(self, address: str, max_retries: int = 3) -> bool:
        """Ensure connection is established, with retries if needed.

        This method guarantees that after successful return, the transport
        is connected and ready to use. It handles:
        - Initial connection
        - Reconnection if disconnected
        - Retry logic with backoff

        Args:
            address: Device address to connect to
            max_retries: Maximum connection attempts (default: 3)

        Returns:
            True if connected successfully, False if all retries exhausted

        Raises:
            TransportError: If connection fails for unrecoverable reason

        Example:
            >>> success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
            >>> if success:
            ...     response = await transport.send(data)
        """

    @abstractmethod
    async def handle_connection_lost(self) -> None:
        """Handle unexpected connection loss.

        Called when connection is detected as lost. Implementations should:
        - Update connection state
        - Trigger reconnection logic (if enabled)
        - Notify listeners/callbacks

        Example:
            >>> await manager.handle_connection_lost()
            >>> # Manager will attempt reconnection
        """

    @property
    @abstractmethod
    def connection_state(self) -> str:
        """Get current connection state.

        Returns:
            Connection state as string: "disconnected", "connecting",
            "connected", "reconnecting", "failed"

        Example:
            >>> state = manager.connection_state
            >>> assert state in ["disconnected", "connecting", "connected",
            ...                   "reconnecting", "failed"]
        """
