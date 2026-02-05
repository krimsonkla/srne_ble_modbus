"""BLE transport implementation for SRNE inverter.

This module implements the ITransport interface for Bluetooth Low Energy
communication with the SRNE inverter device.

Extracted from coordinator.py to provide clean separation of concerns.
"""

import asyncio
import logging
import time
from typing import Optional, Callable

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import (
    establish_connection,
    close_stale_connections_by_address,
    asyncio_timeout,
)
from homeassistant.components import bluetooth

from ...domain.interfaces import ITransport
from ...domain.exceptions import DeviceRejectedCommandError
from ...const import (
    BLE_NOTIFY_UUID,
    BLE_WRITE_UUID,
    BLE_NOTIFY_SUBSCRIBE_TIMEOUT,
    BLE_NOTIFY_RETRY_DELAY,
    BLE_DISCONNECT_TIMEOUT,
    BLE_CONNECTION_TIMEOUT,
    BLE_WRITE_PROCESSING_DELAY,
    MODBUS_RESPONSE_TIMEOUT,
    MAX_CONSECUTIVE_TIMEOUTS,
)
from ..decorators import handle_transport_errors

_LOGGER = logging.getLogger(__name__)

# Use BLE_CONNECTION_TIMEOUT for overall connection safety
BLEAK_SAFETY_TIMEOUT = BLE_CONNECTION_TIMEOUT


