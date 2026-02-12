"""Constants for SRNE Solar Charge Inverter integration.

This file contains only essential constants needed by the integration code.
Register definitions are now stored in YAML configuration files.
"""

from __future__ import annotations


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

# ============================================================================
# TIMING CONSTANTS
# ============================================================================
# All timing constants are in SECONDS unless explicitly noted.

# BLE Communication Timing
BLE_COMMAND_TIMEOUT = 1.5  # Timeout for BLE command operations
BLE_NOTIFY_SUBSCRIBE_TIMEOUT = 1.0  # Timeout for notification subscription
BLE_CONNECTION_TIMEOUT = 5.0  # Overall connection operation timeout
BLE_DISCONNECT_TIMEOUT = 0.5  # Timeout for disconnect operations
BLE_NOTIFY_RETRY_DELAY = 0.25  # Delay between notification subscription retries
BLE_DISCOVERY_TIMEOUT = 15.0  # Wait time for device discovery on HA restart

# Modbus Protocol Timing
MODBUS_RESPONSE_TIMEOUT = 1.5  # Wait for Modbus response from device
MODBUS_WRITE_TIMEOUT = 1  # Timeout for write operations

# Command Delays
COMMAND_DELAY_WRITE = 0.01  # Delay after write operations in preset manager
WRITE_VERIFY_DELAY_UI = 0.15  # Delay before read-verify in UI number entity

# Circuit Breaker Configuration
MAX_CONSECUTIVE_TIMEOUTS = 5  # Force reconnect after N consecutive timeouts

# ============================================================================
# ADAPTIVE TIMING CONSTANTS
# ============================================================================
# Configuration for timing measurement and adaptive learning

# Timing measurement configuration
TIMING_SAMPLE_SIZE = 100  # Number of samples to keep for statistics
TIMING_MIN_SAMPLES = 20  # Minimum samples before calculating statistics

# Learning algorithm configuration
TIMING_PERCENTILE = 0.95  # Use 95th percentile for timeout calculation
TIMING_SAFETY_MARGIN = 1.5  # Safety margin above measured P95
TIMING_MIN_TIMEOUT = 0.5  # Minimum timeout in seconds
TIMING_MAX_TIMEOUT = 5.0  # Maximum timeout in seconds

# ============================================================================
# MODBUS ERROR CODES
# ============================================================================

# Standard Modbus Exception Codes (as per Modbus specification)
MODBUS_ERROR_ILLEGAL_FUNCTION = 0x01
MODBUS_ERROR_ILLEGAL_DATA_ADDRESS = 0x02
MODBUS_ERROR_ILLEGAL_DATA_VALUE = 0x03
MODBUS_ERROR_SLAVE_DEVICE_FAILURE = 0x04
MODBUS_ERROR_ACKNOWLEDGE = 0x05
MODBUS_ERROR_SLAVE_DEVICE_BUSY = 0x06
MODBUS_ERROR_NEGATIVE_ACKNOWLEDGE = 0x07
MODBUS_ERROR_MEMORY_PARITY_ERROR = 0x08
MODBUS_ERROR_GATEWAY_PATH_UNAVAILABLE = 0x0A
MODBUS_ERROR_GATEWAY_TARGET_DEVICE_FAILED = 0x0B

# Standard Modbus error messages
MODBUS_ERROR_MESSAGES = {
    0x01: "Illegal Function - Function code not supported",
    0x02: "Illegal Data Address - Register address not allowable",
    0x03: "Illegal Data Value - Value not allowable",
    0x04: "Slave Device Failure - Unrecoverable error in slave",
    0x05: "Acknowledge - Accepted, long duration command",
    0x06: "Slave Device Busy - Processing long command",
    0x07: "Negative Acknowledge - Cannot perform program function",
    0x08: "Memory Parity Error - Parity error in memory",
    0x0A: "Gateway Path Unavailable - Gateway misconfigured/overloaded",
    0x0B: "Gateway Target Device Failed - No response from target device",
}

# SRNE-specific error codes (device vendor extensions)
SRNE_ERROR_CODES = {
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

# Alias for convenience
MODBUS_ERROR_CODES = SRNE_ERROR_CODES


def format_modbus_error(error_code: int, use_srne_codes: bool = False) -> str:
    """Format Modbus error code with human-readable message.

    Args:
        error_code: Modbus exception code (0x01-0x0B).
        use_srne_codes: If True, use SRNE-specific error messages instead of standard.

    Returns:
        Formatted error string with hex code and descriptive message.
    """
    error_dict = SRNE_ERROR_CODES if use_srne_codes else MODBUS_ERROR_MESSAGES
    message = error_dict.get(error_code, "Unknown error code")
    return f"0x{error_code:02X} ({message})"
