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
    clear_cache,
    asyncio_timeout,
)
from homeassistant.components import bluetooth

from ...domain.interfaces import ITransport
from ...domain.exceptions import (
    DeviceRejectedCommandError,
    TransportConnectionLostError,
)
from ...const import (
    BLE_NOTIFY_UUID,
    BLE_WRITE_UUID,
    BLE_NOTIFY_SUBSCRIBE_TIMEOUT,
    BLE_NOTIFY_RETRY_DELAY,
    BLE_DISCONNECT_TIMEOUT,
    BLE_CONNECTION_TIMEOUT,
    BLE_DISCOVERY_TIMEOUT,
    MODBUS_RESPONSE_TIMEOUT,
    MAX_CONSECUTIVE_TIMEOUTS,
    BLE_WRITE_WITH_RESPONSE,
    BLE_WRITE_PROCESSING_DELAY,
    BLE_FIRST_WRITE_RETRY_DELAY,
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

    def __init__(self, hass, timing_collector=None):
        """Initialize BLE transport.

        Args:
            hass: Home Assistant instance (for bluetooth component access)
            timing_collector: Optional TimingCollector for Phase 2 measurement
        """
        self._hass = hass
        self._address: Optional[str] = None
        self._client: Optional[BleakClient] = None
        self._notification_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)
        # Guards disconnect() against re-entry. client.disconnect() makes Bleak
        # fire disconnected_callback, which schedules handle_connection_lost(),
        # which now calls back into disconnect(). Without this flag that second
        # call can run stop_notify()/disconnect() on the same client while the
        # first is still awaiting them, because _client is not cleared until the
        # finally block.
        self._disconnecting: bool = False
        # True from a successful connect until the first write of that session.
        # Gates the one-shot retry of the first write (see BLE_FIRST_WRITE_RETRY_DELAY).
        self._first_send_after_connect: bool = False
        # Serialises send(). One characteristic, one notification queue, and a
        # device that will happily concatenate two replies into a single
        # notification -- so two overlapping operations cross their responses.
        self._send_lock: asyncio.Lock = asyncio.Lock()
        self._connected = False

        # Circuit breaker state
        self._consecutive_timeouts = 0

        # Adaptive timing (Phase 2: Measurement Infrastructure)
        self._timing_collector = timing_collector

        # Adaptive timing (Phase 5: Runtime Application)
        self._learned_timeouts: dict[str, float] = {}

    def set_learned_timeouts(self, timeouts: dict[str, float]) -> None:
        """Set learned timeout values (Phase 5: Runtime Application).

        Args:
            timeouts: Dict mapping operation -> timeout (seconds)
        """
        self._learned_timeouts = timeouts
        _LOGGER.info(
            "Applied learned timeouts: %s",
            {
                op: f"{val:.2f}s" if isinstance(val, (int, float)) else str(val)
                for op, val in timeouts.items()
            },
        )

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
        _connect_start = time.time()
        _LOGGER.debug("[SRNE_TRACE] connect() ENTRY addr=%s", address)

        # Release any client we are still holding before building a new one.
        #
        # close_stale_connections_by_address() below works at the BlueZ device
        # level; it does not run our stop_notify() path, so on its own it leaves
        # our previous BLE_NOTIFY_UUID subscription attached to
        # _notification_handler. Reconnect paths that skip disconnect() would
        # then stack a second subscription on top of the first. Doing the
        # teardown here makes connect() idempotent for every caller rather than
        # relying on each one to clean up first.
        if self._client is not None:
            _LOGGER.debug(
                "[SRNE_TRACE] connect() found existing client, releasing first"
            )
            await self.disconnect(reason="connect_stale_client")

        # CRITICAL: Close any stale connections first (Home Assistant best practice)
        # This prevents zombie connections where BleakClient reports connected
        # but the device is actually unresponsive
        _LOGGER.debug("Closing stale connections for %s", address)
        await close_stale_connections_by_address(address)

        # NOT clearing the BlueZ GATT cache here, deliberately.
        #
        # A clear_cache(address) call lived here on 2026-09-21 and was removed
        # the same day. It was justified by two facts that are unrelated: the
        # vendor app calls _discoverFreshGattServices, and our stop_notify()
        # fails with "Service Discovery has not been performed yet". The second
        # is not stale-cache evidence -- it happens on the peer-drop path, where
        # the link is already gone and there are no services to find.
        #
        # Measured over 34 clears in one afternoon: zero occurrences of the
        # problem it was meant to help ("First write of session failed"), and
        # one NOTIFY subscribe failure 5s after a clear ("Characteristic
        # 53300005-... was not found!"). That failure class predates the change
        # and also hit renogy and bms_ble, so the clear was not its cause -- but
        # it bought no measured benefit either.
        #
        # Re-add only if something actually demonstrates a stale service cache.

        # Check if BLE adapter is ready (has active scanners)
        # This prevents unclear errors when adapter is still initializing on HA restart
        scanner_count = bluetooth.async_scanner_count(self._hass, connectable=True)
        _LOGGER.info("BLE adapter status: %d active scanner(s) found", scanner_count)

        if scanner_count == 0:
            _LOGGER.error(
                "No active BLE scanners found - Bluetooth adapter may still be initializing. "
                "This is common on first HA startup. HA will automatically retry connection."
            )
            return False

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
            # PHASE 1: Conservative timeout for slow hardware (was 7.0s)
            # Raspberry Pi 3B+ can take longer for BLE discovery on startup
            # Now properly configured in const.py for centralized timing management
            discovery_timeout = BLE_DISCOVERY_TIMEOUT
            discovery_start = time.time()

            while (
                not ble_device and (time.time() - discovery_start) < discovery_timeout
            ):
                await asyncio.sleep(0.5)  # Check every 500ms
                ble_device = _get_ble_device()

            if not ble_device:
                _LOGGER.error(
                    "BLE device %s not found after %.1fs discovery wait. "
                    "Possible causes: (1) Bluetooth adapter still initializing (common on first HA restart), "
                    "(2) Device out of range, (3) Device name/address mismatch. "
                    "HA will automatically retry. Troubleshooting: (1) Wait and let HA retry, "
                    "(2) Move device closer to adapter, (3) Check Bluetooth integration logs for adapter status.",
                    address,
                    discovery_timeout,
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
                # Increased from 2 to 5 attempts for cold start scenarios (HA restart with BLE adapter initialization)
                self._client = await establish_connection(
                    BleakClient,
                    ble_device,
                    address,
                    disconnected_callback=disconnected_callback,
                    ble_device_callback=_get_ble_device,
                    max_attempts=5,
                )

            if not self._client.is_connected:
                _LOGGER.error("Failed to connect to BLE device")
                return False

            # Subscribe to NOTIFY UUID for valid responses (critical - must succeed)
            #
            # This fails intermittently with "Characteristic <NOTIFY_UUID> was
            # not found!", and the cause is an adapter switch rather than
            # anything about this device. habluetooth re-scores the adapters on
            # every reconnect, and with two dongles it alternates: 32 switches
            # between hci0 and hci1 in five hours on 2026-09-21, roughly one per
            # ~266s drop. When the device lands on the other adapter, that
            # adapter's GATT service cache is cold and start_notify can run
            # before services resolve. Measured: all four failures that day fell
            # within ~60s of a switch, two of them within 2s.
            #
            # So clear the BlueZ cache between attempts to force a fresh service
            # discovery. Only on the retry path -- clearing on every connect was
            # tried on 2026-09-21 and removed the same day: 34 clears, zero
            # measured benefit. The failure, not the connect, is what warrants it.
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
                    if attempt < max_notify_attempts - 1:
                        try:
                            await clear_cache(address)
                            _LOGGER.debug(
                                "[SRNE_TRACE] cleared GATT cache after NOTIFY "
                                "subscribe failure on %s",
                                address,
                            )
                        except Exception as cache_err:
                            _LOGGER.debug(
                                "clear_cache after subscribe failure skipped: %s",
                                cache_err,
                            )
                    if attempt == max_notify_attempts - 1:
                        _LOGGER.error(
                            "Timeout subscribing to NOTIFY_UUID after %d attempts: %s",
                            max_notify_attempts,
                            err,
                            exc_info=True,
                        )
                        _LOGGER.debug(
                            "[SRNE_TRACE] connect() start_notify FAIL after %d attempts",
                            max_notify_attempts,
                        )
                        await self.disconnect(reason="start_notify_failed")
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
            # Arm the one-shot retry for this session's first write.
            self._first_send_after_connect = True
            _LOGGER.info("BLE transport connected to %s", address)
            _LOGGER.debug(
                "[SRNE_TRACE] connect() OK addr=%s dt=%.2fs",
                address,
                time.time() - _connect_start,
            )
            return True

        except (BleakError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to establish connection: %s", err, exc_info=True)
            _LOGGER.debug(
                "[SRNE_TRACE] connect() FAIL addr=%s dt=%.2fs err_type=%s err=%s",
                address,
                time.time() - _connect_start,
                type(err).__name__,
                err,
            )
            # Route through disconnect() rather than a bare client.disconnect()
            # so a partially-acquired NOTIFY subscription is released too;
            # otherwise a failed start_notify can leave a stale handle that
            # blocks the next connect with "Notify acquired".
            await self.disconnect(reason="connect_failed")
            return False

    async def disconnect(self, reason: str = "unknown") -> None:
        """Disconnect from BLE device.

        This method:
        1. Stops notifications
        2. Disconnects client
        3. Clears notification queue
        4. Resets circuit breaker timeout counter
        5. Updates connection state

        Args:
            reason: Diagnostic tag for who initiated the disconnect. Used by
                [SRNE_TRACE] logging to attribute drops back to their source
                so we can distinguish integration-initiated disconnects from
                peer/link-layer drops.

        Example:
            >>> await transport.disconnect(reason="shutdown")
            >>> assert not transport.is_connected
        """
        _disc_start = time.time()
        was_client = self._client is not None
        was_connected_flag = self._connected
        client_says_connected = (
            self._client.is_connected if self._client is not None else False
        )
        _LOGGER.debug(
            "[SRNE_TRACE] disconnect() ENTRY reason=%s addr=%s had_client=%s "
            "connected_flag=%s client_is_connected=%s",
            reason,
            self._address,
            was_client,
            was_connected_flag,
            client_says_connected,
        )
        if not self._client:
            _LOGGER.debug(
                "[SRNE_TRACE] disconnect() NOOP reason=%s (no client)", reason
            )
            return

        if self._disconnecting:
            _LOGGER.debug(
                "[SRNE_TRACE] disconnect() NOOP reason=%s (already disconnecting)",
                reason,
            )
            return
        self._disconnecting = True

        try:
            # Always attempt to release the NOTIFY subscription, even when the
            # link is already down. BlueZ keeps the notify acquisition open on
            # the characteristic after an unclean drop (e.g. an ATT 0x0e on a
            # write), and a subsequent connect() then fails start_notify() with
            # [org.bluez.Error.NotPermitted] Notify acquired -- looping until
            # BlueZ times the stale handle out on its own (~minutes). Gating
            # stop_notify behind is_connected skips cleanup exactly when it is
            # needed most, so the call is made unconditionally and its errors
            # are swallowed as non-critical.
            try:
                await asyncio.wait_for(
                    self._client.stop_notify(BLE_NOTIFY_UUID),
                    timeout=BLE_DISCONNECT_TIMEOUT,
                )
                _LOGGER.debug("Stopped BLE_NOTIFY_UUID notifications")
            except (Exception, asyncio.TimeoutError) as err:
                _LOGGER.debug("Stop notify NOTIFY_UUID error (non-critical): %s", err)

            # Disconnect the client regardless of cached connection state so the
            # backend tears down its D-Bus objects and frees the slot.
            try:
                await asyncio.wait_for(
                    self._client.disconnect(), timeout=BLE_DISCONNECT_TIMEOUT
                )
                _LOGGER.debug("BLE connection closed")
            except (Exception, asyncio.TimeoutError) as err:
                _LOGGER.debug("Client disconnect error (non-critical): %s", err)

        except Exception as err:
            _LOGGER.warning("Error during disconnect: %s", err)

        finally:
            self._client = None
            self._connected = False
            self._disconnecting = False
            self._first_send_after_connect = False
            self._consecutive_timeouts = 0  # Reset circuit breaker on disconnect
            self._clear_notification_queue()
            _LOGGER.debug(
                "[SRNE_TRACE] disconnect() DONE reason=%s dt=%.2fs",
                reason,
                time.time() - _disc_start,
            )

    @handle_transport_errors("BLE send", reraise=True)
    async def send(
        self,
        data: bytes,
        timeout: float = MODBUS_RESPONSE_TIMEOUT,
        without_response: bool | None = None,
    ) -> bytes:
        """Serialised entry point. See _send_unlocked for the protocol.

        Every exchange is write -> read result code -> await notification, all
        over one characteristic with one shared notification queue. Nothing
        stopped two of those running at once, and overlapping them crosses the
        replies.

        Observed 2026-09-21 21:19:54. A refresh was mid-flight on batch 16 when
        a user tapped AC Power 76ms later. The write cleared the notification
        queue out from under the read, both wrote to the characteristic, and the
        device answered with both frames concatenated in one notification:

            010308000101900000001985 11 0106df00000173de
            |---- func 0x03 read reply ---| |- func 0x06 write echo -|

        The read consumed it and decoded its four registers; the write was left
        with nothing and timed out. The same race, with the ATT ACK removed, is
        what let a write report success against a read's reply earlier that day.

        A plain lock is enough: send() is never called from inside send(), and
        the longest an operation holds it for is one batch, about 0.85s.
        """
        async with self._send_lock:
            return await self._send_unlocked(data, timeout, without_response)

    async def _send_unlocked(
        self,
        data: bytes,
        timeout: float = MODBUS_RESPONSE_TIMEOUT,
        without_response: bool | None = None,
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
        # Phase 5: Apply learned timeout if available
        if self._learned_timeouts and "ble_send" in self._learned_timeouts:
            learned_timeout = self._learned_timeouts["ble_send"]
            _LOGGER.debug(
                "Using learned timeout: %.2fs (default: %.2fs)",
                learned_timeout,
                timeout,
            )
            timeout = learned_timeout

        # Fail-fast connection check: Detect connection loss immediately
        # This prevents operations from hanging when BLE connection is lost
        if not self.is_connected:
            raise TransportConnectionLostError(
                "BLE connection lost - reconnection needed"
            )

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
            _LOGGER.debug(
                "[SRNE_TRACE] circuit_breaker OPENED timeouts=%d/%d",
                timeout_count,
                MAX_CONSECUTIVE_TIMEOUTS,
            )
            # Force disconnect to trigger reconnection on next attempt
            await self.disconnect(reason="circuit_breaker")
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

        # Phase 2: Start timing measurement
        timing_start = time.time()

        # ATT write mode for this call. Callers that write a register pass
        # without_response=True: an ATT Write Command exchanges no ATT response,
        # so the module cannot return 0x0e on the write itself. The Modbus reply
        # still arrives on NOTIFY either way. Reads keep the module default.
        use_response = (
            BLE_WRITE_WITH_RESPONSE if without_response is None else not without_response
        )

        # One silent retry for the first write of a session. See
        # BLE_FIRST_WRITE_RETRY_DELAY -- the module rejects it often enough that
        # the vendor app retries it as a matter of course.
        write_attempts = 2 if self._first_send_after_connect else 1
        self._first_send_after_connect = False

        try:
            # Step 1: Write command.
            # response=True  -> ATT Write Request: waits for the device ACK and
            #   may raise a device-side 0x0e here.
            # response=False -> ATT Write Command: returns at once, so a brief
            #   settle delay is applied before the read so it does not race the
            #   device storing its result code.
            for _attempt in range(1, write_attempts + 1):
                try:
                    await self._client.write_gatt_char(
                        BLE_WRITE_UUID, data, response=use_response
                    )
                    break
                except BleakError as err:
                    if _attempt >= write_attempts:
                        raise
                    _LOGGER.warning(
                        "First write of session failed (%s); retrying once in %.2fs",
                        err,
                        BLE_FIRST_WRITE_RETRY_DELAY,
                    )
                    await asyncio.sleep(BLE_FIRST_WRITE_RETRY_DELAY)

            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("Write issued (response=%s)", use_response)

            if not use_response and BLE_WRITE_PROCESSING_DELAY > 0:
                await asyncio.sleep(BLE_WRITE_PROCESSING_DELAY)

            # Step 2: Read characteristic to get result code.
            # Note: with response=True the ATT ACK already gates this read. With
            # response=False the settle delay above (BLE_WRITE_PROCESSING_DELAY)
            # plays that role, so the read still reflects the stored result code.
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

            # Phase 2: Record successful timing
            if self._timing_collector:
                duration_ms = (time.time() - timing_start) * 1000
                self._timing_collector.record(
                    operation="ble_send",
                    duration_ms=duration_ms,
                    success=True,
                    metadata={"timeout": timeout},
                )

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

            # Phase 2: Record timeout (failure)
            if self._timing_collector:
                duration_ms = (time.time() - timing_start) * 1000
                self._timing_collector.record(
                    operation="ble_send",
                    duration_ms=duration_ms,
                    success=False,
                    metadata={"timeout": timeout, "error": "timeout"},
                )

            raise

        except DeviceRejectedCommandError:
            # Device rejected command (expected protocol error) - log without stack trace
            # Note: Already logged at DEBUG level when detected (line 319)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION REJECTED ===")

            # Phase 2: Record rejection (protocol error, not timing issue)
            if self._timing_collector:
                duration_ms = (time.time() - timing_start) * 1000
                self._timing_collector.record(
                    operation="ble_send",
                    duration_ms=duration_ms,
                    success=False,
                    metadata={"timeout": timeout, "error": "rejected"},
                )

            raise

        except BleakError as err:
            # BLE connection error (disconnected, timeout, etc.)
            # Convert to RuntimeError for proper exception propagation chain:
            # RuntimeError → UseCase handles → UpdateFailed → ConfigEntryNotReady
            _LOGGER.warning("BLE connection error during send: %s", err)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION CONNECTION ERROR ===")
            _LOGGER.debug(
                "[SRNE_TRACE] send() BleakError err_type=%s err=%s",
                type(err).__name__,
                err,
            )

            # Phase 2: Record connection error
            if self._timing_collector:
                duration_ms = (time.time() - timing_start) * 1000
                self._timing_collector.record(
                    operation="ble_send",
                    duration_ms=duration_ms,
                    success=False,
                    metadata={"timeout": timeout, "error": "ble_connection"},
                )

            # Force disconnect to ensure clean state
            await self.disconnect(reason="send_bleak_error")
            raise TransportConnectionLostError(
                f"BLE connection lost during send: {err}"
            ) from err

        except Exception as err:
            _LOGGER.error("BLE operation failed with exception: %s", err, exc_info=True)
            _LOGGER.debug("=== BLE WRITE-READ-NOTIFY OPERATION FAILED ===")

            # Phase 2: Record unexpected error
            if self._timing_collector:
                duration_ms = (time.time() - timing_start) * 1000
                self._timing_collector.record(
                    operation="ble_send",
                    duration_ms=duration_ms,
                    success=False,
                    metadata={"timeout": timeout, "error": "unexpected"},
                )

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
