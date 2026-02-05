"""Tests for the SRNE Inverter coordinator module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.exc import BleakError

from custom_components.srne_inverter.coordinator import (
    ModbusProtocol,
    SRNEDataUpdateCoordinator,
)


class TestModbusProtocol:
    """Test the Modbus protocol implementation."""

    def test_calculate_crc16(self):
        """Test CRC-16 calculation."""
        # Test with known Modbus frame
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        crc = ModbusProtocol.calculate_crc16(data)
        # Expected CRC for this frame (verify with Modbus calculator)
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_build_read_command(self):
        """Test building a read command."""
        command = ModbusProtocol.build_read_command(
            slave_id=0x01, register=0x0100, count=1
        )

        # Verify structure: slave_id + func + reg_high + reg_low + count_high + count_low + crc_low + crc_high
        assert len(command) == 8
        assert command[0] == 0x01  # Slave ID
        assert command[1] == 0x03  # Function code (read)
        assert command[2] == 0x01  # Register high byte
        assert command[3] == 0x00  # Register low byte
        assert command[4] == 0x00  # Count high byte
        assert command[5] == 0x01  # Count low byte

    def test_build_write_command(self):
        """Test building a write command."""
        command = ModbusProtocol.build_write_command(
            slave_id=0x01, register=0xDF00, value=0x0001
        )

        assert len(command) == 8
        assert command[0] == 0x01  # Slave ID
        assert command[1] == 0x06  # Function code (write)
        assert command[2] == 0xDF  # Register high byte
        assert command[3] == 0x00  # Register low byte
        assert command[4] == 0x00  # Value high byte
        assert command[5] == 0x01  # Value low byte

    def test_decode_response_read_success(self):
        """Test decoding a successful read response."""
        # Simulate response: 8-byte header + slave_id + func + byte_count + data + crc
        header = b"\x00" * 8
        data_bytes = bytes([0x00, 0x55])  # Value 85
        frame = bytes([0x01, 0x03, 0x02]) + data_bytes
        crc = ModbusProtocol.calculate_crc16(frame)
        crc_bytes = bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        response = header + frame + crc_bytes

        decoded = ModbusProtocol.decode_response(response)

        assert decoded is not None
        assert decoded["slave_addr"] == 0x01
        assert decoded["function"] == 0x03
        assert decoded["values"] == [0x0055]

    def test_decode_response_error(self):
        """Test decoding an error response."""
        # Error response: func_code | 0x80 + error_code
        header = b"\x00" * 8
        frame = bytes([0x01, 0x83, 0x02])  # Exception code 0x02
        crc = ModbusProtocol.calculate_crc16(frame)
        crc_bytes = bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        response = header + frame + crc_bytes

        decoded = ModbusProtocol.decode_response(response)

        assert decoded is not None
        assert "error" in decoded
        assert decoded["error"] == 0x02

    def test_decode_response_crc_mismatch(self):
        """Test decoding with invalid CRC."""
        header = b"\x00" * 8
        frame = bytes([0x01, 0x03, 0x02, 0x00, 0x55])
        bad_crc = bytes([0xFF, 0xFF])  # Invalid CRC
        response = header + frame + bad_crc

        decoded = ModbusProtocol.decode_response(response)

        assert decoded is None  # Should return None on CRC error


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
