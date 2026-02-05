"""RegisterMapperService for mapping raw register values to named registers.

This service handles the transformation of raw Modbus register values into
meaningful data with proper data types, scaling, and units.

Extracted from coordinator._to_signed_int16() and register_batching.extract_batch_data().
Application Layer Extraction
"""

import logging
from typing import Any, Dict, List, Optional

from ...domain.value_objects import RegisterAddress, RegisterValue
from ...domain.helpers.transformations import convert_to_signed_int16

_LOGGER = logging.getLogger(__name__)


class RegisterMapperService:
    """Service for mapping and transforming register values.

    This service handles:
    - Mapping raw register values to named registers
    - Data type conversions (uint16, int16, uint32, int32)
    - Applying scaling factors (e.g., ×0.1 for voltage)
    - Applying offset adjustments (e.g., -40 for temperature)
    - Multi-register value extraction (32-bit, 64-bit)
    - Metadata extraction (units, device_class, state_class)

    Responsibilities:
    - Convert raw register arrays to named value dictionaries
    - Apply data type conversions (signed/unsigned)
    - Apply scaling and offset transformations
    - Extract multi-register values
    - Validate transformed values

    Example:
        >>> service = RegisterMapperService()
        >>> batch_data = {0: 2400, 1: 65500}  # offset -> raw_value
        >>> register_map = {0: "battery_voltage", 1: "battery_current"}
        >>> definitions = {
        ...     "battery_voltage": {"scaling": 0.1, "data_type": "uint16"},
        ...     "battery_current": {"scaling": 0.1, "data_type": "int16"}
        ... }
        >>> result = service.map_batch_to_registers(batch_data, register_map, definitions)
        >>> assert result["battery_voltage"] == 240.0  # 2400 * 0.1
        >>> assert result["battery_current"] == -3.6   # -36 * 0.1
    """

    def map_batch_to_registers(
        self,
        raw_values: List[int],
        register_map: Dict[int, str],
        register_definitions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Map raw register values to named registers with transformations.

        Args:
            raw_values: List of raw uint16 values from Modbus response
            register_map: Mapping of offset -> register_name
            register_definitions: Register definitions with scaling, data_type, etc.

        Returns:
            Dictionary of register_name -> transformed_value

        Example:
            >>> raw_values = [2400, 100, 5000]
            >>> register_map = {0: "voltage", 1: "current", 2: "power"}
            >>> definitions = {
            ...     "voltage": {"scaling": 0.1, "data_type": "uint16"},
            ...     "current": {"scaling": 0.1, "data_type": "int16"},
            ...     "power": {"scaling": 1, "data_type": "uint16"}
            ... }
            >>> result = service.map_batch_to_registers(raw_values, register_map, definitions)
            >>> assert result == {"voltage": 240.0, "current": 10.0, "power": 5000}
        """
        data = {}
        processed_offsets = set()  # Track which offsets consumed by multi-register

        for offset, reg_name in register_map.items():
            # Skip if already processed as part of multi-register value
            if offset in processed_offsets:
                continue

            if offset >= len(raw_values):
                _LOGGER.debug(
                    "Offset %d for register %s exceeds response length %d",
                    offset,
                    reg_name,
                    len(raw_values),
                )
                continue

            reg_def = register_definitions.get(reg_name, {})
            length = reg_def.get("length", 1)

            # Extract raw value (single or multi-register)
            if length > 1:
                raw_value = self.extract_multi_register_value(
                    raw_values,
                    offset,
                    length,
                )
                if raw_value is None:
                    _LOGGER.debug(
                        "Multi-register value %s (length=%d) at offset %d exceeds response length",
                        reg_name,
                        length,
                        offset,
                    )
                    continue

                # Mark all offsets as processed
                for i in range(length):
                    processed_offsets.add(offset + i)
            else:
                raw_value = raw_values[offset]
                processed_offsets.add(offset)

            # Apply transformations
            transformed_value = self.apply_transformations(raw_value, reg_def)
            data[reg_name] = transformed_value

        return data

    def apply_transformations(
        self,
        raw_value: int,
        register_definition: Dict[str, Any],
    ) -> float:
        """Apply data type conversion, scaling, and offset to raw value.

        Args:
            raw_value: Raw register value (uint16 or combined multi-register)
            register_definition: Register definition with data_type, scaling, offset

        Returns:
            Transformed value as float

        Example:
            >>> # Voltage: 2400 * 0.1 = 240.0V
            >>> service.apply_transformations(2400, {"scaling": 0.1, "data_type": "uint16"})
            240.0

            >>> # Current: -36 * 0.1 = -3.6A (signed)
            >>> service.apply_transformations(65500, {"scaling": 0.1, "data_type": "int16"})
            -3.6

            >>> # Temperature: 250 * 0.1 - 40 = -15.0°C
            >>> service.apply_transformations(250, {"scaling": 0.1, "offset": -40})
            -15.0
        """
        # Get transformation parameters
        data_type = register_definition.get("data_type", "uint16")
        scaling = register_definition.get("scaling", 1)
        offset = register_definition.get("offset", 0)
        length = register_definition.get("length", 1)

        # Apply data type conversion (only for single register values)
        if length == 1:
            converted_value = self.convert_data_type(raw_value, data_type)
        else:
            # Multi-register values - check data type
            if data_type in ("int32", "int64"):
                # Convert to signed
                converted_value = self._to_signed_multi_register(raw_value, length)
            else:
                converted_value = raw_value

        # Apply scaling
        scaled_value = converted_value * scaling

        # Apply offset
        final_value = scaled_value + offset

        return final_value

    def convert_data_type(self, value: int, data_type: str) -> int:
        """Convert raw value to specified data type.

        Args:
            value: Raw uint16 value (0-65535)
            data_type: Target data type (uint16, int16, uint32, int32, etc.)

        Returns:
            Converted value

        Example:
            >>> service.convert_data_type(65535, "uint16")
            65535
            >>> service.convert_data_type(65535, "int16")
            -1
            >>> service.convert_data_type(32768, "int16")
            -32768
        """
        if data_type == "int16":
            return convert_to_signed_int16(value)
        elif data_type == "uint16":
            return value
        else:
            # For multi-register types (uint32, int32, etc.), no conversion here
            # Conversion handled in apply_transformations
            return value

    def extract_multi_register_value(
        self,
        values: List[int],
        start_offset: int,
        register_count: int,
    ) -> Optional[int]:
        """Extract multi-register value (32-bit, 64-bit).

        Combines multiple consecutive 16-bit registers into a single value.
        Uses big-endian byte order (high word first).

        Args:
            values: List of raw uint16 values
            start_offset: Starting offset in values list
            register_count: Number of registers to combine (2=32bit, 4=64bit)

        Returns:
            Combined value as int, or None if not enough values

        Example:
            >>> # 32-bit: 0x0001 0x0002 -> 0x00010002 = 65538
            >>> service.extract_multi_register_value([1, 2], 0, 2)
            65538

            >>> # 64-bit: Combine 4 registers
            >>> service.extract_multi_register_value([0, 0, 1, 2], 0, 4)
            65538
        """
        if start_offset + register_count > len(values):
            return None

        # Combine registers: high word first (big-endian)
        combined_value = 0
        for i in range(register_count):
            combined_value = (combined_value << 16) | values[start_offset + i]

        return combined_value

    def _to_signed_multi_register(self, value: int, register_count: int) -> int:
        """Convert multi-register unsigned value to signed.

        Args:
            value: Unsigned multi-register value
            register_count: Number of registers (2=32bit, 4=64bit)

        Returns:
            Signed value

        Example:
            >>> # 32-bit: 0xFFFFFFFF -> -1
            >>> service._to_signed_multi_register(0xFFFFFFFF, 2)
            -1

            >>> # 32-bit: 0x80000000 -> -2147483648
            >>> service._to_signed_multi_register(0x80000000, 2)
            -2147483648
        """
        bit_count = register_count * 16
        sign_bit = 1 << (bit_count - 1)

        if value >= sign_bit:
            return value - (1 << bit_count)
        return value

    def extract_metadata(
        self,
        register_name: str,
        register_definition: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract metadata from register definition.

        Args:
            register_name: Register name
            register_definition: Register definition dictionary

        Returns:
            Dictionary with metadata (unit, device_class, state_class, etc.)

        Example:
            >>> definition = {
            ...     "unit": "V",
            ...     "device_class": "voltage",
            ...     "state_class": "measurement"
            ... }
            >>> metadata = service.extract_metadata("battery_voltage", definition)
            >>> assert metadata["unit"] == "V"
            >>> assert metadata["device_class"] == "voltage"
        """
        return {
            "unit": register_definition.get("unit"),
            "device_class": register_definition.get("device_class"),
            "state_class": register_definition.get("state_class"),
            "name": register_definition.get("name", register_name),
            "description": register_definition.get("description"),
        }

    def validate_transformed_value(
        self,
        value: float,
        register_definition: Dict[str, Any],
    ) -> bool:
        """Validate transformed value against min/max constraints.

        Args:
            value: Transformed value
            register_definition: Register definition with min/max

        Returns:
            True if value is within valid range

        Example:
            >>> definition = {"min": 0, "max": 100}
            >>> service.validate_transformed_value(50, definition)
            True
            >>> service.validate_transformed_value(150, definition)
            False
        """
        min_value = register_definition.get("min")
        max_value = register_definition.get("max")

        if min_value is not None and value < min_value:
            _LOGGER.warning(
                "Value %.2f below minimum %.2f",
                value,
                min_value,
            )
            return False

        if max_value is not None and value > max_value:
            _LOGGER.warning(
                "Value %.2f above maximum %.2f",
                value,
                max_value,
            )
            return False

        return True
