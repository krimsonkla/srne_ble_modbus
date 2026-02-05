"""Tests for BLE Transport connection recovery.

This test suite verifies the connection drop detection and recovery
mechanisms in the BLE transport layer.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from bleak.exc import BleakError

from custom_components.srne_inverter.infrastructure.transport.ble_transport import (
    BLETransport,
)
from custom_components.srne_inverter.domain.exceptions import (
    DeviceRejectedCommandError,
)
from custom_components.srne_inverter.const import (
    MODBUS_RESPONSE_TIMEOUT,
    MAX_CONSECUTIVE_TIMEOUTS,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def transport(mock_hass):
    """Create BLE transport instance."""
    return BLETransport(mock_hass)


@pytest.fixture
def mock_bleak_client():
    """Create mock BleakClient."""
    client = Mock()
    client.is_connected = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=b"\x2d\x2d\x2d\x2d")  # Dash ACK
    return client


class TestConnectionDropDetection:
    """Test connection drop detection during send operations."""

    @pytest.mark.asyncio
    async def test_send_fails_fast_when_disconnected(self, transport):
        """Test that send() raises RuntimeError immediately when disconnected.

        This verifies the fail-fast connection check at line 311 of ble_transport.py.
        When transport.is_connected returns False, send() should raise RuntimeError
        immediately without attempting any BLE operations.
        """
        # Arrange
        transport._connected = False
        transport._client = None
        command = b"\x01\x03\x01\x00\x00\x01"

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="BLE connection lost - reconnection needed"
        ):
            await transport.send(command)

    @pytest.mark.asyncio
    async def test_send_detects_client_disconnection(
        self, transport, mock_bleak_client
    ):
        """Test send() detects when BleakClient reports disconnected.

        Even if _connected flag is True, if the underlying BleakClient
        reports is_connected=False, the send should fail fast.
        """
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client
        mock_bleak_client.is_connected = False  # Simulate connection loss
        command = b"\x01\x03\x01\x00\x00\x01"

        # Act & Assert
        with pytest.raises(
            RuntimeError, match="BLE connection lost - reconnection needed"
        ):
            await transport.send(command)

    @pytest.mark.asyncio
    async def test_send_handles_mid_operation_disconnect(
        self, transport, mock_bleak_client
    ):
        """Test handling of disconnection during send operation.

        Simulates the case where connection is lost between the initial
        check and the actual write operation.
        """
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client

        # Simulate disconnect during write
        mock_bleak_client.write_gatt_char.side_effect = BleakError("Connection lost")
        command = b"\x01\x03\x01\x00\x00\x01"

        # Act & Assert
        with pytest.raises((BleakError, RuntimeError)):
            await transport.send(command)

    @pytest.mark.asyncio
    async def test_is_connected_property_checks_all_conditions(
        self, transport, mock_bleak_client
    ):
        """Test is_connected property validates all connection requirements.

        The property should check:
        1. _connected flag is True
        2. _client is not None
        3. _client.is_connected is True
        """
        # All conditions met
        transport._connected = True
        transport._client = mock_bleak_client
        mock_bleak_client.is_connected = True
        assert transport.is_connected is True

        # _connected flag False
        transport._connected = False
        assert transport.is_connected is False

        # _client is None
        transport._connected = True
        transport._client = None
        assert transport.is_connected is False

        # BleakClient reports disconnected
        transport._connected = True
        transport._client = mock_bleak_client
        mock_bleak_client.is_connected = False
        assert transport.is_connected is False


class TestCircuitBreakerBehavior:
    """Test circuit breaker behavior for zombie connections."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_max_timeouts(
        self, transport, mock_bleak_client
    ):
        """Test circuit breaker opens after MAX_CONSECUTIVE_TIMEOUTS.

        After MAX_CONSECUTIVE_TIMEOUTS consecutive timeout errors,
        the circuit breaker should open and force a disconnect.
        """
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client

        command = b"\x01\x03\x01\x00\x00\x01"

        # Act - Generate MAX_CONSECUTIVE_TIMEOUTS timeouts
        for i in range(MAX_CONSECUTIVE_TIMEOUTS):
            # Queue never gets notification (causes timeout)
            with pytest.raises(asyncio.TimeoutError):
                await transport.send(command, timeout=0.1)
            assert transport._consecutive_timeouts == i + 1

        # Next send should trigger circuit breaker
        with pytest.raises(RuntimeError, match="Connection circuit breaker opened"):
            await transport.send(command)

        # Verify disconnect was called
        assert transport._connected is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(
        self, transport, mock_bleak_client
    ):
        """Test circuit breaker resets after successful operation."""
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client
        transport._consecutive_timeouts = 2  # Pre-load with timeouts

        command = b"\x01\x03\x01\x00\x00\x01"

        # Mock successful response - put in queue AFTER clear is called by send()
        response = b"\x01\x03\x04\x00\x01\x00\x02"

        # Patch the queue's get to return our response
        original_get = transport._notification_queue.get

        async def mock_get():
            # First time, put response then get it
            if transport._notification_queue.empty():
                await transport._notification_queue.put(response)
            return await original_get()

        transport._notification_queue.get = mock_get

        # Act
        result = await transport.send(command)

        # Assert
        assert result == response
        assert transport._consecutive_timeouts == 0  # Reset!

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_disconnect(
        self, transport, mock_bleak_client
    ):
        """Test circuit breaker resets on manual disconnect."""
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client
        transport._consecutive_timeouts = 5

        # Act
        await transport.disconnect()

        # Assert
        assert transport._consecutive_timeouts == 0


