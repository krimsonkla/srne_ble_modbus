"""Constants for SRNE Solar Charge Inverter integration.

This file contains only essential constants needed by the integration code.
Register definitions are now stored in YAML configuration files.
"""

from __future__ import annotations

from typing import Any

# Domain and basic constants
DOMAIN = "srne_ble_modbus"
MANUFACTURER = "SRNE"
DEFAULT_NAME = "SRNE BLE Modbus"
DEFAULT_SLAVE_ID = 1
UNIVERSAL_SLAVE_ID = 255

# Serial port settings
BAUDRATE = 9600
BYTESIZE = 8
PARITY = "N"
STOPBITS = 1

# Modbus function codes
FUNC_READ_HOLDING = 0x03
FUNC_WRITE_SINGLE = 0x06
FUNC_WRITE_MULTIPLE = 0x10

# BLE GATT characteristics (from SRNE HF Series protocol)
BLE_SERVICE_UUID = "BCBBFD59-AB2E-7109-0CFD-F2D00295169F"
BLE_WRITE_UUID = "53300001-0023-4BD4-BBD5-A6920E4C5653"
BLE_NOTIFY_UUID = "53300005-0023-4BD4-BBD5-A6920E4C5653"

# Timing constants (in seconds) - Optimized for BLE Modbus performance
COMMAND_DELAY = 0.1  # Default delay - matches other BLE integrations (100ms)
COMMAND_DELAY_WRITE = 0.5  # Write operations need more processing time
BATCH_READ_DELAY = 0.1  # Batch reads - fast sequential reads (100ms)
WRITE_TIMEOUT = 2000  # Timeout for write operations
READ_TIMEOUT = 2000  # Timeout for read operations
POWER_STATE_CHANGE_DELAY = 5000  # Wait after power on/off command


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def calculate_crc16(data: bytes) -> int:
    """Calculate CRC16 for Modbus RTU.

    Args:
        data: Message bytes

    Returns:
        16-bit CRC value
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_modbus_read(slave_id: int, register: int, count: int = 1) -> bytes:
    """Build Modbus RTU read command (function code 0x03).

    Args:
        slave_id: Modbus slave address
        register: Starting register address
        count: Number of registers to read

    Returns:
        Complete Modbus RTU frame with CRC
    """
    if not 1 <= slave_id <= 254 and slave_id != UNIVERSAL_SLAVE_ID:
        raise ValueError(f"Invalid slave ID: {slave_id}")
    if not 1 <= count <= 32:
        raise ValueError(f"Invalid register count: {count}. Must be 1-32.")

    frame = bytes(
        [
            slave_id,
            FUNC_READ_HOLDING,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
    )

    crc = calculate_crc16(frame)
    frame += bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    return frame


def build_modbus_write(slave_id: int, register: int, value: int) -> bytes:
    """Build Modbus RTU write command (function code 0x06).

    Args:
        slave_id: Modbus slave address
        register: Register address to write
        value: 16-bit value to write

    Returns:
        Complete Modbus RTU frame with CRC
    """
    if not 1 <= slave_id <= 254 and slave_id != UNIVERSAL_SLAVE_ID:
        raise ValueError(f"Invalid slave ID: {slave_id}")
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"Invalid value: {value}. Must be 0-65535.")

    # Build frame: slave_id + function_code + register_hi + register_lo + value_hi + value_lo
    frame = bytes(
        [
            slave_id,
            FUNC_WRITE_SINGLE,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )

    crc = calculate_crc16(frame)
    frame += bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    return frame


def decode_modbus_response(data: bytes) -> dict[str, Any]:
    """Decode a Modbus RTU response frame.

    Args:
        data: Complete Modbus response frame including CRC.

    Returns:
        Dictionary with decoded response data:
        - slave_id: Slave address
        - function_code: Function code
        - byte_count: Number of data bytes (for read responses)
        - values: List of register values (for read responses)
        - register: Register address (for write responses)
        - value: Written value (for write responses)
        - error: Error code if response is an error

    Raises:
        ValueError: If CRC check fails or frame is invalid.
    """
    if len(data) < 5:
        raise ValueError("Response too short")

    # Verify CRC
    received_crc = (data[-1] << 8) | data[-2]
    calculated_crc = calculate_crc16(data[:-2])
    if received_crc != calculated_crc:
        raise ValueError(
            f"CRC mismatch: received={received_crc:04X}, calculated={calculated_crc:04X}"
        )

    result = {
        "slave_id": data[0],
        "function_code": data[1],
    }

    # Check for error response
    if data[1] & 0x80:
        result["error"] = data[2]
        return result

    # Decode based on function code
    if data[1] == FUNC_READ_HOLDING:  # Read response
        byte_count = data[2]
        result["byte_count"] = byte_count
        result["values"] = []
        for i in range(0, byte_count, 2):
            value = (data[3 + i] << 8) | data[4 + i]
            result["values"].append(value)

    elif data[1] == FUNC_WRITE_SINGLE:  # Write single response
        result["register"] = (data[2] << 8) | data[3]
        result["value"] = (data[4] << 8) | data[5]

    elif data[1] == FUNC_WRITE_MULTIPLE:  # Write multiple response
        result["register"] = (data[2] << 8) | data[3]
        result["count"] = (data[4] << 8) | data[5]

    return result


def apply_scaling(value: int, register_info: dict[str, Any]) -> float:
    """Apply scaling factor to a register value.

    Args:
        value: Raw register value.
        register_info: Register information dictionary containing 'scaling' and 'signed' keys.

    Returns:
        Scaled value as float.
    """
    # Handle signed values
    if register_info.get("signed", False):
        if value & 0x8000:  # Negative value
            value = value - 0x10000

    # Apply scaling
    scaling = register_info.get("scaling", 1)
    return value * scaling


def encode_time(hour: int, minute: int) -> int:
    """Encode time as hour*256 + minute for timed charging/discharging registers.

    Args:
        hour: Hour (0-23).
        minute: Minute (0-59).

    Returns:
        Encoded time value.
    """
    if not 0 <= hour <= 23:
        raise ValueError(f"Invalid hour: {hour}. Must be 0-23.")
    if not 0 <= minute <= 59:
        raise ValueError(f"Invalid minute: {minute}. Must be 0-59.")

    return hour * 256 + minute


def decode_time(value: int) -> tuple[int, int]:
    """Decode time from register value to (hour, minute).

    Args:
        value: Encoded time value from register.

    Returns:
        Tuple of (hour, minute).
    """
    hour = value // 256
    minute = value % 256
    return hour, minute


# ============================================================================
# MODBUS ERROR CODES
# ============================================================================

# Error codes for Modbus exceptions
MODBUS_ERROR_CODES = {
    0x01: "Illegal command - slave may not support this command",
    0x02: "Illegal data address - register address out of legal range",
    0x03: "Illegal data value - register value out of range",
    0x04: "Operation failure - parameter write invalid or slave doesn't support command",
    0x05: "Password error - password incorrect for address validation",
    0x06: "Data frame error - incorrect length or CRC mismatch",
    0x07: "Parameter read-only - attempted to write read-only parameter",
    0x08: "Parameters cannot be modified during operation",
    0x09: "Password protection - system locked, password required",
    0x0A: "Length error - read/write register count exceeds 32",
    0x0B: "Permission denied - no permission for this operation",
}
