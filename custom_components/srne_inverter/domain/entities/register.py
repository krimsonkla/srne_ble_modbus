"""Register entity with business logic.

A Register represents a Modbus register with its configuration and
decoding logic. Unlike RegisterAddress (value object), a Register is
an entity with business behavior.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from ..value_objects import RegisterAddress, RegisterValue
from ..value_objects.register_value import DataType


@dataclass
class Register:
    """Domain entity representing a Modbus register.

    A Register encapsulates:
    - Register address and metadata
    - Data type and conversion parameters
    - Business logic for decoding raw values
    - Validation rules

    Attributes:
        address: Register address (value object)
        name: Human-readable register name
        data_type: How to interpret the raw value
        scale: Scaling factor (default: 1.0)
        offset: Offset to apply after scaling (default: 0)
        unit: Unit of measurement (e.g., "V", "A", "W")
        description: Human-readable description
        read_only: Whether register is read-only
        min_value: Minimum valid decoded value (optional)
        max_value: Maximum valid decoded value (optional)

    Example:
        >>> # Battery voltage register
        >>> register = Register(
        ...     address=RegisterAddress(0x0100),
        ...     name="battery_voltage",
        ...     data_type=DataType.UINT16,
        ...     scale=0.1,
        ...     unit="V",
        ...     description="Battery voltage in volts",
        ...     min_value=40.0,
        ...     max_value=60.0,
        ... )
        >>> value = register.decode_value(486)
        >>> assert value.decoded_value == 48.6
        >>> assert register.is_valid_value(48.6)
    """

    address: RegisterAddress
    name: str
    data_type: DataType = DataType.UINT16
    scale: float = 1.0
    offset: int = 0
    unit: str = ""
    description: str = ""
    read_only: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def decode_value(self, raw_value: int) -> RegisterValue:
        """Decode raw register value to RegisterValue.

        Args:
            raw_value: Raw integer value from device

        Returns:
            RegisterValue with decoded value

        Example:
            >>> register = Register(
            ...     address=RegisterAddress(0x0100),
            ...     name="battery_voltage",
            ...     scale=0.1,
            ... )
            >>> value = register.decode_value(486)
            >>> assert value.decoded_value == 48.6
        """
        return RegisterValue(
            address=int(self.address),
            raw_value=raw_value,
            data_type=self.data_type,
            scale=self.scale,
            offset=self.offset,
        )

    def encode_value(self, decoded_value: float) -> int:
        """Encode decoded value to raw register value.

        Inverse of decode_value. Used when writing to registers.

        Args:
            decoded_value: Human-readable value (e.g., 48.6V)

        Returns:
            Raw integer value to write to device

        Raises:
            ValueError: If value is out of valid range

        Example:
            >>> register = Register(
            ...     address=RegisterAddress(0x0100),
            ...     name="battery_voltage",
            ...     scale=0.1,
            ...     read_only=False,
            ... )
            >>> raw = register.encode_value(48.6)
            >>> assert raw == 486
        """
        if self.read_only:
            raise ValueError(f"Cannot encode value for read-only register {self.name}")

        if not self.is_valid_value(decoded_value):
            raise ValueError(
                f"Value {decoded_value} is out of valid range "
                f"[{self.min_value}, {self.max_value}] for register {self.name}"
            )

        # Reverse the decoding: remove offset, then divide by scale
        raw_float = (decoded_value - self.offset) / self.scale

        # Round to nearest integer
        raw_int = round(raw_float)

        # Validate raw value is in uint16 range
        if raw_int < 0 or raw_int > 0xFFFF:
            raise ValueError(
                f"Encoded value {raw_int} is out of uint16 range for register {self.name}"
            )

        return raw_int

    def is_valid_value(self, decoded_value: float) -> bool:
        """Check if decoded value is within valid range.

        Args:
            decoded_value: Value to validate

        Returns:
            True if value is valid, False otherwise

        Example:
            >>> register = Register(
            ...     address=RegisterAddress(0x0100),
            ...     name="battery_voltage",
            ...     min_value=40.0,
            ...     max_value=60.0,
            ... )
            >>> assert register.is_valid_value(48.6)
            >>> assert not register.is_valid_value(80.0)
        """
        if self.min_value is not None and decoded_value < self.min_value:
            return False
        if self.max_value is not None and decoded_value > self.max_value:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert register to dictionary representation.

        Returns:
            Dictionary with all register attributes

        Example:
            >>> register = Register(
            ...     address=RegisterAddress(0x0100),
            ...     name="battery_voltage",
            ...     unit="V",
            ... )
            >>> data = register.to_dict()
            >>> assert data["name"] == "battery_voltage"
            >>> assert data["address"] == 0x0100
        """
        return {
            "address": int(self.address),
            "address_hex": self.address.to_hex(),
            "name": self.name,
            "data_type": self.data_type.value,
            "scale": self.scale,
            "offset": self.offset,
            "unit": self.unit,
            "description": self.description,
            "read_only": self.read_only,
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Register":
        """Create Register from dictionary representation.

        Args:
            data: Dictionary with register attributes

        Returns:
            Register instance

        Example:
            >>> data = {
            ...     "address": 0x0100,
            ...     "name": "battery_voltage",
            ...     "data_type": "uint16",
            ...     "scale": 0.1,
            ...     "unit": "V",
            ... }
            >>> register = Register.from_dict(data)
            >>> assert register.name == "battery_voltage"
        """
        address = data["address"]
        if not isinstance(address, RegisterAddress):
            address = RegisterAddress(address)

        data_type_str = data.get("data_type", "uint16")
        data_type = DataType(data_type_str)

        return cls(
            address=address,
            name=data["name"],
            data_type=data_type,
            scale=data.get("scale", 1.0),
            offset=data.get("offset", 0),
            unit=data.get("unit", ""),
            description=data.get("description", ""),
            read_only=data.get("read_only", True),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
        )

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Register({self.name} @ {self.address.to_hex()}, "
            f"{self.data_type.value}, scale={self.scale})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Register(address={self.address!r}, name={self.name!r}, "
            f"data_type={self.data_type!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on address (entity identity).

        Two registers are the same if they have the same address,
        regardless of other attributes.

        Args:
            other: Object to compare with

        Returns:
            True if same address, False otherwise
        """
        if not isinstance(other, Register):
            return False
        return self.address == other.address

    def __hash__(self) -> int:
        """Hash based on address for use in sets/dicts."""
        return hash(self.address)
