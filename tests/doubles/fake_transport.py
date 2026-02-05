"""Fake transport for testing without BLE hardware.

This fake implements ITransport interface for testing.
"""

from typing import List, Tuple, Optional, Callable
from custom_components.srne_inverter.domain.interfaces import ITransport


class FakeTransport(ITransport):
    """Fake BLE transport for testing.

    This fake allows tests to control responses without actual BLE hardware.
    It tracks connection state and can simulate various failure scenarios.

    Attributes:
        _connected: Whether transport is connected
        _responses: Predefined command→response mappings
        _calls: History of send() calls
        _fail_next: Whether next send() should fail

    Example:
        >>> transport = FakeTransport()
        >>> await transport.connect("AA:BB:CC:DD:EE:FF")
        >>> transport.add_response(b'\\x01\\x03', b'\\x01\\x03\\x04...')
        >>> response = await transport.send(b'\\x01\\x03...')
        >>> assert len(response) > 0
    """

    def __init__(self):
        """Initialize fake transport."""
        self._connected = False
        self._responses: List[Tuple[bytes, bytes]] = []
        self._calls: List[bytes] = []
        self._fail_next = False
        self._address: str = ""

    async def connect(
        self, address: str, disconnected_callback: Optional[Callable] = None
    ) -> bool:
        """Simulate connection.

        Args:
            address: Device address
            disconnected_callback: Optional callback for disconnect events (not used in fake)

        Returns:
            True (always succeeds unless configured to fail)
        """
        if self._fail_next:
            self._fail_next = False
            return False

        self._connected = True
        self._address = address
        # Note: disconnected_callback is accepted but not used in fake transport
        return True

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._connected = False

    async def send(self, data: bytes, timeout: float = 5.0) -> bytes:
        """Simulate sending data and receiving response.

        Args:
            data: Command to send
            timeout: Ignored (no actual waiting)

        Returns:
            Predefined response for this command

        Raises:
            RuntimeError: If not connected
            ValueError: If no response configured for command
        """
        if not self._connected:
            raise RuntimeError("Not connected")

        self._calls.append(data)

        if self._fail_next:
            self._fail_next = False
            raise TimeoutError("Simulated timeout")

        # Find matching response
        for cmd_prefix, response in self._responses:
            if data.startswith(cmd_prefix):
                return response

        raise ValueError(f"No response configured for command: {data.hex()}")

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    # Test helper methods

    def add_response(self, command_prefix: bytes, response: bytes) -> None:
        """Add predefined response for command.

        Args:
            command_prefix: First bytes of command to match
            response: Response to return

        Example:
            >>> transport = FakeTransport()
            >>> transport.add_response(b'\\x01\\x03', b'response_data')
        """
        self._responses.append((command_prefix, response))

    def get_calls(self) -> List[bytes]:
        """Get history of send() calls.

        Returns:
            List of all commands sent

        Example:
            >>> transport = FakeTransport()
            >>> await transport.send(b'command1')
            >>> await transport.send(b'command2')
            >>> assert len(transport.get_calls()) == 2
        """
        return self._calls.copy()

    def clear_calls(self) -> None:
        """Clear call history."""
        self._calls.clear()

    def fail_next_send(self) -> None:
        """Make next send() raise TimeoutError.

        Example:
            >>> transport = FakeTransport()
            >>> transport.fail_next_send()
            >>> with pytest.raises(TimeoutError):
            ...     await transport.send(b'command')
        """
        self._fail_next = True

    def fail_next_connect(self) -> None:
        """Make next connect() return False."""
        self._fail_next = True

    def reset(self) -> None:
        """Reset transport to initial state."""
        self._connected = False
        self._responses.clear()
        self._calls.clear()
        self._fail_next = False
        self._address = ""