class TestConnectionRecovery:
    """Test connection recovery scenarios."""

    @pytest.mark.asyncio
    async def test_connect_closes_stale_connections_first(self, transport, mock_hass):
        """Test that connect() closes stale connections before connecting.

        This is critical for preventing zombie connections (line 121).
        """
        # Arrange
        address = "AA:BB:CC:DD:EE:FF"
        mock_ble_device = Mock()
        mock_ble_device.address = address

        with patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.close_stale_connections_by_address"
        ) as mock_close_stale, patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.establish_connection"
        ) as mock_establish:

            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.start_notify = AsyncMock()
            mock_establish.return_value = mock_client

            # Act
            success = await transport.connect(address)

            # Assert
            assert success is True
            mock_close_stale.assert_called_once_with(address)

    @pytest.mark.asyncio
    async def test_successful_reconnection_after_disconnect(self, transport, mock_hass):
        """Test successful reconnection after connection loss."""
        # Arrange
        address = "AA:BB:CC:DD:EE:FF"
        mock_ble_device = Mock()
        mock_ble_device.address = address

        with patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.close_stale_connections_by_address"
        ), patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.establish_connection"
        ) as mock_establish:

            mock_client = Mock()
            mock_client.is_connected = True
            mock_client.start_notify = AsyncMock()
            mock_establish.return_value = mock_client

            # First connection
            success = await transport.connect(address)
            assert success is True
            assert transport.is_connected is True

            # Simulate disconnect
            await transport.disconnect()
            assert transport.is_connected is False

            # Reconnect
            mock_client.is_connected = True  # Reset for reconnection
            success = await transport.connect(address)
            assert success is True
            assert transport.is_connected is True


class TestNoZombieTasks:
    """Test that no background tasks remain after connection loss."""

    @pytest.mark.asyncio
    async def test_disconnect_clears_notification_queue(
        self, transport, mock_bleak_client
    ):
        """Test that disconnect clears notification queue."""
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client

        # Add notifications to queue
        await transport._notification_queue.put(b"notification1")
        await transport._notification_queue.put(b"notification2")
        assert transport._notification_queue.qsize() == 2

        # Act
        await transport.disconnect()

        # Assert
        assert transport._notification_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_no_pending_tasks_after_disconnect(
        self, transport, mock_bleak_client
    ):
        """Test that no tasks remain pending after disconnect."""
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client

        # Get initial task count
        initial_tasks = len([t for t in asyncio.all_tasks() if not t.done()])

        # Act
        await transport.disconnect()
        await asyncio.sleep(0)  # Let tasks complete

        # Assert
        final_tasks = len([t for t in asyncio.all_tasks() if not t.done()])
        # Should not have created new pending tasks
        assert final_tasks <= initial_tasks


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_send_with_device_rejected_error(self, transport, mock_bleak_client):
        """Test handling of DeviceRejectedCommandError."""
        # Arrange
        transport._connected = True
        transport._client = mock_bleak_client

        command = b"\x01\x03\x01\x00\x00\x01"

        # Mock the queue's get to return dash pattern after clear
        dash_response = b"\x2d\x2d\x2d\x2d\x00\x00"

        original_get = transport._notification_queue.get

        async def mock_get():
            # After clear is called, put the dash pattern
            if transport._notification_queue.empty():
                await transport._notification_queue.put(dash_response)
            return await original_get()

        transport._notification_queue.get = mock_get

        # Act & Assert
        with pytest.raises(DeviceRejectedCommandError, match="Register unsupported"):
            await transport.send(command)

        # Verify timeout counter NOT incremented (protocol error, not timeout)
        assert transport._consecutive_timeouts == 0

    @pytest.mark.asyncio
    async def test_disconnect_when_already_disconnected(self, transport):
        """Test disconnect is idempotent."""
        # Arrange
        transport._connected = False
        transport._client = None

        # Act - Should not raise
        await transport.disconnect()

        # Assert
        assert transport.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_timeout_returns_false(self, transport, mock_hass):
        """Test that connection timeout returns False."""
        # Arrange
        address = "AA:BB:CC:DD:EE:FF"
        mock_ble_device = Mock()

        with patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.close_stale_connections_by_address"
        ), patch(
            "custom_components.srne_inverter.infrastructure.transport.ble_transport.establish_connection",
            side_effect=asyncio.TimeoutError("Connection timeout"),
        ):

            # Act
            success = await transport.connect(address)

            # Assert
            assert success is False
            assert transport.is_connected is False
