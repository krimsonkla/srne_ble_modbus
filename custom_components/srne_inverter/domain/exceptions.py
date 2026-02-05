"""Custom exceptions for the SRNE inverter integration.

This module defines domain-specific exceptions that represent expected
error conditions in the SRNE inverter protocol and communication.
"""


class DeviceRejectedCommandError(Exception):
    """Device rejected command (expected protocol error).

    Raised when the device legitimately rejects a command, such as when
    a batch contains an unsupported register. This is not an error in the
    code, but a limitation of the device firmware.

    The device indicates this condition by returning a "dash error pattern"
    (0x2D2D2D2D...) when the BLE_WRITE_UUID characteristic is read after
    writing a command.

    This exception should be logged without a stack trace since it represents
    an expected protocol condition, not a bug in the integration code.

    Example:
        >>> raise DeviceRejectedCommandError(
        ...     "Batch contains unsupported register (dash error pattern)"
        ... )
    """
