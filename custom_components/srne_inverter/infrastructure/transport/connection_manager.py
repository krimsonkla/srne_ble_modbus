"""Connection manager for BLE transport lifecycle.

This module implements connection lifecycle management with:
- Exponential backoff retry logic
- Connection failure tracking
- Automatic reconnection
- State management

Extracted from coordinator.py connection logic.
"""

import asyncio
import time
import logging
from typing import Optional

from ...domain.interfaces import IConnectionManager, ITransport
from ..decorators import handle_transport_errors
from ..state_machines import (
    ConnectionStateMachine,
    ConnectionState,
    ConnectionEvent,
)

_LOGGER = logging.getLogger(__name__)


class ConnectionManager(IConnectionManager):
    """Manages BLE connection lifecycle with retry logic.

    This implementation:
    - Tracks consecutive failures
    - Implements exponential backoff
    - Provides connection state
    - Handles automatic reconnection

    Attributes:
        _transport: Underlying transport
        _address: Device address
        _consecutive_failures: Count of consecutive failed attempts
        _last_connection_attempt: Timestamp of last attempt
        _backoff_time: Current backoff delay
        _state: Current connection state

    Example:
        >>> transport = BLETransport(hass)
        >>> manager = ConnectionManager(transport)
        >>> success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        >>> if success:
        ...     # Use transport
    """

    # Constants
    MAX_CONSECUTIVE_FAILURES = 5
    INITIAL_BACKOFF = 1.0  # seconds
    MAX_BACKOFF = 300.0  # 5 minutes

    def __init__(self, transport: ITransport):
        """Initialize connection manager.

        Args:
            transport: Transport to manage
        """
        self._transport = transport
        self._address: Optional[str] = None
        self._consecutive_failures = 0
        self._last_connection_attempt = 0.0
        self._backoff_time = self.INITIAL_BACKOFF
        self._state_machine = ConnectionStateMachine()

        # Register state callbacks for logging
        self._state_machine.on_state(ConnectionState.CONNECTED, self._on_connected)
        self._state_machine.on_state(ConnectionState.FAILED, self._on_failed)

    def _on_connected(self):
        """Callback when connection established."""
        _LOGGER.info("Connection established successfully")

    def _on_failed(self):
        """Callback when connection failed."""
        _LOGGER.warning("Connection failed")

    def _handle_disconnect(self, client):
        """Handle unexpected BLE disconnect event.

        This callback is registered with Bleak and called automatically
        when the BLE connection is lost. It triggers the connection
        lost handler which updates state and increments failure counter.

        Args:
            client: BleakClient that disconnected

        Note:
            This is called from Bleak's event loop and must not be async.
            We schedule the async handler using create_task.
        """
        # Extract diagnostic information from client
        client_address = getattr(client, "address", "unknown")
        is_connected = getattr(client, "is_connected", None)

        # Try to get RSSI if available (platform-dependent)
        rssi = None
        try:
            # RSSI may be available on some platforms via internal backend
            if hasattr(client, "_backend"):
                rssi = getattr(client._backend, "rssi", None)
        except Exception:
            pass  # RSSI not available on this platform

        _LOGGER.warning(
            "BLE disconnect callback triggered - Address: %s, Client connected state: %s, RSSI: %s, "
            "Current failures: %d, Current state: %s",
            client_address,
            is_connected,
            f"{rssi}dBm" if rssi is not None else "unavailable",
            self._consecutive_failures,
            self._state_machine.state.name if self._state_machine else "unknown",
        )

        # Schedule async handler - can't await in callback
        asyncio.create_task(self.handle_connection_lost())

    @handle_transport_errors("Ensure connection", reraise=False, default_return=False)
    async def ensure_connected(self, address: str, max_retries: int = 3) -> bool:
        """Ensure connection is established with retry logic.

        This method implements exponential backoff:
        1. Check if already connected
        2. Check failure count and backoff time
        3. Attempt connection
        4. Update failure tracking on result

        Uses state machine to track connection lifecycle.

        Args:
            address: Device address to connect to
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            True if connected successfully

        Example:
            >>> success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
            >>> assert success is True
        """
        self._address = address

        # Already connected?
        if self._state_machine.is_connected:
            return True

        # Check if we can initiate connection
        if not self._state_machine.can_connect:
            _LOGGER.warning(
                "Cannot connect in state: %s", self._state_machine.state.name
            )
            return False

        # Check if we've hit max failures
        if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            time_since_last = time.time() - self._last_connection_attempt

            if time_since_last >= self.MAX_BACKOFF:
                # Reset after max backoff period
                _LOGGER.info(
                    "Resetting failure counter after %.1fs - attempting recovery",
                    time_since_last,
                )
                self._consecutive_failures = 0
                self._backoff_time = self.INITIAL_BACKOFF
            else:
                # Still in backoff period
                _LOGGER.error(
                    "Maximum consecutive connection failures (%d) reached. "
                    "Waiting %.1fs before reset attempt.",
                    self.MAX_CONSECUTIVE_FAILURES,
                    self.MAX_BACKOFF - time_since_last,
                )
                self._state = "failed"
                return False

        # Apply exponential backoff if we have failures
        if self._consecutive_failures > 0:
            current_time = time.time()
            time_since_last = current_time - self._last_connection_attempt

            if time_since_last < self._backoff_time:
                wait_time = self._backoff_time - time_since_last
                _LOGGER.debug(
                    "Waiting %.1fs before reconnection (backoff: %.1fs, failures: %d/%d)",
                    wait_time,
                    self._backoff_time,
                    self._consecutive_failures,
                    self.MAX_CONSECUTIVE_FAILURES,
                )
                await asyncio.sleep(wait_time)

        # Attempt connection
        self._last_connection_attempt = time.time()

        # Transition to CONNECTING state
        # Use RETRY event if in RECONNECTING state, otherwise CONNECT
        if self._state_machine.state == ConnectionState.RECONNECTING:
            self._state_machine.transition(ConnectionEvent.RETRY)
        else:
            self._state_machine.transition(ConnectionEvent.CONNECT)

        try:
            _LOGGER.debug("Attempting connection to %s", address)
            # Wire up disconnect callback for automatic zombie connection detection
            success = await self._transport.connect(
                address, disconnected_callback=self._handle_disconnect
            )

            if success:
                # Connection successful - reset failure tracking
                _LOGGER.info("Connected successfully to %s", address)
                self._consecutive_failures = 0
                self._backoff_time = self.INITIAL_BACKOFF
                self._state_machine.transition(ConnectionEvent.CONNECT_SUCCESS)
                return True
            else:
                # Connection failed
                self._handle_connection_failure()
                self._state_machine.transition(ConnectionEvent.CONNECT_FAILED)
                return False
        except Exception:
            # Exception during connection - handle as failure
            self._handle_connection_failure()
            self._state_machine.transition(ConnectionEvent.CONNECT_FAILED)
            raise

    async def handle_connection_lost(self) -> None:
        """Handle unexpected connection loss.

        Called when connection is detected as lost.
        Updates state and increments failure counter.

        No automatic retry - let coordinator decide.
        Exception propagation triggers ConfigEntryNotReady on first refresh,
        allowing Home Assistant's built-in retry mechanism to handle recovery.

        Example:
            >>> await manager.handle_connection_lost()
            >>> assert manager.connection_state == "reconnecting"
        """
        _LOGGER.warning("Connection lost to %s", self._address)
        self._consecutive_failures += 1
        self._backoff_time = min(self._backoff_time * 2, self.MAX_BACKOFF)

        # Transition to RECONNECTING if currently connected, otherwise force it
        if not self._state_machine.transition(ConnectionEvent.CONNECTION_LOST):
            # If not in CONNECTED state, force RECONNECTING
            self._state_machine.force_state(ConnectionState.RECONNECTING)

        _LOGGER.debug(
            "Connection lost, backoff increased to %.1fs (failures: %d/%d)",
            self._backoff_time,
            self._consecutive_failures,
            self.MAX_CONSECUTIVE_FAILURES,
        )

    @property
    def connection_state(self) -> str:
        """Get current connection state.

        Returns:
            State: "disconnected", "connecting", "connected",
                   "reconnecting", "failed"

        Example:
            >>> state = manager.connection_state
            >>> assert state in ["disconnected", "connecting", "connected"]
        """
        return self._state_machine.state.name.lower()

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            True if in CONNECTED state
        """
        return self._state_machine.is_connected

    def _handle_connection_failure(self) -> None:
        """Handle connection failure.

        Updates failure tracking and backoff time.
        """
        self._consecutive_failures += 1
        self._backoff_time = min(self._backoff_time * 2, self.MAX_BACKOFF)

        _LOGGER.debug(
            "Connection failed, backoff increased to %.1fs (failures: %d/%d)",
            self._backoff_time,
            self._consecutive_failures,
            self.MAX_CONSECUTIVE_FAILURES,
        )

    def reset_failures(self) -> None:
        """Reset failure tracking.

        Called to force immediate retry (e.g., user-triggered reconnect).

        Example:
            >>> manager.reset_failures()
            >>> success = await manager.ensure_connected(address)
        """
        _LOGGER.info("Resetting connection failure tracking")
        self._consecutive_failures = 0
        self._backoff_time = self.INITIAL_BACKOFF
        self._state_machine.reset()

    def get_failure_info(self) -> dict:
        """Get current failure tracking info.

        Returns:
            Dictionary with failure statistics

        Example:
            >>> info = manager.get_failure_info()
            >>> print(f"Failures: {info['consecutive_failures']}")
        """
        return {
            "consecutive_failures": self._consecutive_failures,
            "backoff_time": self._backoff_time,
            "last_attempt": self._last_connection_attempt,
            "state": self.connection_state,
        }
