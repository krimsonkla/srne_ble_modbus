"""Tests for ModbusRTUProtocol implementation.

These tests verify the protocol implementation matches the original
coordinator behavior and properly implements the IProtocol interface.
"""

import pytest
import struct
from custom_components.srne_inverter.infrastructure.protocol import (
    ModbusCRC16,
    ModbusRTUProtocol,
)
from custom_components.srne_inverter.const import (
    FUNC_READ_HOLDING,
    FUNC_WRITE_SINGLE,
)


@pytest.fixture
def crc():
    """Create CRC calculator."""
    return ModbusCRC16()


@pytest.fixture
def protocol(crc):
    """Create protocol instance."""
    return ModbusRTUProtocol(crc)


class TestModbusRTUProtocolInitialization:
    """Test protocol initialization."""

    def test_create_with_crc(self, crc):
        """Test creating protocol with CRC calculator."""
        protocol = ModbusRTUProtocol(crc)
        assert protocol is not None

    def test_create_with_custom_slave_id(self, crc):
        """Test creating protocol with custom slave ID."""
        protocol = ModbusRTUProtocol(crc, slave_id=0x02)
        assert protocol is not None


class TestBuildReadCommand:
    """Test building read holding registers commands."""

    def test_build_read_command_structure(self, protocol):
        """Verify read command has correct structure."""
        command = protocol.build_read_command(0x0100, 1)

        assert len(command) == 8  # slave + func + addr + count + crc

    def test_build_read_command_slave_id(self, protocol):
        """Verify slave ID is first byte."""
        command = protocol.build_read_command(0x0100, 1)
        assert command[0] == 0x01

    def test_build_read_command_function_code(self, protocol):
        """Verify function code is 0x03."""
        command = protocol.build_read_command(0x0100, 1)
        assert command[1] == FUNC_READ_HOLDING

    def test_build_read_command_address_big_endian(self, protocol):
        """Verify address is big-endian."""
        command = protocol.build_read_command(0x0100, 1)
        assert command[2:4] == b"\x01\x00"

    def test_build_read_command_count_big_endian(self, protocol):
        """Verify count is big-endian."""
        command = protocol.build_read_command(0x0100, 2)
        assert command[4:6] == b"\x00\x02"

    def test_build_read_command_valid_crc(self, protocol, crc):
        """Verify CRC in command is valid."""
        command = protocol.build_read_command(0x0100, 1)

        frame = command[:-2]
        crc_in_command = struct.unpack("<H", command[-2:])[0]
        calculated_crc = crc.calculate(frame)

        assert crc_in_command == calculated_crc

    def test_build_read_command_different_addresses(self, protocol):
        """Verify different addresses produce different commands."""
        cmd1 = protocol.build_read_command(0x0100, 1)
        cmd2 = protocol.build_read_command(0x0200, 1)
        assert cmd1 != cmd2

    def test_build_read_command_different_counts(self, protocol):
        """Verify different counts produce different commands."""
        cmd1 = protocol.build_read_command(0x0100, 1)
        cmd2 = protocol.build_read_command(0x0100, 2)
        assert cmd1 != cmd2


