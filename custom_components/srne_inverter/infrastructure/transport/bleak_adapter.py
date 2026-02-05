"""Adapter for BleakClient to enable testing.

This adapter wraps BleakClient to provide a testable interface.
In tests, we can inject a fake adapter instead of using real BLE hardware.
"""

from typing import Optional
from bleak import BleakClient
from bleak.backends.device import BLEDevice


class BleakAdapter:
    """Adapter for BleakClient.

    This wrapper allows us to:
    1. Mock BLE operations in tests
    2. Add logging/monitoring
    3. Handle Bleak API changes in one place

    Attributes:
        client: Underlying BleakClient instance

    Example:
        >>> adapter = BleakAdapter(ble_device)
        >>> await adapter.connect()
        >>> data = await adapter.read_gatt_char(uuid)
        >>> await adapter.disconnect()
    """

    def __init__(self, device: BLEDevice):
        """Initialize adapter with BLE device.

        Args:
            device: BLE device to connect to
        """
        self._device = device
        self._client: Optional[BleakClient] = None

    async def connect(self) -> bool:
        """Connect to BLE device.

        Returns:
            True if connection successful

        Raises:
            BleakError: If connection fails
        """
        if self._client is None:
            self._client = BleakClient(self._device)

        await self._client.connect()
        return self._client.is_connected

    async def disconnect(self) -> None:
        """Disconnect from BLE device."""
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()

    async def write_gatt_char(
        self, char_specifier: str, data: bytes, response: bool = False
    ) -> None:
        """Write data to GATT characteristic.

        Args:
            char_specifier: UUID of characteristic
            data: Data to write
            response: Whether to wait for response

        Raises:
            RuntimeError: If not connected
            BleakError: If write fails
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to device")

        await self._client.write_gatt_char(char_specifier, data, response=response)

    async def read_gatt_char(self, char_specifier: str) -> bytes:
        """Read data from GATT characteristic.

        Args:
            char_specifier: UUID of characteristic

        Returns:
            Data read from characteristic

        Raises:
            RuntimeError: If not connected
            BleakError: If read fails
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to device")

        return await self._client.read_gatt_char(char_specifier)

    @property
    def is_connected(self) -> bool:
        """Check if connected to device.

        Returns:
            True if connected
        """
        return self._client is not None and self._client.is_connected

    async def start_notify(self, char_specifier: str, callback) -> None:
        """Start receiving notifications from a characteristic.

        Args:
            char_specifier: UUID of characteristic
            callback: Callback function for notifications

        Raises:
            RuntimeError: If not connected
            BleakError: If notification setup fails
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to device")

        await self._client.start_notify(char_specifier, callback)

    async def stop_notify(self, char_specifier: str) -> None:
        """Stop receiving notifications from a characteristic.

        Args:
            char_specifier: UUID of characteristic

        Raises:
            RuntimeError: If not connected
            BleakError: If stop notify fails
        """
        if self._client is None or not self._client.is_connected:
            raise RuntimeError("Not connected to device")

        await self._client.stop_notify(char_specifier)

    @property
    def address(self) -> str:
        """Get device address.

        Returns:
            Device MAC address
        """
        return self._device.address
