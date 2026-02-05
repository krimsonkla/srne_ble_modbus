"""RegisterValue value object.

Represents a value read from a Modbus register, including metadata.
"""

from dataclasses import dataclass
from enum import Enum

from ..helpers.transformations import convert_to_signed_int16


class DataType(Enum):
    """Register data types."""

    UINT16 = "uint16"  # Unsigned 16-bit integer (0-65535)
    INT16 = "int16"  # Signed 16-bit integer (-32768 to 32767)
    UINT32 = "uint32"  # Unsigned 32-bit (two registers)
    INT32 = "int32"  # Signed 32-bit (two registers)
    FLOAT32 = "float32"  # IEEE 754 float (two registers)


@dataclass(frozen=True)
class RegisterValue:
    """Immutable register value with metadata.

    Represents a raw value read from a register, along with metadata
    needed to interpret it correctly.

    Attributes:
        address: Register address this value came from
        raw_value: Raw integer value read from device (0-65535)
        data_type: How to interpret the raw value
        scale: Scaling factor to apply (default: 1.0)
        offset: Offset to apply after scaling (default: 0)

    Example:
        >>> # Battery voltage: raw 486 → 48.6V (scale 0.1)
        >>> value = RegisterValue(
        ...     address=0x0100,
        ...     raw_value=486,
        ...     data_type=DataType.UINT16,
        ...     scale=0.1
        ... )
        >>> assert value.decoded_value == 48.6

        >>> # Temperature: raw 65 → 25°C (offset -40)
        >>> temp = RegisterValue(
        ...     address=0x0200,
        ...     raw_value=65,
        ...     data_type=DataType.INT16,
        ...     offset=-40
        ... )
        >>> assert temp.decoded_value == 25
    """

    address: int
    raw_value: int
    data_type: DataType = DataType.UINT16
    scale: float = 1.0
    offset: int = 0

    def __post_init__(self) -> None:
        """Validate register value.

        Raises:
            ValueError: If raw_value is outside valid range for data type
        """
        if not isinstance(self.address, int):
            raise TypeError(f"Address must be int, got {type(self.address).__name__}")

        if not isinstance(self.raw_value, int):
            raise TypeError(
                f"Raw value must be int, got {type(self.raw_value).__name__}"
            )

        # Validate raw_value range based on data type
        if self.data_type in (DataType.UINT16, DataType.INT16):
            if self.raw_value < 0 or self.raw_value > 0xFFFF:
                raise ValueError(
                    f"Raw value for {self.data_type.value} must be 0-65535, "
                    f"got {self.raw_value}"
                )
        elif self.data_type in (DataType.UINT32, DataType.INT32):
            if self.raw_value < 0 or self.raw_value > 0xFFFFFFFF:
                raise ValueError(
                    f"Raw value for {self.data_type.value} must be 0-4294967295, "
                    f"got {self.raw_value}"
                )

    @property
    def decoded_value(self) -> float:
        """Decode raw value to actual value.

        Applies data type conversion, scaling, and offset.

        Returns:
            Decoded value as float

        Example:
            >>> # Unsigned with scale
            >>> val = RegisterValue(0x0100, 486, DataType.UINT16, scale=0.1)
            >>> assert val.decoded_value == 48.6

            >>> # Signed negative with offset
            >>> val = RegisterValue(0x0200, 0xFFCE, DataType.INT16, offset=0)
            >>> assert val.decoded_value == -50
        """
        # Convert based on data type
        if self.data_type == DataType.UINT16:
            typed_value = self.raw_value
        elif self.data_type == DataType.INT16:
            # Convert to signed int16
            typed_value = self._to_signed_int16(self.raw_value)
        elif self.data_type == DataType.UINT32:
            typed_value = self.raw_value
        elif self.data_type == DataType.INT32:
            # Convert to signed int32
            typed_value = self._to_signed_int32(self.raw_value)
        else:
            typed_value = self.raw_value

        # Apply scale and offset
        return (typed_value * self.scale) + self.offset

    @staticmethod
    def _to_signed_int16(value: int) -> int:
        """Convert uint16 to signed int16.

        Args:
            value: Unsigned 16-bit value (0-65535)

        Returns:
            Signed interpretation (-32768 to 32767)

        Example:
            >>> RegisterValue._to_signed_int16(0xFFCE)
            -50
            >>> RegisterValue._to_signed_int16(0x7FFF)
            32767
        """
        return convert_to_signed_int16(value)

    @staticmethod
    def _to_signed_int32(value: int) -> int:
        """Convert uint32 to signed int32.

        Args:
            value: Unsigned 32-bit value (0-4294967295)

        Returns:
            Signed interpretation (-2147483648 to 2147483647)
        """
        if value > 0x7FFFFFFF:
            return value - 0x100000000
        return value

    def to_hex(self) -> str:
        """Format raw value as hex string.

        Returns:
            Raw value as hex string

        Example:
            >>> RegisterValue(0x0100, 486).to_hex()
            '0x01E6'
        """
        if self.data_type in (DataType.UINT16, DataType.INT16):
            return f"{self.raw_value:#06x}"
        else:
            return f"{self.raw_value:#010x}"

    def __str__(self) -> str:
        """String representation for logging.

        Returns:
            Human-readable string

        Example:
            >>> str(RegisterValue(0x0100, 486, scale=0.1))
            'RegisterValue(0x0100: 486 → 48.6)'
        """
        return (
            f"RegisterValue({self.address:#06x}: "
            f"{self.raw_value} → {self.decoded_value})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"RegisterValue(address={self.address:#06x}, "
            f"raw_value={self.raw_value}, "
            f"data_type={self.data_type.value}, "
            f"scale={self.scale}, offset={self.offset})"
        )
