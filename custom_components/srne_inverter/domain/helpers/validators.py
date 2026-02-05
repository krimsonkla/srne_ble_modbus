"""Validation helper functions.

This module provides standardized validation functions for domain entities
and value objects. All validators raise ValidationError (subclass of ValueError)
for invalid inputs.
"""

from typing import Any, Union


class ValidationError(ValueError):
    """Domain validation error.

    Raised when validation fails. This is a subclass of ValueError
    for code simplicity.
    """


def validate_register_address(address: int, name: str = "address") -> int:
    """Validate register address is in valid range (0x0000-0xFFFF).

    Args:
        address: Register address to validate
        name: Parameter name for error message

    Returns:
        Validated address

    Raises:
        ValidationError: If address is invalid

    Examples:
        >>> validate_register_address(0x1234)
        4660
        >>> validate_register_address(0x10000)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: Invalid address: 0x10000 (must be 0x0000-0xFFFF)
    """
    if not isinstance(address, int):
        raise ValidationError(
            f"Invalid {name}: must be integer, got {type(address).__name__}"
        )

    if not 0 <= address <= 0xFFFF:
        raise ValidationError(
            f"Invalid {name}: 0x{address:04X} (must be 0x0000-0xFFFF)"
        )

    return address


def validate_register_value(value: int, name: str = "value") -> int:
    """Validate register value is in valid range (0-65535).

    Args:
        value: Register value to validate
        name: Parameter name for error message

    Returns:
        Validated value

    Raises:
        ValidationError: If value is invalid

    Examples:
        >>> validate_register_value(1000)
        1000
        >>> validate_register_value(70000)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: Invalid value: 70000 (must be 0-65535)
    """
    if not isinstance(value, int):
        raise ValidationError(
            f"Invalid {name}: must be integer, got {type(value).__name__}"
        )

    if not 0 <= value <= 0xFFFF:
        raise ValidationError(f"Invalid {name}: {value} (must be 0-65535)")

    return value


def validate_range(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float],
    name: str = "value",
) -> Union[int, float]:
    """Validate value is within specified range.

    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        name: Parameter name for error message

    Returns:
        Validated value

    Raises:
        ValidationError: If value out of range

    Examples:
        >>> validate_range(50, 0, 100)
        50
        >>> validate_range(150, 0, 100)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: value 150 out of range [0, 100]
    """
    if not min_value <= value <= max_value:
        raise ValidationError(f"{name} {value} out of range [{min_value}, {max_value}]")
    return value


def validate_not_none(value: Any, name: str = "value") -> Any:
    """Validate value is not None.

    Args:
        value: Value to validate
        name: Parameter name for error message

    Returns:
        Validated value

    Raises:
        ValidationError: If value is None

    Examples:
        >>> validate_not_none("test")
        'test'
        >>> validate_not_none(None)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: value cannot be None
    """
    if value is None:
        raise ValidationError(f"{name} cannot be None")
    return value


def validate_type(value: Any, expected_type: type, name: str = "value") -> Any:
    """Validate value is of expected type.

    Args:
        value: Value to validate
        expected_type: Expected type
        name: Parameter name for error message

    Returns:
        Validated value

    Raises:
        ValidationError: If value is wrong type

    Examples:
        >>> validate_type("hello", str)
        'hello'
        >>> validate_type(123, str)  # doctest: +SKIP
        Traceback (most recent call last):
        ...
        ValidationError: value must be str, got int
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{name} must be {expected_type.__name__}, got {type(value).__name__}"
        )
    return value
