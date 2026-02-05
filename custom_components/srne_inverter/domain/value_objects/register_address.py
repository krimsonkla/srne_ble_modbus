"""RegisterAddress value object.

Represents a Modbus register address (0x0000 - 0xFFFF).
Encapsulates validation and conversion logic.
"""

from dataclasses import dataclass
from typing import Final

from ..helpers.address_helpers import format_address, parse_address


@dataclass(frozen=True)
class RegisterAddress:
    """Immutable Modbus register address.

    Modbus register addresses are 16-bit unsigned integers (0-65535).
    This value object ensures addresses are always valid.

    Attributes:
        value: Register address as integer (0x0000 - 0xFFFF)

    Example:
        >>> addr = RegisterAddress(0x0100)
        >>> assert addr.value == 256
        >>> assert addr.to_hex() == "0x0100"
        >>> bytes_repr = addr.to_bytes()
        >>> assert bytes_repr == b'\\x01\\x00'

    Raises:
        ValueError: If address is outside valid range
    """

    value: int

    # Constants
    MIN_ADDRESS: Final[int] = 0x0000
    MAX_ADDRESS: Final[int] = 0xFFFF

    def __post_init__(self) -> None:
        """Validate address is in valid range.

        Raises:
            ValueError: If address < 0 or > 0xFFFF
        """
        if not isinstance(self.value, int):
            raise TypeError(f"Address must be int, got {type(self.value).__name__}")

        if self.value < self.MIN_ADDRESS or self.value > self.MAX_ADDRESS:
            raise ValueError(
                f"Register address must be between {self.MIN_ADDRESS:#06x} "
                f"and {self.MAX_ADDRESS:#06x}, got {self.value:#06x}"
            )

    def to_bytes(self) -> bytes:
        """Convert address to big-endian byte representation.

        Modbus uses big-endian (network byte order) for addresses.

        Returns:
            2-byte representation in big-endian format

        Example:
            >>> RegisterAddress(0x0100).to_bytes()
            b'\\x01\\x00'
            >>> RegisterAddress(0x1234).to_bytes()
            b'\\x12\\x34'
        """
        return self.value.to_bytes(2, byteorder="big")

    def to_hex(self) -> str:
        """Format address as hex string.

        Returns:
            Address formatted as "0xXXXX" (4 hex digits)

        Example:
            >>> RegisterAddress(256).to_hex()
            '0x0100'
            >>> RegisterAddress(0xFFFF).to_hex()
            '0xFFFF'
        """
        return format_address(self.value)

    def __str__(self) -> str:
        """String representation for logging.

        Returns:
            Human-readable address string

        Example:
            >>> str(RegisterAddress(0x0100))
            'RegisterAddress(0x0100)'
        """
        return f"RegisterAddress({self.to_hex()})"

    def __repr__(self) -> str:
        """Developer representation.

        Returns:
            Representation string for debugging
        """
        return f"RegisterAddress(value={self.value:#06x})"

    def __int__(self) -> int:
        """Allow casting to int.

        Returns:
            Address as integer

        Example:
            >>> int(RegisterAddress(0x0100))
            256
        """
        return self.value

    def __add__(self, other: int) -> "RegisterAddress":
        """Add offset to address.

        Args:
            other: Integer offset to add

        Returns:
            New RegisterAddress with offset applied

        Raises:
            ValueError: If result is outside valid range

        Example:
            >>> addr = RegisterAddress(0x0100)
            >>> next_addr = addr + 1
            >>> assert next_addr.value == 0x0101
        """
        return RegisterAddress(self.value + other)

    def __sub__(self, other: int) -> "RegisterAddress":
        """Subtract offset from address.

        Args:
            other: Integer offset to subtract

        Returns:
            New RegisterAddress with offset applied

        Raises:
            ValueError: If result is outside valid range

        Example:
            >>> addr = RegisterAddress(0x0100)
            >>> prev_addr = addr - 1
            >>> assert prev_addr.value == 0x00FF
        """
        return RegisterAddress(self.value - other)

    def __lt__(self, other: "RegisterAddress") -> bool:
        """Less than comparison.

        Args:
            other: RegisterAddress to compare with

        Returns:
            True if this address is less than other

        Example:
            >>> RegisterAddress(0x0100) < RegisterAddress(0x0200)
            True
        """
        if not isinstance(other, RegisterAddress):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "RegisterAddress") -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, RegisterAddress):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "RegisterAddress") -> bool:
        """Greater than comparison.

        Args:
            other: RegisterAddress to compare with

        Returns:
            True if this address is greater than other

        Example:
            >>> RegisterAddress(0x0200) > RegisterAddress(0x0100)
            True
        """
        if not isinstance(other, RegisterAddress):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "RegisterAddress") -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, RegisterAddress):
            return NotImplemented
        return self.value >= other.value

    @classmethod
    def from_bytes(cls, data: bytes) -> "RegisterAddress":
        """Create RegisterAddress from big-endian bytes.

        Args:
            data: 2-byte big-endian representation

        Returns:
            RegisterAddress instance

        Raises:
            ValueError: If data is not exactly 2 bytes

        Example:
            >>> addr = RegisterAddress.from_bytes(b'\\x01\\x00')
            >>> assert addr.value == 0x0100
        """
        if len(data) != 2:
            raise ValueError(f"Expected 2 bytes, got {len(data)}")

        value = int.from_bytes(data, byteorder="big")
        return cls(value)

    @classmethod
    def from_hex(cls, hex_str: str) -> "RegisterAddress":
        """Create RegisterAddress from hex string.

        Args:
            hex_str: Hex string like "0x0100" or "0100"

        Returns:
            RegisterAddress instance

        Example:
            >>> addr = RegisterAddress.from_hex("0x0100")
            >>> assert addr.value == 0x0100
            >>> addr2 = RegisterAddress.from_hex("0100")
            >>> assert addr2.value == 0x0100
        """
        value = parse_address(hex_str)
        return cls(value)
