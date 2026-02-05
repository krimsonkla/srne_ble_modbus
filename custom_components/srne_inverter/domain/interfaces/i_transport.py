"""ITransport interface for transport layer implementations.

Extracted from transport.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod


class ITransport(ABC):
    """Interface for transport layer implementations.

    The transport layer handles low-level communication with the device.
    For BLE, this includes GATT characteristic read/write operations.

    Connection lifecycle:
        1. connect(address) → establishes connection
        2. send(data) → sends data and receives response (multiple times)
        3. disconnect() → closes connection

    Example:
        >>> transport = BLETransport()
        >>> await transport.connect("AA:BB:CC:DD:EE:FF")
        >>> response = await transport.send(command_bytes)
        >>> await transport.disconnect()
    """

    @abstractmethod
    async def connect(self, address: str) -> bool:
        """Establish connection to device.

        Args:
            address: Device address (BLE MAC for BLE, COM port for Serial, etc.)
                    Example: "AA:BB:CC:DD:EE:FF" for BLE

        Returns:
            True if connection successful, False otherwise

        Raises:
            TransportError: If connection fails due to hardware/network issues
            ValueError: If address format is invalid

        Example:
            >>> success = await transport.connect("AA:BB:CC:DD:EE:FF")
            >>> assert success is True
            >>> assert transport.is_connected is True
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to device.

        This method should be idempotent (safe to call multiple times).
        After disconnect, is_connected should return False.

        Example:
            >>> await transport.disconnect()
            >>> assert transport.is_connected is False
        """

    @abstractmethod
    async def send(self, data: bytes, timeout: float = 5.0) -> bytes:
        """Send data and receive response.

        This is a synchronous request-response operation:
        1. Write data to device
        2. Wait for response (with timeout)
        3. Return response data

        Args:
            data: Raw bytes to send (typically Modbus RTU frame)
            timeout: Maximum time to wait for response in seconds (default: 5.0)

        Returns:
            Response bytes from device

        Raises:
            TransportError: If not connected or send/receive fails
            TimeoutError: If no response within timeout period
            ValueError: If data is empty or invalid

        Example:
            >>> command = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01, 0xD4, 0x04])
            >>> response = await transport.send(command, timeout=3.0)
            >>> assert len(response) > 0
        """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is currently connected.

        Returns:
            True if connected, False otherwise

        Example:
            >>> await transport.connect("AA:BB:CC:DD:EE:FF")
            >>> assert transport.is_connected is True
            >>> await transport.disconnect()
            >>> assert transport.is_connected is False
        """