class TestBuildReadCommandValidation:
    """Test read command input validation."""

    def test_build_read_negative_address_raises_error(self, protocol):
        """Verify negative address raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_read_command(-1, 1)

    def test_build_read_address_too_large_raises_error(self, protocol):
        """Verify address > 0xFFFF raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_read_command(0x10000, 1)

    def test_build_read_count_zero_raises_error(self, protocol):
        """Verify count of 0 raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-125"):
            protocol.build_read_command(0x0100, 0)

    def test_build_read_count_too_large_raises_error(self, protocol):
        """Verify count > 125 raises ValueError."""
        with pytest.raises(ValueError, match="must be 1-125"):
            protocol.build_read_command(0x0100, 126)

    def test_build_read_min_valid_address(self, protocol):
        """Verify minimum valid address works."""
        command = protocol.build_read_command(0x0000, 1)
        assert command[2:4] == b"\x00\x00"

    def test_build_read_max_valid_address(self, protocol):
        """Verify maximum valid address works."""
        command = protocol.build_read_command(0xFFFF, 1)
        assert command[2:4] == b"\xff\xff"

    def test_build_read_min_valid_count(self, protocol):
        """Verify minimum valid count works."""
        command = protocol.build_read_command(0x0100, 1)
        assert command[4:6] == b"\x00\x01"

    def test_build_read_max_valid_count(self, protocol):
        """Verify maximum valid count works."""
        command = protocol.build_read_command(0x0100, 125)
        assert command[4:6] == b"\x00\x7d"


class TestBuildWriteCommand:
    """Test building write single register commands."""

    def test_build_write_command_structure(self, protocol):
        """Verify write command has correct structure."""
        command = protocol.build_write_command(0x0100, 300)
        assert len(command) == 8

    def test_build_write_command_function_code(self, protocol):
        """Verify function code is 0x06."""
        command = protocol.build_write_command(0x0100, 300)
        assert command[1] == FUNC_WRITE_SINGLE

    def test_build_write_command_value_big_endian(self, protocol):
        """Verify value is big-endian."""
        command = protocol.build_write_command(0x0100, 0x012C)
        assert command[4:6] == b"\x01\x2c"

    def test_build_write_command_valid_crc(self, protocol, crc):
        """Verify CRC in command is valid."""
        command = protocol.build_write_command(0x0100, 300)

        frame = command[:-2]
        crc_in_command = struct.unpack("<H", command[-2:])[0]
        calculated_crc = crc.calculate(frame)

        assert crc_in_command == calculated_crc


class TestBuildWriteCommandValidation:
    """Test write command input validation."""

    def test_build_write_negative_address_raises_error(self, protocol):
        """Verify negative address raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_write_command(-1, 300)

    def test_build_write_address_too_large_raises_error(self, protocol):
        """Verify address > 0xFFFF raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_write_command(0x10000, 300)

    def test_build_write_negative_value_raises_error(self, protocol):
        """Verify negative value raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_write_command(0x0100, -1)

    def test_build_write_value_too_large_raises_error(self, protocol):
        """Verify value > 0xFFFF raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            protocol.build_write_command(0x0100, 0x10000)


class TestDecodeReadResponse:
    """Test decoding read holding registers responses."""

    def test_decode_read_response_with_ble_header(self, protocol):
        """Verify decoding response with BLE header."""
        # Simulated response: 8-byte header + Modbus frame
        # For simplicity, we'll create a valid response manually
        # In reality, would come from device

        # Build expected response structure
        modbus_frame = bytes(
            [
                0x01,  # Slave ID
                0x03,  # Function code
                0x02,  # Byte count (1 register = 2 bytes)
                0x01,
                0x2C,  # Value = 300 (0x012C)
            ]
        )

        # Add CRC
        crc = ModbusCRC16()
        crc_value = crc.calculate(modbus_frame)
        modbus_frame_with_crc = modbus_frame + struct.pack("<H", crc_value)

        # Add BLE header
        ble_header = bytes([0x00] * 8)
        full_response = ble_header + modbus_frame_with_crc

        # Decode
        result = protocol.decode_response(full_response)

        # Verify result structure
        assert isinstance(result, dict)
        assert 0 in result  # First register
        assert result[0] == 300

    def test_decode_read_response_without_ble_header(self, protocol):
        """Verify decoding response without BLE header."""
        modbus_frame = bytes(
            [
                0x01,
                0x03,
                0x02,
                0x01,
                0x2C,
            ]
        )

        crc = ModbusCRC16()
        crc_value = crc.calculate(modbus_frame)
        full_frame = modbus_frame + struct.pack("<H", crc_value)

        result = protocol.decode_response(full_frame)
        assert isinstance(result, dict)
        assert 0 in result

    def test_decode_read_multiple_registers(self, protocol):
        """Verify decoding response with multiple registers."""
        modbus_frame = bytes(
            [
                0x01,
                0x03,
                0x04,  # 2 registers = 4 bytes
                0x01,
                0xE6,  # Register 0 = 486
                0x00,
                0xFA,  # Register 1 = 250
            ]
        )

        crc = ModbusCRC16()
        crc_value = crc.calculate(modbus_frame)
        full_frame = bytes([0x00] * 8) + modbus_frame + struct.pack("<H", crc_value)

        result = protocol.decode_response(full_frame)
        assert len(result) == 2
        assert result[0] == 486
        assert result[1] == 250


class TestDecodeWriteResponse:
    """Test decoding write single register responses."""

    def test_decode_write_response(self, protocol):
        """Verify decoding write response."""
        modbus_frame = bytes(
            [
                0x01,
                0x06,  # Slave + function
                0x01,
                0x00,  # Address = 0x0100
                0x01,
                0x2C,  # Value = 300
            ]
        )

        crc = ModbusCRC16()
        crc_value = crc.calculate(modbus_frame)
        full_frame = bytes([0x00] * 8) + modbus_frame + struct.pack("<H", crc_value)

        result = protocol.decode_response(full_frame)
        assert isinstance(result, dict)
        assert 0x0100 in result
        assert result[0x0100] == 300


class TestDecodeErrorResponse:
    """Test decoding error responses."""

    def test_decode_error_response(self, protocol):
        """Verify error response detection."""
        modbus_frame = bytes(
            [
                0x01,
                0x83,  # Error function code (0x03 | 0x80)
                0x02,  # Error code
            ]
        )

        crc = ModbusCRC16()
        crc_value = crc.calculate(modbus_frame)
        full_frame = bytes([0x00] * 8) + modbus_frame + struct.pack("<H", crc_value)

        result = protocol.decode_response(full_frame)
        assert "error" in result
        assert result["error"] == 0x02


class TestDecodeResponseValidation:
    """Test response decoding validation."""

    def test_decode_too_short_raises_error(self, protocol):
        """Verify too-short response raises ValueError."""
        with pytest.raises(ValueError, match="too short"):
            protocol.decode_response(bytes([0x01, 0x03]))

    def test_decode_invalid_crc_raises_error(self, protocol):
        """Verify invalid CRC raises ValueError."""
        modbus_frame = bytes([0x01, 0x03, 0x02, 0x01, 0x2C])
        bad_crc = bytes([0x00, 0x00])  # Wrong CRC
        full_frame = bytes([0x00] * 8) + modbus_frame + bad_crc

        with pytest.raises(ValueError, match="CRC mismatch"):
            protocol.decode_response(full_frame)


class TestProtocolInterfaceCompliance:
    """Test that ModbusRTUProtocol properly implements IProtocol."""

    def test_implements_iprotocol(self, protocol):
        """Verify protocol implements IProtocol interface."""
        from custom_components.srne_inverter.domain.interfaces import IProtocol

        assert isinstance(protocol, IProtocol)

    def test_has_required_methods(self, protocol):
        """Verify protocol has all required methods."""
        assert hasattr(protocol, "build_read_command")
        assert hasattr(protocol, "build_write_command")
        assert hasattr(protocol, "decode_response")
        assert callable(protocol.build_read_command)
        assert callable(protocol.build_write_command)
        assert callable(protocol.decode_response)


class TestProtocolCompatibility:
    """Test compatibility with original coordinator implementation."""

    def test_read_command_matches_original(self, protocol, crc):
        """Verify read command matches original coordinator output."""
        command = protocol.build_read_command(0x0100, 1)

        # This should match exactly what coordinator.ModbusProtocol.build_read_command produces
        assert command[0] == 0x01  # Slave
        assert command[1] == 0x03  # Function
        assert command[2:4] == b"\x01\x00"  # Address
        assert command[4:6] == b"\x00\x01"  # Count

        # CRC should be valid
        frame = command[:-2]
        crc_value = struct.unpack("<H", command[-2:])[0]
        assert crc_value == crc.calculate(frame)

    def test_write_command_matches_original(self, protocol, crc):
        """Verify write command matches original coordinator output."""
        command = protocol.build_write_command(0x0100, 300)

        assert command[0] == 0x01
        assert command[1] == 0x06
        assert command[2:4] == b"\x01\x00"
        assert command[4:6] == b"\x01\x2c"

        frame = command[:-2]
        crc_value = struct.unpack("<H", command[-2:])[0]
        assert crc_value == crc.calculate(frame)
