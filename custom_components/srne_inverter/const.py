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
# BLE Modbus communication requires careful timing for reliable operation.
#
# PHASE 1: CONSERVATIVE DEFAULTS (2026-02-11)
# Setting conservative timeouts to accommodate slow hardware (Raspberry Pi 3B+).
# These values prioritize reliability over performance:
# - Longer timeouts reduce false positives from slow BLE adapters
# - Higher circuit breaker threshold allows more retry attempts
# - Extended discovery timeout handles slower BLE scanning
#
# Previous optimized values (for reference):
# - MODBUS_RESPONSE_TIMEOUT: 0.7s (now 1.5s)
# - BLE_COMMAND_TIMEOUT: 0.5s (now 1.0s)
# - BLE_CONNECTION_TIMEOUT: 3.0s (now 5.0s)
# - MAX_CONSECUTIVE_TIMEOUTS: 3 (now 5)
# - discovery_timeout: 7.0s (now 15.0s in ble_transport.py)
#
# Next phases will add adaptive logic while maintaining these safe defaults.

# BLE Communication Timing (all in seconds)
BLE_COMMAND_TIMEOUT = 1.0  # Timeout for BLE command operations (was 0.5s)
BLE_WRITE_PROCESSING_DELAY = (
    0.03  # Device processing time after write (optimized: was 0.05s)
)
BLE_READ_DELAY = 0.05  # Small delay before read operation
BLE_NOTIFY_SUBSCRIBE_TIMEOUT = 1.0  # Timeout for notification subscription
BLE_CONNECTION_TIMEOUT = 5.0  # Overall connection operation timeout (was 3.0s)
BLE_DISCONNECT_TIMEOUT = 0.5  # Timeout for disconnect operations
BLE_NOTIFY_RETRY_DELAY = 0.25  # Delay between notification subscription retries

# Modbus Protocol Timing (all in seconds)
MODBUS_RESPONSE_TIMEOUT = 1.5  # Wait for Modbus response from device (was 0.7s)
MODBUS_WRITE_TIMEOUT = 1  # Timeout for write operations (faster than read)
MODBUS_RETRY_DELAY = 0.25  # Delay between retry attempts

# Command Delays (all in seconds)
COMMAND_DELAY = 0.01  # Standard delay between commands (increased for stability)
COMMAND_DELAY_WRITE = 0.01  # Delay after write operations (increased for stability)
BATCH_READ_DELAY = 0.005  # Delay between batch read operations (optimized: was 0.01s)
POWER_STATE_CHANGE_DELAY = (
    5.0  # Delay after power state changes (converted from milliseconds)
)
WRITE_VERIFY_DELAY = (
    0.05  # Delay before read-verify after write (inverter processing time)
)
WRITE_VERIFY_DELAY_UI = (
    0.15  # Delay before read-verify in UI number entity (with safety margin)
)

# BLE Discovery
BLE_DISCOVERY_TIMEOUT = 15.0  # Wait time for device discovery on HA restart (was 7.0s hardcoded)

# Circuit Breaker Configuration
MAX_CONSECUTIVE_TIMEOUTS = 5  # Force reconnect after N consecutive timeouts (was 3)

# ============================================================================
# ADAPTIVE TIMING CONSTANTS (PHASE 2)
# ============================================================================
# Configuration for timing measurement and adaptation infrastructure

# Timing measurement configuration
TIMING_SAMPLE_SIZE = 100  # Number of samples to keep for statistics (rolling window)
TIMING_MIN_SAMPLES = 20  # Minimum samples before calculating statistics

# Learning algorithm configuration (Phase 3)
TIMING_PERCENTILE = 0.95  # Use 95th percentile for timeout calculation
TIMING_SAFETY_MARGIN = 1.5  # 50% safety margin above measured P95
TIMING_MIN_TIMEOUT = 0.5  # Minimum timeout in seconds (prevents too-aggressive timeouts)
TIMING_MAX_TIMEOUT = 5.0  # Maximum timeout in seconds (prevents excessive waits)

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