class BLETransport(ITransport):
    """BLE transport for SRNE inverter communication.

    This implementation handles:
    - BLE connection via bleak
    - Notification-based communication
    - Send/receive with timeout
    - Notification queue management

    Communication Pattern:
        1. Write command to BLE_WRITE_UUID with response=True (wait for ACK)
        2. Read BLE_WRITE_UUID to get result code
        3. Check result code for dash error pattern (0x2D2D2D2D...)
        4. If clean, wait for notification on BLE_NOTIFY_UUID

    Characteristic Properties:
        - BLE_WRITE_UUID (0x53300001): WRITE + READ (stores result code)
        - BLE_NOTIFY_UUID (0x53300005): NOTIFY (sends Modbus responses)

    Attributes:
        _address: Device BLE MAC address
        _adapter: BleakAdapter wrapping BleakClient
        _notification_queue: Queue for received notifications
        _connected: Connection state flag

    Example:
        >>> transport = BLETransport("AA:BB:CC:DD:EE:FF", hass)
        >>> await transport.connect("AA:BB:CC:DD:EE:FF")
        >>> response = await transport.send(command_bytes, timeout=MODBUS_RESPONSE_TIMEOUT)
        >>> await transport.disconnect()
    """

    def __init__(self, hass):
        """Initialize BLE transport.

        Args:
            hass: Home Assistant instance (for bluetooth component access)
        """
        self._hass = hass
        self._address: Optional[str] = None
        self._client: Optional[BleakClient] = None
        self._notification_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)
        self._connected = False

        # Circuit breaker state
        self._consecutive_timeouts = 0

    async def connect(
        self, address: str, disconnected_callback: Optional[Callable] = None
    ) -> bool:
        """Connect to BLE device using establish_connection.

        This uses bleak_retry_connector which provides automatic retry logic
        matching the original coordinator behavior.

        Args:
            address: Device BLE MAC address
            disconnected_callback: Optional callback for disconnect events

        Returns:
            True if connection successful

        Raises:
            RuntimeError: If device not found
            BleakError: If connection fails

        Example:
            >>> transport = BLETransport(hass)
            >>> success = await transport.connect("AA:BB:CC:DD:EE:FF")
            >>> assert success is True
        """
        self._address = address

        # CRITICAL: Close any stale connections first (Home Assistant best practice)
        # This prevents zombie connections where BleakClient reports connected
        # but the device is actually unresponsive
        _LOGGER.debug("Closing stale connections for %s", address)
        await close_stale_connections_by_address(address)

        # Callback to get latest BLE device info
        def _get_ble_device():
            return bluetooth.async_ble_device_from_address(
                self._hass, address, connectable=True
            )

        # Wait for BLE scanner to discover device (critical on HA restart)
        # The scanner may not have discovered the device yet on fresh startup
        ble_device = _get_ble_device()

        if not ble_device:
            _LOGGER.info(
                "BLE device %s not yet discovered, waiting for scanner (typical on HA restart)...",
                address,
            )
            discovery_timeout = 7.0  # seconds
            discovery_start = time.time()

            while (
                not ble_device and (time.time() - discovery_start) < discovery_timeout
            ):
                await asyncio.sleep(0.5)  # Check every 500ms
                ble_device = _get_ble_device()

            if not ble_device:
                _LOGGER.error(
                    "BLE device not found after %.1fs discovery wait: %s",
                    discovery_timeout,
                    address,
                )
                return False

            _LOGGER.info(
                "BLE device discovered after %.1fs", time.time() - discovery_start
            )

        _LOGGER.debug("Connecting to BLE device %s", address)

        try:
            # Wrap connection with safety timeout (Home Assistant best practice)
            async with asyncio_timeout(BLEAK_SAFETY_TIMEOUT):
                # Use establish_connection for automatic retry logic
                self._client = await establish_connection(
                    BleakClient,
                    ble_device,
                    address,
                    disconnected_callback=disconnected_callback,
                    ble_device_callback=_get_ble_device,
                    max_attempts=2,
                )

            if not self._client.is_connected:
                _LOGGER.error("Failed to connect to BLE device")
                return False

            # Subscribe to NOTIFY UUID for valid responses (critical - must succeed)
            max_notify_attempts = 2
            for attempt in range(max_notify_attempts):
                try:
                    await asyncio.wait_for(
                        self._client.start_notify(
                            BLE_NOTIFY_UUID, self._notification_handler
                        ),
                        timeout=BLE_NOTIFY_SUBSCRIBE_TIMEOUT,
                    )
                    break
                except (asyncio.TimeoutError, BleakError) as err:
                    if attempt == max_notify_attempts - 1:
                        _LOGGER.error(
                            "Timeout subscribing to NOTIFY_UUID after %d attempts",
                            max_notify_attempts,
                        )
                        await self.disconnect()
                        return False
                    _LOGGER.debug(
                        "NOTIFY_UUID subscription attempt %d failed, retrying: %s",
                        attempt + 1,
                        err,
                    )
                    await asyncio.sleep(BLE_NOTIFY_RETRY_DELAY)

            self._connected = True
            # Reset circuit breaker on successful connection
            self._consecutive_timeouts = 0
            _LOGGER.info("BLE transport connected to %s", address)
            return True

        except (BleakError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to establish connection: %s", err)
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from BLE device.

        This method:
        1. Stops notifications
        2. Disconnects client
        3. Clears notification queue
        4. Resets circuit breaker timeout counter
        5. Updates connection state

        Example:
            >>> await transport.disconnect()
            >>> assert not transport.is_connected
        """
        if not self._client:
            return

        try:
            # Stop notifications
            if self._client.is_connected:
                # Stop NOTIFY UUID
                try:
                    await asyncio.wait_for(
                        self._client.stop_notify(BLE_NOTIFY_UUID),
                        timeout=BLE_DISCONNECT_TIMEOUT,
                    )
                    _LOGGER.debug("Stopped BLE_NOTIFY_UUID notifications")
                except (Exception, asyncio.TimeoutError) as err:
                    _LOGGER.debug(
                        "Stop notify NOTIFY_UUID error (non-critical): %s", err
                    )

                # Disconnect
                await asyncio.wait_for(
                    self._client.disconnect(), timeout=BLE_DISCONNECT_TIMEOUT
                )
                _LOGGER.debug("BLE connection closed")

        except Exception as err:
            _LOGGER.warning("Error during disconnect: %s", err)

        finally:
            self._client = None
            self._connected = False
            self._consecutive_timeouts = 0  # Reset circuit breaker on disconnect
            self._clear_notification_queue()

    @handle_transport_errors("BLE send", reraise=True)
    async def send(
        self, data: bytes, timeout: float = MODBUS_RESPONSE_TIMEOUT
    ) -> bytes:
        """Send command with write-then-read error detection.

        CORRECTED IMPLEMENTATION:
        1. Write command to BLE_WRITE_UUID with response=True (wait for ACK)
        2. Read BLE_WRITE_UUID to get result code
        3. Check result code for dash error pattern (0x2D2D2D2D...)
        4. If success, wait for notification on BLE_NOTIFY_UUID

        Device Behavior:
            Error Case:
                - Write → Device stores dash pattern in 0x53300001
                - Read → Get dash pattern (0x2D2D2D2D...00)
                - Interpretation: Batch contains unsupported register
                - No notification sent on 0x53300005

            Success Case:
                - Write → Device stores clean result code in 0x53300001
                - Read → Get clean/empty result
                - Device processes command
                - Notification arrives on 0x53300005 with Modbus data

        Circuit Breaker:
            After MAX_CONSECUTIVE_TIMEOUTS (3) failures, the connection is
            marked as dead and disconnected. This prevents infinite timeout
            loops when the device becomes unresponsive (zombie connection).

        Args:
            data: Command bytes to send
            timeout: Maximum wait time for response (default: MODBUS_RESPONSE_TIMEOUT)

        Returns:
            Response bytes from device

        Raises:
            RuntimeError: If not connected or circuit breaker open
            DeviceRejectedCommandError: If device rejects command (unsupported register)
            TimeoutError: If no response within timeout
            BleakError: If write/read fails

        Example:
            >>> command = protocol.build_read_command(0x0100, 1)
            >>> response = await transport.send(command, timeout=MODBUS_RESPONSE_TIMEOUT)
            >>> assert len(response) > 0
        """
        # Fail-fast connection check: Detect connection loss immediately
        # This prevents operations from hanging when BLE connection is lost
        if not self.is_connected:
            raise RuntimeError("BLE connection lost - reconnection needed")

        if not self._connected or not self._client:
            raise RuntimeError("Not connected to device")

        # Circuit breaker check: too many consecutive timeouts = zombie connection
        if self._consecutive_timeouts >= MAX_CONSECUTIVE_TIMEOUTS:
            timeout_count = (
                self._consecutive_timeouts
            )  # Capture before disconnect resets it
            _LOGGER.error(
                "Circuit breaker opened after %d consecutive timeouts - forcing disconnect",
                timeout_count,
            )
            # Force disconnect to trigger reconnection on next attempt
            await self.disconnect()
            raise RuntimeError(
                f"Connection circuit breaker opened after {timeout_count} timeouts. "
                "Connection will be re-established on next update."
            )

        # Clear any stale notifications
        self._clear_notification_queue()

        # COMPREHENSIVE DEBUG LOGGING
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION START ===")
            _LOGGER.debug(
                "Sending %d bytes to %s: %s", len(data), self._address, data.hex()
            )

        try:
            # Step 1: Write command WITH response (wait for ACK)
            await self._client.write_gatt_char(BLE_WRITE_UUID, data, response=True)
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("Write acknowledged by device (response=True completed)")

            # Step 1.5: CRITICAL - Wait for device to process command
            # The device needs time to:
            # 1. Process the Modbus command (20-50ms)
            # 2. Update the WRITE_UUID characteristic value (10ms)
            # 3. Prepare the notification (20ms)
            # Without this delay, read_gatt_char may return STALE data from previous operations.
            # Using BLE_WRITE_PROCESSING_DELAY from const.py for tuning
            await asyncio.sleep(BLE_WRITE_PROCESSING_DELAY)
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Waited %.3fs for device processing", BLE_WRITE_PROCESSING_DELAY
                )

            # Step 2: Read characteristic to get result code
            result_code = await self._client.read_gatt_char(BLE_WRITE_UUID)
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Read result code from WRITE_UUID: length=%d, hex=%s",
                    len(result_code),
                    result_code.hex() if result_code else "(empty)",
                )

            # Step 3: Dash pattern is NORMAL ACK (not an error!)
            # According to BLE_PROTOCOL.md, the device sends "----..." as acknowledgment
            # that it received the command. The actual Modbus response comes via notification.
            if _LOGGER.isEnabledFor(logging.DEBUG):
                if len(result_code) >= 4 and result_code[:4] == b"\x2d\x2d\x2d\x2d":
                    _LOGGER.debug(
                        "Received normal dash ACK pattern: %s",
                        (
                            result_code[:20].hex()
                            if len(result_code) >= 20
                            else result_code.hex()
                        ),
                    )
                else:
                    # Non-dash pattern - log for investigation
                    _LOGGER.debug(
                        "Read ACK (non-dash pattern): %s",
                        (
                            result_code[:20].hex()
                            if len(result_code) >= 20
                            else result_code.hex()
                        ),
                    )

                _LOGGER.debug("ACK received, waiting for notification on NOTIFY_UUID")

            # Step 4: Wait for actual Modbus response on NOTIFY_UUID
            response = await asyncio.wait_for(
                self._notification_queue.get(), timeout=timeout
            )

            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Received notification from NOTIFY_UUID: length=%d, hex=%s",
                    len(response),
                    response[:40].hex() if len(response) > 40 else response.hex(),
                )

            # Step 5: Check if notification contains dash error (REAL error case)
            # If the device sends dashes in the notification, the register is truly unsupported
            if len(response) >= 4 and response[:4] == b"\x2d\x2d\x2d\x2d":
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(
                        "Notification contains dash pattern - register unsupported"
                    )
                # Don't increment timeout counter - this is a protocol error, not timeout
                raise DeviceRejectedCommandError(
                    "Register unsupported (dash pattern in notification)"
                )

            # Success! Reset circuit breaker
            self._consecutive_timeouts = 0

            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION SUCCESS ===")

            return response

        except asyncio.TimeoutError:
            # Timeout indicates potential zombie connection or slow device
            self._consecutive_timeouts += 1
            _LOGGER.warning(
                "BLE send timeout #%d/%d (no notification received within %ds)",
                self._consecutive_timeouts,
                MAX_CONSECUTIVE_TIMEOUTS,
                timeout,
            )
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION TIMEOUT ===")
            raise

        except DeviceRejectedCommandError:
            # Device rejected command (expected protocol error) - log without stack trace
            # Note: Already logged at DEBUG level when detected (line 319)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION REJECTED ===")
            raise

        except BleakError as err:
            # BLE connection error (disconnected, timeout, etc.)
            # Convert to RuntimeError for proper exception propagation chain:
            # RuntimeError → UseCase handles → UpdateFailed → ConfigEntryNotReady
            _LOGGER.warning("BLE connection error during send: %s", err)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION CONNECTION ERROR ===")
            # Force disconnect to ensure clean state
            await self.disconnect()
            raise RuntimeError(f"BLE connection lost during send: {err}") from err

        except Exception as err:
            _LOGGER.error("BLE operation failed with exception: %s", err, exc_info=True)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION FAILED ===")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected.

        Returns:
            True if connected

        Example:
            >>> assert transport.is_connected
        """
        return (
            self._connected and self._client is not None and self._client.is_connected
        )

    def _notification_handler(self, sender: int, data: bytes) -> None:
        """Handle incoming BLE notifications from NOTIFY_UUID.

        Note: Only subscribed to BLE_NOTIFY_UUID (0x53300005).
        Error detection happens via read_gatt_char(), not notifications.

        Args:
            sender: Characteristic handle
            data: Notification data

        This callback is called by Bleak when notifications arrive.
        Data is queued for retrieval by send().
        """
        # Get characteristic UUID for logging
        char_uuid = getattr(sender, "uuid", "unknown")

        _LOGGER.debug(
            "Notification received: %d bytes from %s, hex=%s",
            len(data),
            char_uuid,
            data[:40].hex() if len(data) > 40 else data.hex(),
        )

        # Queue notification for processing
        try:
            self._notification_queue.put_nowait(data)
        except asyncio.QueueFull:
            _LOGGER.warning("Notification queue full, dropping old data")
            self._clear_notification_queue()
            self._notification_queue.put_nowait(data)

    def _clear_notification_queue(self) -> None:
        """Clear all pending notifications from queue.

        Called before sending new command to ensure we get
        the correct response (not a stale one).
        """
        while not self._notification_queue.empty():
            try:
                self._notification_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        _LOGGER.debug("Notification queue cleared")
