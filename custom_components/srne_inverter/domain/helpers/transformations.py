"""Value transformation helper functions.

This module provides utilities for transforming register values including
scaling, precision rounding, and data type conversions (signed/unsigned).
"""

from typing import Union


def apply_scaling(value: Union[int, float], scale: float = 1.0) -> float:
    """Apply scaling factor to value.

    Args:
        value: Raw value
        scale: Scaling factor (default: 1.0)

    Returns:
        Scaled value as float

    Examples:
        >>> apply_scaling(100, 0.1)
        10.0
        >>> apply_scaling(50, 2.0)
        100.0
        >>> apply_scaling(42)
        42.0
    """
    return float(value) * scale


def apply_precision(value: float, precision: int = 2) -> float:
    """Round value to specified precision.

    Args:
        value: Value to round
        precision: Number of decimal places (default: 2)

    Returns:
        Rounded value

    Examples:
        >>> apply_precision(12.3456)
        12.35
        >>> apply_precision(12.3456, 1)
        12.3
        >>> apply_precision(12.3456, 0)
        12.0
    """
    return round(value, precision)


def convert_to_signed_int16(value: int) -> int:
    """Convert unsigned 16-bit to signed 16-bit.

    Uses two's complement representation. Values >= 0x8000 are negative.

    Args:
        value: Unsigned 16-bit integer (0-65535)

    Returns:
        Signed 16-bit integer (-32768 to 32767)

    Examples:
        >>> convert_to_signed_int16(0x0000)
        0
        >>> convert_to_signed_int16(0x7FFF)
        32767
        >>> convert_to_signed_int16(0x8000)
        -32768
        >>> convert_to_signed_int16(0xFFFF)
        -1
    """
    if value >= 0x8000:
        return value - 0x10000
    return value


def convert_to_unsigned_int16(value: int) -> int:
    """Convert signed 16-bit to unsigned 16-bit.

    Uses two's complement representation. Negative values are converted
    to unsigned representation.

    Args:
        value: Signed 16-bit integer (-32768 to 32767)

    Returns:
        Unsigned 16-bit integer (0-65535)

    Examples:
        >>> convert_to_unsigned_int16(0)
        0
        >>> convert_to_unsigned_int16(32767)
        32767
        >>> convert_to_unsigned_int16(-32768)
        32768
        >>> convert_to_unsigned_int16(-1)
        65535
    """
    if value < 0:
        return value + 0x10000
    return value & 0xFFFF


def process_register_value(
    raw_value: int,
    data_type: str = "uint16",
    scale: float = 1.0,
    offset: int = 0,
    precision: int = 2,
) -> Union[int, float]:
    """Process raw register value with all transformations.

    Applies transformations in this order:
    1. Data type conversion (signed/unsigned)
    2. Offset addition
    3. Scaling
    4. Precision rounding (if result is float)

    Args:
        raw_value: Raw 16-bit register value (0-65535)
        data_type: Data type ("uint16" or "int16")
        scale: Scaling factor (default: 1.0)
        offset: Offset to apply before scaling (default: 0)
        precision: Decimal places for rounding (default: 2)

    Returns:
        Processed value (int if scale=1.0 and offset=0, else float)

    Examples:
        >>> process_register_value(1000)
        1000.0
        >>> process_register_value(1000, scale=0.1)
        100.0
        >>> process_register_value(0x8000, data_type="int16")
        -32768.0
        >>> process_register_value(100, offset=10, scale=2.5, precision=1)
        275.0
    """
    # Convert data type
    if data_type == "int16":
        value = convert_to_signed_int16(raw_value)
    else:
        value = raw_value

    # Apply offset and scale
    value = (value + offset) * scale

    # Apply precision if float
    if isinstance(value, float) and precision is not None:
        value = apply_precision(value, precision)

    return value


def encode_register_value(
    display_value: Union[int, float],
    scale: float = 1.0,
    offset: int = 0,
    data_type: str = "uint16",
) -> int:
    """Encode display value back to register value.

    Inverse of process_register_value. Removes scaling and offset,
    then converts to appropriate data type.

    Args:
        display_value: Display value to encode
        scale: Scaling factor used for decoding (default: 1.0)
        offset: Offset used for decoding (default: 0)
        data_type: Target data type ("uint16" or "int16")

    Returns:
        Raw register value (0-65535)

    Examples:
        >>> encode_register_value(100.0, scale=0.1)
        1000
        >>> encode_register_value(-32768.0, data_type="int16")
        32768
        >>> encode_register_value(275.0, offset=10, scale=2.5)
        100
    """
    # Remove scale and offset
    value = int(round(display_value / scale)) - offset

    # Convert to unsigned if needed
    if data_type == "int16" and value < 0:
        value = convert_to_unsigned_int16(value)

    return value & 0xFFFF
