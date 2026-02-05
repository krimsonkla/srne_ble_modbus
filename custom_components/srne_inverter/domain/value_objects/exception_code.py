"""Modbus exception codes.

Extracted from modbus_frame.py for one-class-per-file compliance.
"""

from enum import IntEnum


class ExceptionCode(IntEnum):
    """Modbus exception codes with human-readable descriptions.

    These codes are returned by Modbus devices to indicate various error conditions.
    Each code corresponds to a specific error condition as defined in the SRNE protocol.
    """

    ILLEGAL_FUNCTION = 0x01  # Illegal command - slave may not support this command
    ILLEGAL_DATA_ADDRESS = (
        0x02  # Illegal data address - register address out of legal range
    )
    ILLEGAL_DATA_VALUE = 0x03  # Illegal data value - register value out of range
    SLAVE_DEVICE_FAILURE = 0x04  # Operation failure - parameter write invalid or slave doesn't support command
    ACKNOWLEDGE = 0x05  # Password error - password incorrect for address validation
    SLAVE_DEVICE_BUSY = 0x06  # Data frame error - incorrect length or CRC mismatch
    PARAMETER_READ_ONLY = (
        0x07  # Parameter read-only - attempted to write read-only parameter
    )
    MEMORY_PARITY_ERROR = 0x08  # Parameters cannot be modified during operation
    PASSWORD_PROTECTION = 0x09  # Password protection - system locked, password required
    GATEWAY_PATH_UNAVAILABLE = (
        0x0A  # Length error - read/write register count exceeds 32
    )
    GATEWAY_TARGET_NO_RESPONSE = (
        0x0B  # Permission denied - no permission for this operation
    )
