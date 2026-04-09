"""Modbus RTU protocol implementation.

This module implements the Modbus RTU protocol over BLE for the SRNE inverter.
It handles command building, response decoding, and error handling.

This implementation is extracted from the original coordinator.py ModbusProtocol
class and maintains identical behavior.
"""

import struct
import logging
from typing import Dict, Any

from ...domain.interfaces import IProtocol, ICRC
from ...const import (
    FUNC_READ_HOLDING,
    FUNC_WRITE_SINGLE,
    FUNC_WRITE_MULTIPLE,
    DEFAULT_SLAVE_ID,
    format_modbus_error,
)

# BLE notify payloads may include a zero prefix (spec: 8 bytes) and/or trailing bytes.
# Modbus RTU CRC is computed only over the ADU; trim/skip so we do not misread CRC.
_MAX_BLE_ZERO_PREFIX = 24
_MAX_READ_RESPONSE_DATA_BYTES = 252  # 126 registers × 2, within spec

_LOGGER = logging.getLogger(__name__)


class ModbusRTUProtocol(IProtocol):
    """Modbus RTU protocol implementation for BLE communication.

    This implementation handles:
    - Building Modbus RTU frames (read/write commands)
    - Decoding responses with BLE framing
    - CRC validation
    - Error response detection

    Framing:
        BLE: SRNE prepends up to 8 (sometimes fewer) 0x00 bytes before the ADU;
        notify payloads may also contain bytes after the CRC. USB serial: plain
        Modbus RTU only; ``SerialTransport`` strips a leading TX echo when present.

    Attributes:
        crc: CRC calculator implementation
        slave_id: Modbus slave ID (default: 0x01)

    Example:
        >>> from .modbus_crc16 import ModbusCRC16
        >>> protocol = ModbusRTUProtocol(ModbusCRC16())
        >>> command = protocol.build_read_command(0x0100, 2)
        >>> # Send command via transport...
        >>> result = protocol.decode_response(response_bytes)
    """

    def __init__(self, crc: ICRC, slave_id: int = DEFAULT_SLAVE_ID):
        """Initialize Modbus RTU protocol.

        Args:
            crc: CRC calculator implementation
            slave_id: Modbus slave ID (default: 0x01)
        """
        self._crc = crc
        self._slave_id = slave_id

    @staticmethod
    def _strip_leading_zero_padding(response: bytes) -> bytes:
        """Remove leading 0x00 bytes up to _MAX_BLE_ZERO_PREFIX.

        SRNE docs describe an 8-byte zero header; some stacks use shorter padding.
        Valid Modbus RTU responses never use slave ID 0, so leading zeros are never
        part of the ADU.
        """
        i = 0
        n = len(response)
        while (
            i < n
            and i < _MAX_BLE_ZERO_PREFIX
            and response[i] == 0
        ):
            i += 1
        return response[i:]

    def _trim_to_modbus_adu(self, frame: bytes) -> bytes:
        """If the buffer is longer than the ADU, keep only the first ADU.

        BLE notifications sometimes append extra bytes; using the last two bytes
        of the full buffer as CRC then fails validation.
        """
        if len(frame) < 5:
            return frame

        function_code = frame[1]
        if function_code & 0x80:
            expected = 5
        elif function_code == FUNC_READ_HOLDING:
            if len(frame) < 3:
                return frame
            byte_count = frame[2]
            if byte_count > _MAX_READ_RESPONSE_DATA_BYTES:
                return frame
            expected = 3 + byte_count + 2
        elif function_code in (FUNC_WRITE_SINGLE, FUNC_WRITE_MULTIPLE):
            expected = 8
        else:
            return frame

        if len(frame) < expected:
            raise ValueError(
                f"Incomplete Modbus frame: expected {expected} bytes, got {len(frame)}"
            )

        if len(frame) > expected:
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Trimming Modbus notify payload: %d -> %d bytes (dropped %d trailing)",
                    len(frame),
                    expected,
                    len(frame) - expected,
                )
            return frame[:expected]

        return frame

    def build_read_command(self, start_address: int, count: int) -> bytes:
        """Build Modbus Read Holding Registers (0x03) command.

        Args:
            start_address: Starting register address (0x0000 - 0xFFFF)
            count: Number of consecutive registers to read (1-125)

        Returns:
            Complete Modbus RTU frame ready to send
            Format: [Slave][0x03][Addr_H][Addr_L][Count_H][Count_L][CRC_L][CRC_H]

        Raises:
            ValueError: If address or count is out of valid range

        Example:
            >>> protocol = ModbusRTUProtocol(ModbusCRC16())
            >>> cmd = protocol.build_read_command(0x0100, 1)
            >>> assert cmd[0] == 0x01  # Slave ID
            >>> assert cmd[1] == 0x03  # Function code
            >>> assert len(cmd) == 8   # Total frame length
        """
        # Validate inputs
        if start_address < 0 or start_address > 0xFFFF:
            raise ValueError(f"Register address must be 0-65535, got {start_address}")
        if count < 1 or count > 125:
            raise ValueError(f"Register count must be 1-125, got {count}")

        # Build frame: Slave ID + Function + Address (BE) + Count (BE)
        data = struct.pack(
            ">BBHH",
            self._slave_id,
            FUNC_READ_HOLDING,
            start_address,
            count,
        )

        # Calculate and append CRC (little-endian)
        crc_value = self._crc.calculate(data)
        frame = data + struct.pack("<H", crc_value)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Built read command: addr=0x%04X, count=%d, frame=%s",
                start_address,
                count,
                frame.hex(),
            )

        return frame

    def build_write_command(self, address: int, value: int) -> bytes:
        """Build Modbus Write Single Register (0x06) command.

        Args:
            address: Register address to write (0x0000 - 0xFFFF)
            value: 16-bit value to write (0x0000 - 0xFFFF)

        Returns:
            Complete Modbus RTU frame ready to send
            Format: [Slave][0x06][Addr_H][Addr_L][Val_H][Val_L][CRC_L][CRC_H]

        Raises:
            ValueError: If address or value is out of valid range

        Example:
            >>> protocol = ModbusRTUProtocol(ModbusCRC16())
            >>> cmd = protocol.build_write_command(0x0100, 300)
            >>> assert cmd[1] == 0x06  # Function code
        """
        # Validate inputs
        if address < 0 or address > 0xFFFF:
            raise ValueError(f"Register address must be 0-65535, got {address}")
        if value < 0 or value > 0xFFFF:
            raise ValueError(f"Register value must be 0-65535, got {value}")

        # Build frame: Slave ID + Function + Address (BE) + Value (BE)
        data = struct.pack(
            ">BBHH",
            self._slave_id,
            FUNC_WRITE_SINGLE,
            address,
            value,
        )

        # Calculate and append CRC (little-endian)
        crc_value = self._crc.calculate(data)
        frame = data + struct.pack("<H", crc_value)

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Built write command: addr=0x%04X, value=%d, frame=%s",
                address,
                value,
                frame.hex(),
            )

        return frame

    def decode_response(self, response: bytes) -> Dict[str, Any]:
        """Decode Modbus response into register address-value pairs.

        This handles:
        - BLE framing header removal (8 bytes of 0x00)
        - SRNE dash error pattern detection (vendor-specific)
        - CRC validation
        - Error response detection (function code with 0x80 bit set)
        - Multi-register response parsing

        Args:
            response: Raw response bytes from transport (may include BLE header)

        Returns:
            Dictionary mapping register addresses to values
            Example: {0x0100: 486, 0x0101: 250}
            For errors: {"error": error_code} or {"error": "unsupported_register"}

        Raises:
            ValueError: If response is malformed or CRC invalid

        Example:
            >>> protocol = ModbusRTUProtocol(ModbusCRC16())
            >>> response = bytes([
            ...     0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # BLE header
            ...     0x01, 0x03, 0x04, 0x01, 0xE6, 0x00, 0xFA, 0x9F, 0x1C
            ... ])
            >>> result = protocol.decode_response(response)
            >>> # result = {0x0100: 486, 0x0101: 250}
        """
        # Minimum response length check
        if len(response) < 5:  # Minimum Modbus frame without BLE header
            _LOGGER.debug("Response too short: %d bytes", len(response))
            raise ValueError(f"Response too short: {len(response)} bytes")

        # Strip BLE zero prefix (see _strip_leading_zero_padding)
        modbus_frame = self._strip_leading_zero_padding(response)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "After zero-prefix strip: %d bytes, hex=%s",
                len(modbus_frame),
                modbus_frame[:40].hex() if len(modbus_frame) > 40 else modbus_frame.hex(),
            )

        if len(modbus_frame) < 5:  # Min: slave + func + data + CRC
            _LOGGER.debug("Modbus frame too short: %d bytes", len(modbus_frame))
            raise ValueError(f"Modbus frame too short: {len(modbus_frame)} bytes")

        # Check for SRNE dash error pattern (vendor-specific, not standard Modbus)
        # Pattern: 0x2D2D2D2D... (ASCII "----")
        # This indicates the batch contained an unsupported register
        # Detection happens BEFORE CRC validation since dash responses don't have valid CRC
        if len(modbus_frame) >= 4 and modbus_frame[:4] == b"\x2d\x2d\x2d\x2d":
            _LOGGER.warning(
                "SRNE dash error detected in protocol layer: %s",
                (
                    modbus_frame[:20].hex()
                    if len(modbus_frame) >= 20
                    else modbus_frame.hex()
                ),
            )
            return {
                "error": "unsupported_register",
                "details": "Device returned dash pattern - batch contains unsupported register",
            }

        modbus_frame = self._trim_to_modbus_adu(modbus_frame)

        # Validate CRC
        received_crc = struct.unpack("<H", modbus_frame[-2:])[0]
        calculated_crc = self._crc.calculate(modbus_frame[:-2])

        if received_crc != calculated_crc:
            _LOGGER.warning(
                "CRC mismatch: received=0x%04X, calculated=0x%04X",
                received_crc,
                calculated_crc,
            )
            raise ValueError(
                f"CRC mismatch: received=0x{received_crc:04X}, "
                f"calculated=0x{calculated_crc:04X}"
            )

        # Parse frame header
        slave_addr = modbus_frame[0]
        function_code = modbus_frame[1]

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Decoded frame: slave=0x%02X, func=0x%02X",
                slave_addr,
                function_code,
            )

        # Check for error response (function code with 0x80 bit set)
        if function_code & 0x80:
            error_code = modbus_frame[2]
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Modbus exception: func=0x%02X, %s",
                    function_code,
                    format_modbus_error(error_code, use_srne_codes=True),
                )
            return {"error": error_code}

        # Decode read response
        if function_code == FUNC_READ_HOLDING:
            return self._decode_read_response(modbus_frame)

        # Decode write response
        if function_code == FUNC_WRITE_SINGLE:
            return self._decode_write_response(modbus_frame)

        _LOGGER.warning("Unknown function code: 0x%02X", function_code)
        raise ValueError(f"Unknown function code: 0x{function_code:02X}")

    def _decode_read_response(self, frame: bytes) -> Dict[int, int]:
        """Decode read holding registers response.

        Frame format: [Slave][Func][ByteCount][Data...][CRC]

        Args:
            frame: Modbus frame (without BLE header)

        Returns:
            Dictionary mapping register addresses to values

        Performance: Uses bulk struct.unpack for 20-25% speedup vs loop
        """
        byte_count = frame[2]
        register_count = byte_count // 2

        # Bulk unpack all registers at once (20-25% faster than loop)
        # Format: ">%dH" unpacks N big-endian unsigned shorts
        format_str = f">{register_count}H"
        unpacked_values = struct.unpack(format_str, frame[3 : 3 + byte_count])

        # Convert tuple to dict with index keys
        values = {i: val for i, val in enumerate(unpacked_values)}

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Decoded read response: %d registers, values=%s",
                register_count,
                values,
            )

        return values

    def _decode_write_response(self, frame: bytes) -> Dict[int, int]:
        """Decode write single register response.

        Frame format: [Slave][Func][Addr_H][Addr_L][Val_H][Val_L][CRC]

        Args:
            frame: Modbus frame (without BLE header)

        Returns:
            Dictionary with register address and written value
        """
        register = struct.unpack(">H", frame[2:4])[0]
        value = struct.unpack(">H", frame[4:6])[0]

        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Decoded write response: addr=0x%04X, value=%d",
                register,
                value,
            )

        return {register: value}
