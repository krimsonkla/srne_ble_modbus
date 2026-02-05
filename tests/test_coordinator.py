"""Tests for the SRNE Inverter coordinator module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.exc import BleakError

from custom_components.srne_inverter.coordinator import (
    SRNEDataUpdateCoordinator,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


@pytest.fixture
def mock_ble_device():
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "E6-Test"
    return device


@pytest.fixture
def mock_ble_client():
    """Create a mock BLE client."""
    client = MagicMock()
    client.is_connected = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    return client


class TestSRNEDataUpdateCoordinator:
    """Test the SRNE data update coordinator."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_hass, mock_config_entry):
        """Test coordinator initialization."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        assert coordinator._address == "AA:BB:CC:DD:EE:FF"
        assert coordinator._client is None
        assert coordinator._ble_device is None

    @pytest.mark.asyncio
    async def test_update_data_success(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test successful data update."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._client = mock_ble_client
        coordinator._ble_device = mock_ble_device

        # Mock successful response - need 4 elements for batch read at 0x0100
        async def mock_read_register(register, count=1, slave_id=1):
            if register == 0x0100 and count == 4:
                return {
                    "values": [85, 524, 0, 125]
                }  # SOC, Voltage*10, Reserved, Current*10
            return {"values": [0]}

        coordinator._read_register = AsyncMock(side_effect=mock_read_register)

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()

            assert data["battery_soc"] == 85
            assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_update_data_connection_failure(self, mock_hass, mock_config_entry):
        """Test data update when connection fails."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        with patch.object(coordinator, "_ensure_connection", return_value=False):
            from homeassistant.helpers.update_coordinator import UpdateFailed

            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_ensure_connection_success(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test successful BLE connection."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        with patch(
            "custom_components.srne_inverter.coordinator.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.srne_inverter.coordinator.BleakClient",
            return_value=mock_ble_client,
        ):
            result = await coordinator._ensure_connection()

            assert result is True
            assert coordinator._client is not None
            mock_ble_client.connect.assert_called_once()
            mock_ble_client.start_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connection_ble_error(
        self, mock_hass, mock_config_entry, mock_ble_device
    ):
        """Test BLE connection error handling."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=BleakError("Connection failed"))

        with patch(
            "custom_components.srne_inverter.coordinator.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ), patch(
            "custom_components.srne_inverter.coordinator.BleakClient",
            return_value=mock_client,
        ):
            result = await coordinator._ensure_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_command_delay_enforcement(self, mock_hass, mock_config_entry):
        """Test that command delay is enforced between commands."""
        from custom_components.srne_inverter.const import COMMAND_DELAY

        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        asyncio.get_event_loop().time()
        await coordinator._enforce_command_delay()
        first_time = coordinator._last_command_time

        # Second call should wait
        await coordinator._enforce_command_delay()
        elapsed = coordinator._last_command_time - first_time

        # Should be approximately COMMAND_DELAY seconds (with small tolerance for timing variations)
        assert elapsed >= COMMAND_DELAY - 0.1  # Allow 100ms tolerance

    @pytest.mark.asyncio
    async def test_write_register_queuing(
        self, mock_hass, mock_config_entry, mock_ble_client
    ):
        """Test write register command queuing."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._client = mock_ble_client

        # Mock the notification queue to provide a response
        async def mock_notification():
            # Simulate successful write response
            header = b"\x00" * 8
            frame = bytes([0x01, 0x06, 0xDF, 0x00, 0x00, 0x01])  # Write response
            crc = ModbusProtocol.calculate_crc16(frame)
            crc_bytes = bytes([crc & 0xFF, (crc >> 8) & 0xFF])
            return header + frame + crc_bytes

        # Queue a write command
        result = await coordinator.async_write_register(0xDF00, 0x0001)

        assert result is True
        assert not coordinator._write_queue.empty()

        # Wait for write task to complete and clean up
        if coordinator._write_task:
            try:
                await asyncio.wait_for(coordinator._write_task, timeout=0.5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                coordinator._write_task.cancel()
                try:
                    await coordinator._write_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_hass, mock_config_entry, mock_ble_client):
        """Test coordinator shutdown."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._client = mock_ble_client

        await coordinator.async_shutdown()

        mock_ble_client.stop_notify.assert_called_once()
        mock_ble_client.disconnect.assert_called_once()
        assert coordinator._client is None


class TestSignedIntConversion:
    """Test Round 3 signed integer conversion."""

    def test_positive_values_unchanged(self):
        """Test positive values remain unchanged."""
        assert SRNEDataUpdateCoordinator._to_signed_int16(0) == 0
        assert SRNEDataUpdateCoordinator._to_signed_int16(100) == 100
        assert SRNEDataUpdateCoordinator._to_signed_int16(32767) == 32767

    def test_negative_values_converted(self):
        """Test negative values converted from unsigned."""
        assert SRNEDataUpdateCoordinator._to_signed_int16(65535) == -1
        assert SRNEDataUpdateCoordinator._to_signed_int16(65436) == -100
        assert SRNEDataUpdateCoordinator._to_signed_int16(64336) == -1200
        assert SRNEDataUpdateCoordinator._to_signed_int16(32768) == -32768

    def test_boundary_values(self):
        """Test boundary values."""
        # Just below sign bit
        assert SRNEDataUpdateCoordinator._to_signed_int16(32767) == 32767
        # Sign bit set
        assert SRNEDataUpdateCoordinator._to_signed_int16(32768) == -32768
        # Maximum negative
        assert SRNEDataUpdateCoordinator._to_signed_int16(65535) == -1


class TestRound3CoordinatorBatchReads:
    """Test Round 3 coordinator batch register reads."""

    @pytest.mark.asyncio
    async def test_batch_read_all_registers(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test coordinator reads all Round 3 registers."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        # Mock register responses
        register_responses = {
            0x0100: [75, 524, 0, 125],  # SOC, Voltage*10, Reserved, Current*10
            0x0107: [3500],  # PV Power
            0x0109: [64336],  # Grid Power (-1200 as unsigned)
            0x010D: [2300],  # Load Power
            0x0221: [452],  # Inverter Temp (45.2 * 10) - DC-AC heatsink
            0x0220: [285],  # Battery Temp (28.5 * 10) - DC-DC heatsink
            0x0210: [5],  # Machine State
            0xE204: [0],  # Priority (Solar First) - Output Priority register
        }

        async def mock_read_register(reg, count=1, slave_id=1):
            if reg in register_responses:
                return {"values": register_responses[reg]}
            return None

        coordinator._read_register = mock_read_register

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()

            # Assert all values present and correctly scaled
            assert data["battery_soc"] == 75
            assert data["battery_voltage"] == pytest.approx(52.4)  # 524 * 0.1
            assert data["battery_current"] == pytest.approx(12.5)  # 125 * 0.1
            assert data["pv_power"] == 3500
            assert data["grid_power"] == -1200  # Signed conversion
            assert data["load_power"] == 2300
            assert data["inverter_temperature"] == pytest.approx(45.2)  # 452 * 0.1
            assert data["battery_temperature"] == pytest.approx(28.5)  # 285 * 0.1
            assert data["machine_state"] == 5
            assert data["energy_priority"] == 0
            assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_partial_register_failure(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test coordinator handles partial register read failures gracefully."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        # Mock with some failures
        async def mock_read_with_failures(reg, count=1, slave_id=1):
            if reg == 0x0100:
                return {"values": [75, 524, 0, 125]}
            elif reg == 0x0107:
                return None  # Simulate PV power read failure
            elif reg == 0x0109:
                return {"values": [1200]}
            elif reg == 0x010D:
                return {"values": [2300]}
            elif reg == 0x011A:
                return {"values": [452]}
            elif reg == 0x011C:
                return {"values": [285]}
            elif reg == 0x0210:
                return {"values": [5]}
            elif reg == 0xDF01:
                return {"values": [0]}
            return {"values": [0]}

        coordinator._read_register = mock_read_with_failures

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()

            # Assert: Should have battery data and grid power, missing PV power
            assert data["battery_soc"] == 75
            assert data["battery_voltage"] == pytest.approx(52.4)
            assert "pv_power" not in data  # Failed read
            assert "grid_power" in data
            assert data["load_power"] == 2300

    @pytest.mark.asyncio
    async def test_signed_current_charging(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test battery current reads correctly when charging (positive)."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        async def mock_read_register(reg, count=1, slave_id=1):
            if reg == 0x0100:
                return {"values": [75, 524, 0, 125]}  # Current = 12.5A charging
            return {"values": [0]}

        coordinator._read_register = mock_read_register

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()
            assert data["battery_current"] == pytest.approx(12.5)  # Positive = charging

    @pytest.mark.asyncio
    async def test_signed_current_discharging(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test battery current reads correctly when discharging (negative)."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        async def mock_read_register(reg, count=1, slave_id=1):
            if reg == 0x0100:
                # Current = -8.3A discharging (65453 = -83 in signed 16-bit)
                return {"values": [75, 524, 0, 65453]}
            return {"values": [0]}

        coordinator._read_register = mock_read_register

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()
            assert data["battery_current"] == pytest.approx(
                -8.3
            )  # Negative = discharging

    @pytest.mark.asyncio
    async def test_grid_power_importing(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test grid power reads correctly when importing (positive)."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        async def mock_read_register(reg, count=1, slave_id=1):
            if reg == 0x0109:
                return {"values": [1800]}  # Importing 1800W
            elif reg == 0x0100:
                return {"values": [75, 524, 0, 125]}
            return {"values": [0]}

        coordinator._read_register = mock_read_register

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()
            assert data["grid_power"] == 1800  # Positive = importing

    @pytest.mark.asyncio
    async def test_grid_power_exporting(
        self, mock_hass, mock_config_entry, mock_ble_device, mock_ble_client
    ):
        """Test grid power reads correctly when exporting (negative)."""
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)
        coordinator._ble_device = mock_ble_device
        coordinator._client = mock_ble_client

        async def mock_read_register(reg, count=1, slave_id=1):
            if reg == 0x0109:
                # -1200W export (64336 = -1200 in signed 16-bit)
                return {"values": [64336]}
            elif reg == 0x0100:
                return {"values": [75, 524, 0, 125]}
            return {"values": [0]}

        coordinator._read_register = mock_read_register

        with patch.object(coordinator, "_ensure_connection", return_value=True):
            data = await coordinator._async_update_data()
            assert data["grid_power"] == -1200  # Negative = exporting


class TestConnectionDropRecovery:
    """Test connection drop detection and recovery in coordinator.

    These tests verify the connection recovery implementation from Phase 1 and Phase 2.
    """

    @pytest.mark.asyncio
    async def test_coordinator_handles_use_case_connection_error(
        self, mock_hass, mock_config_entry
    ):
        """Test coordinator handles RuntimeError from use case.

        When RefreshDataUseCase raises RuntimeError due to connection loss,
        the coordinator should convert it to UpdateFailed for Home Assistant.
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        # Mock use case to raise connection error
        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = RuntimeError(
            "BLE connection lost - reconnection needed"
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Act & Assert
        with pytest.raises(UpdateFailed, match="BLE connection lost"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_coordinator_handles_circuit_breaker_error(
        self, mock_hass, mock_config_entry
    ):
        """Test coordinator handles circuit breaker error from transport."""
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        # Mock use case to raise circuit breaker error
        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = RuntimeError(
            "Connection circuit breaker opened after 3 timeouts"
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Act & Assert
        with pytest.raises(UpdateFailed, match="Circuit breaker opened"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_first_refresh_handles_connection_failure(
        self, mock_hass, mock_config_entry
    ):
        """Test async_config_entry_first_refresh handles connection failure.

        Home Assistant calls this on startup. Connection failures should
        be handled gracefully (HA will retry automatically).
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        # Mock use case to fail connection
        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = RuntimeError(
            "BLE connection lost - reconnection needed"
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Act & Assert
        # First refresh should raise UpdateFailed, which HA will handle
        with pytest.raises(UpdateFailed):
            await coordinator.async_config_entry_first_refresh()

    @pytest.mark.asyncio
    async def test_recovery_on_next_update_cycle(self, mock_hass, mock_config_entry):
        """Test successful data retrieval on next update after connection recovery.

        Simulates:
        1. Update fails due to connection loss (raises UpdateFailed)
        2. Connection is recovered
        3. Next update succeeds
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("BLE connection lost - reconnection needed")

            # Second call succeeds
            from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
                RefreshDataResult,
            )
            from datetime import datetime

            return RefreshDataResult(
                data={
                    "battery_soc": 85,
                    "battery_voltage": 52.4,
                    "connected": True,
                    "update_duration": 1.5,
                    "total_updates": 1,
                    "failed_reads": 0,
                    "last_update_time": datetime.now(),
                },
                success=True,
                duration=1.5,
                failed_reads=0,
            )

        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = mock_execute
        coordinator._refresh_data_use_case = mock_use_case

        # Act - First update (should fail)
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        # Act - Second update (should succeed)
        data = await coordinator._async_update_data()

        # Assert
        assert data["battery_soc"] == 85
        assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_no_zombie_tasks_after_connection_failure(
        self, mock_hass, mock_config_entry
    ):
        """Test no background tasks remain after connection failure.

        When connection fails, all tasks should be cleaned up properly.
        No orphaned tasks should remain running.
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        # Mock use case to fail
        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = RuntimeError(
            "BLE connection lost - reconnection needed"
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Get initial task count
        initial_tasks = len([t for t in asyncio.all_tasks() if not t.done()])

        # Act
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        # Let any pending tasks complete
        await asyncio.sleep(0)

        # Assert
        final_tasks = len([t for t in asyncio.all_tasks() if not t.done()])
        # Should not have created new zombie tasks
        assert final_tasks <= initial_tasks

    @pytest.mark.asyncio
    async def test_connection_state_reflected_in_data(
        self, mock_hass, mock_config_entry
    ):
        """Test connection state is properly reflected in returned data.

        The 'connected' field should accurately reflect connection status.
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
            RefreshDataResult,
        )
        from datetime import datetime

        # Mock successful connection
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = RefreshDataResult(
            data={
                "battery_soc": 85,
                "connected": True,
                "update_duration": 1.5,
                "total_updates": 1,
                "failed_reads": 0,
                "last_update_time": datetime.now(),
            },
            success=True,
            duration=1.5,
            failed_reads=0,
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Act
        data = await coordinator._async_update_data()

        # Assert
        assert data["connected"] is True

    @pytest.mark.asyncio
    async def test_multiple_consecutive_connection_failures(
        self, mock_hass, mock_config_entry
    ):
        """Test handling of multiple consecutive connection failures.

        Coordinator should consistently raise UpdateFailed for each failure.
        Home Assistant will handle retry logic.
        """
        # Arrange
        coordinator = SRNEDataUpdateCoordinator(mock_hass, mock_config_entry)

        mock_use_case = AsyncMock()
        mock_use_case.execute.side_effect = RuntimeError(
            "BLE connection lost - reconnection needed"
        )
        coordinator._refresh_data_use_case = mock_use_case

        # Act & Assert - Multiple failures
        for i in range(3):
            with pytest.raises(UpdateFailed, match="BLE connection lost"):
                await coordinator._async_update_data()
