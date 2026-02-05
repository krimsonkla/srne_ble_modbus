"""Modbus function codes.

Extracted from modbus_frame.py for one-class-per-file compliance.
"""

from enum import IntEnum


class FunctionCode(IntEnum):
    """Modbus function codes."""

    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_REGISTERS = 0x10

    # Error responses have 0x80 bit set
    ERROR_READ_HOLDING = 0x83
    ERROR_READ_INPUT = 0x84
    ERROR_WRITE_SINGLE = 0x86
    ERROR_WRITE_MULTIPLE = 0x90
