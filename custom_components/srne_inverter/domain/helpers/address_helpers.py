"""Address format helper functions.

This module provides utilities for parsing, formatting, and validating
register addresses in various formats (hex strings, decimal, integers).
"""

from typing import Union


def parse_address(address: Union[str, int]) -> int:
    """Parse address from string or int to int.

    Supports hex strings (0x1234), decimal strings, and integers.

    Args:
        address: Address in any supported format

    Returns:
        Integer address

    Raises:
        ValueError: If address format is invalid

    Examples:
        >>> parse_address("0x1234")
        4660
        >>> parse_address("1234")
        4660
        >>> parse_address(4660)
        4660
    """
    if isinstance(address, int):
        return address

    if isinstance(address, str):
        address = address.strip()
        try:
            if address.startswith("0x") or address.startswith("0X"):
                return int(address, 16)
            else:
                # Try hex first, then decimal
                try:
                    return int(address, 16)
                except ValueError:
                    return int(address, 10)
        except ValueError as err:
            raise ValueError(f"Invalid address format: '{address}'") from err

    raise ValueError(f"Address must be str or int, got {type(address)}")


def format_address(address: int, prefix: bool = True) -> str:
    """Format address as hex string.

    Args:
        address: Integer address
        prefix: Whether to include '0x' prefix

    Returns:
        Formatted hex string (e.g., "0x1234" or "1234")

    Examples:
        >>> format_address(4660)
        '0x1234'
        >>> format_address(4660, prefix=False)
        '1234'
    """
    if prefix:
        return f"0x{address:04X}"
    else:
        return f"{address:04X}"


def address_in_range(
    address: int, start: int, end: int, inclusive: bool = True
) -> bool:
    """Check if address is in specified range.

    Args:
        address: Address to check
        start: Range start
        end: Range end
        inclusive: Whether end is inclusive (default: True)

    Returns:
        True if address in range

    Examples:
        >>> address_in_range(0x1234, 0x1000, 0x2000)
        True
        >>> address_in_range(0x2000, 0x1000, 0x2000, inclusive=False)
        False
    """
    if inclusive:
        return start <= address <= end
    else:
        return start <= address < end


def calculate_register_count(start: int, end: int) -> int:
    """Calculate number of registers in range.

    Args:
        start: Starting address
        end: Ending address (inclusive)

    Returns:
        Number of registers

    Examples:
        >>> calculate_register_count(0x1000, 0x1009)
        10
    """
    return end - start + 1
