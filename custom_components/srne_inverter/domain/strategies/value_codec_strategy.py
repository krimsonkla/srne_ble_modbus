"""Value encoding/decoding strategies using Strategy pattern."""

from abc import ABC, abstractmethod
from typing import Any

from ..helpers.transformations import (
    convert_to_signed_int16,
    convert_to_unsigned_int16,
)


class ValueCodecStrategy(ABC):
    """Abstract strategy for encoding/decoding register values."""

    @abstractmethod
    def decode(self, raw_value: int, scale: float = 1.0, offset: int = 0) -> Any:
        """Decode raw register value to display value.

        Args:
            raw_value: Raw 16-bit register value
            scale: Scaling factor
            offset: Offset to apply before scaling

        Returns:
            Decoded display value
        """

    @abstractmethod
    def encode(self, display_value: Any, scale: float = 1.0, offset: int = 0) -> int:
        """Encode display value to raw register value.

        Args:
            display_value: Display value to encode
            scale: Scaling factor
            offset: Offset to remove before encoding

        Returns:
            Raw 16-bit register value
        """


class UInt16Codec(ValueCodecStrategy):
    """Codec for unsigned 16-bit integers."""

    def decode(self, raw_value: int, scale: float = 1.0, offset: int = 0) -> float:
        """Decode unsigned 16-bit value."""
        return (raw_value + offset) * scale

    def encode(self, display_value: float, scale: float = 1.0, offset: int = 0) -> int:
        """Encode to unsigned 16-bit value."""
        return int(round(display_value / scale)) - offset


class Int16Codec(ValueCodecStrategy):
    """Codec for signed 16-bit integers (two's complement)."""

    def decode(self, raw_value: int, scale: float = 1.0, offset: int = 0) -> float:
        """Decode signed 16-bit value."""
        value = convert_to_signed_int16(raw_value)
        return (value + offset) * scale

    def encode(self, display_value: float, scale: float = 1.0, offset: int = 0) -> int:
        """Encode to signed 16-bit value."""
        value = int(round(display_value / scale)) - offset
        return convert_to_unsigned_int16(value) & 0xFFFF


class BoolCodec(ValueCodecStrategy):
    """Codec for boolean values (0 = False, non-zero = True)."""

    def decode(self, raw_value: int, scale: float = 1.0, offset: int = 0) -> bool:
        """Decode to boolean."""
        return raw_value != 0

    def encode(self, display_value: bool, scale: float = 1.0, offset: int = 0) -> int:
        """Encode from boolean."""
        return 1 if display_value else 0


class CodecFactory:
    """Factory for creating appropriate codec based on data type."""

    _codecs = {
        "uint16": UInt16Codec(),
        "int16": Int16Codec(),
        "bool": BoolCodec(),
    }

    @classmethod
    def get_codec(cls, data_type: str) -> ValueCodecStrategy:
        """Get codec for data type.

        Args:
            data_type: Data type string (uint16, int16, bool)

        Returns:
            Appropriate codec instance

        Raises:
            ValueError: If data type unknown

        Example:
            >>> codec = CodecFactory.get_codec("int16")
            >>> decoded = codec.decode(0xFFEC, scale=0.1)  # -20 in int16
            >>> decoded
            -2.0
        """
        codec = cls._codecs.get(data_type.lower())
        if not codec:
            raise ValueError(f"Unknown data type: {data_type}")
        return codec

    @classmethod
    def register_codec(cls, data_type: str, codec: ValueCodecStrategy):
        """Register custom codec.

        Args:
            data_type: Data type string
            codec: Codec instance

        Example:
            >>> class UInt32Codec(ValueCodecStrategy):
            ...     pass
            >>> CodecFactory.register_codec("uint32", UInt32Codec())
        """
        cls._codecs[data_type.lower()] = codec

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported data types.

        Returns:
            List of data type strings
        """
        return list(cls._codecs.keys())
