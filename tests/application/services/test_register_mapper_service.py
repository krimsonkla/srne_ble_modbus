"""Tests for RegisterMapperService.

Tests cover:
- Simple uint16 value mapping
- Signed int16 conversions
- Scaling factors (×0.1, ×0.01, ×10)
- Offset adjustments (+100, -40)
- Multi-register values (32-bit, 64-bit)
- Metadata extraction
- Value validation
- Edge cases (negative values, overflow, etc.)

Phase 2 Week 6: Application Layer Extraction (Day 29)
"""

import pytest
from custom_components.srne_inverter.application.services.register_mapper_service import (
    RegisterMapperService,
)


class TestRegisterMapperService:
    """Test suite for RegisterMapperService."""

    @pytest.fixture
    def service(self):
        """Create RegisterMapperService instance."""
        return RegisterMapperService()

    # =========================================================================
    # to_signed_int16 Tests
    # =========================================================================

    def test_to_signed_int16_positive_values(self, service):
        """Test conversion of positive values."""
        assert service.to_signed_int16(0) == 0
        assert service.to_signed_int16(100) == 100
        assert service.to_signed_int16(32767) == 32767

    def test_to_signed_int16_negative_values(self, service):
        """Test conversion of negative values (two's complement)."""
        assert service.to_signed_int16(32768) == -32768
        assert service.to_signed_int16(65535) == -1
        assert service.to_signed_int16(65500) == -36
        assert service.to_signed_int16(0xFFFF) == -1
        assert service.to_signed_int16(0x8000) == -32768

    def test_to_signed_int16_boundary_values(self, service):
        """Test boundary conditions."""
        assert service.to_signed_int16(0x7FFF) == 32767  # Max positive
        assert service.to_signed_int16(0x8000) == -32768  # Min negative
        assert service.to_signed_int16(0x8001) == -32767

    # =========================================================================
    # convert_data_type Tests
    # =========================================================================

    def test_convert_data_type_uint16(self, service):
        """Test uint16 conversion (no change)."""
        assert service.convert_data_type(0, "uint16") == 0
        assert service.convert_data_type(32768, "uint16") == 32768
        assert service.convert_data_type(65535, "uint16") == 65535

    def test_convert_data_type_int16(self, service):
        """Test int16 conversion (signed)."""
        assert service.convert_data_type(0, "int16") == 0
        assert service.convert_data_type(32767, "int16") == 32767
        assert service.convert_data_type(32768, "int16") == -32768
        assert service.convert_data_type(65535, "int16") == -1

    def test_convert_data_type_unknown_type(self, service):
        """Test unknown data type (returns value unchanged)."""
        assert service.convert_data_type(1234, "unknown") == 1234

    # =========================================================================
    # extract_multi_register_value Tests
    # =========================================================================

    def test_extract_multi_register_32bit(self, service):
        """Test 32-bit value extraction (2 registers)."""
        # 0x0001 0x0002 -> 0x00010002 = 65538
        values = [1, 2]
        result = service.extract_multi_register_value(values, 0, 2)
        assert result == 65538

        # 0xFFFF 0xFFFF -> 0xFFFFFFFF = 4294967295
        values = [0xFFFF, 0xFFFF]
        result = service.extract_multi_register_value(values, 0, 2)
        assert result == 0xFFFFFFFF

    def test_extract_multi_register_64bit(self, service):
        """Test 64-bit value extraction (4 registers)."""
        # 0x0000 0x0001 0x0000 0x0002 -> 65538
        values = [0, 1, 0, 2]
        result = service.extract_multi_register_value(values, 0, 4)
        assert result == 0x0001_0000_0002

    def test_extract_multi_register_offset(self, service):
        """Test extraction with non-zero offset."""
        values = [99, 1, 2, 99]
        result = service.extract_multi_register_value(values, 1, 2)
        assert result == 65538

    def test_extract_multi_register_insufficient_values(self, service):
        """Test extraction when not enough values available."""
        values = [1]
        result = service.extract_multi_register_value(values, 0, 2)
        assert result is None

        values = [1, 2]
        result = service.extract_multi_register_value(values, 1, 2)
        assert result is None

    # =========================================================================
    # apply_transformations Tests
    # =========================================================================

    def test_apply_transformations_no_scaling(self, service):
        """Test transformation with no scaling (default=1)."""
        reg_def = {"data_type": "uint16"}
        result = service.apply_transformations(100, reg_def)
        assert result == 100

    def test_apply_transformations_scaling_voltage(self, service):
        """Test voltage scaling (×0.1)."""
        # Battery voltage: raw 2400 × 0.1 = 240.0V
        reg_def = {"data_type": "uint16", "scaling": 0.1}
        result = service.apply_transformations(2400, reg_def)
        assert result == 240.0

    def test_apply_transformations_scaling_current(self, service):
        """Test current scaling with signed values (×0.1)."""
        # Current: raw -36 (65500 unsigned) × 0.1 = -3.6A
        reg_def = {"data_type": "int16", "scaling": 0.1}
        result = service.apply_transformations(65500, reg_def)
        assert result == pytest.approx(-3.6)

    def test_apply_transformations_scaling_power(self, service):
        """Test power scaling (×1, no change)."""
        reg_def = {"data_type": "uint16", "scaling": 1}
        result = service.apply_transformations(500, reg_def)
        assert result == 500

    def test_apply_transformations_scaling_small(self, service):
        """Test small scaling factor (×0.01)."""
        reg_def = {"data_type": "uint16", "scaling": 0.01}
        result = service.apply_transformations(12345, reg_def)
        assert result == pytest.approx(123.45)

    def test_apply_transformations_scaling_large(self, service):
        """Test large scaling factor (×10)."""
        reg_def = {"data_type": "uint16", "scaling": 10}
        result = service.apply_transformations(50, reg_def)
        assert result == 500

    def test_apply_transformations_with_offset_temperature(self, service):
        """Test temperature with offset: value × 0.1 - 40."""
        # Temperature: raw 250 × 0.1 - 40 = -15.0°C
        reg_def = {"data_type": "uint16", "scaling": 0.1, "offset": -40}
        result = service.apply_transformations(250, reg_def)
        assert result == pytest.approx(-15.0)

    def test_apply_transformations_with_positive_offset(self, service):
        """Test positive offset adjustment."""
        reg_def = {"data_type": "uint16", "scaling": 1, "offset": 100}
        result = service.apply_transformations(50, reg_def)
        assert result == 150

    def test_apply_transformations_combined(self, service):
        """Test combined scaling and offset."""
        # (raw × scaling) + offset
        # (1000 × 0.1) + 10 = 110
        reg_def = {"data_type": "uint16", "scaling": 0.1, "offset": 10}
        result = service.apply_transformations(1000, reg_def)
        assert result == pytest.approx(110.0)

    def test_apply_transformations_multi_register_uint32(self, service):
        """Test multi-register unsigned 32-bit value."""
        # Combined value 0x00010002 = 65538
        reg_def = {"data_type": "uint32", "scaling": 1, "length": 2}
        result = service.apply_transformations(65538, reg_def)
        assert result == 65538

    def test_apply_transformations_multi_register_int32(self, service):
        """Test multi-register signed 32-bit value."""
        # 0xFFFFFFFF = -1 (signed)
        reg_def = {"data_type": "int32", "scaling": 1, "length": 2}
        result = service.apply_transformations(0xFFFFFFFF, reg_def)
        assert result == -1

    # =========================================================================
    # map_batch_to_registers Tests
    # =========================================================================

    def test_map_batch_simple_values(self, service):
        """Test mapping simple register values."""
        raw_values = [2400, 100, 500]
        register_map = {
            0: "battery_voltage",
            1: "battery_current",
            2: "power",
        }
        definitions = {
            "battery_voltage": {"data_type": "uint16", "scaling": 0.1},
            "battery_current": {"data_type": "uint16", "scaling": 0.1},
            "power": {"data_type": "uint16", "scaling": 1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["battery_voltage"] == pytest.approx(240.0)
        assert result["battery_current"] == pytest.approx(10.0)
        assert result["power"] == 500

    def test_map_batch_signed_values(self, service):
        """Test mapping with signed values."""
        raw_values = [65500, 32768]  # -36, -32768 when signed
        register_map = {
            0: "current",
            1: "temperature_offset",
        }
        definitions = {
            "current": {"data_type": "int16", "scaling": 0.1},
            "temperature_offset": {"data_type": "int16", "scaling": 1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["current"] == pytest.approx(-3.6)
        assert result["temperature_offset"] == -32768

    def test_map_batch_multi_register_value(self, service):
        """Test mapping with multi-register (32-bit) value."""
        # Battery capacity: 2 registers combine to form 32-bit value
        raw_values = [0, 1, 100]  # First two combine: 0x0001
        register_map = {
            0: "battery_capacity_ah",
            2: "voltage",  # Note: offset 2 because capacity uses 2 registers
        }
        definitions = {
            "battery_capacity_ah": {
                "data_type": "uint32",
                "scaling": 1,
                "length": 2,
            },
            "voltage": {"data_type": "uint16", "scaling": 0.1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["battery_capacity_ah"] == 1
        assert result["voltage"] == pytest.approx(10.0)

    def test_map_batch_skips_processed_offsets(self, service):
        """Test that offsets consumed by multi-register are skipped."""
        # Register map tries to read offset 1 separately, but it's part of capacity
        raw_values = [0, 1, 100]
        register_map = {
            0: "battery_capacity_ah",  # Uses offsets 0 and 1
            1: "should_be_skipped",  # Offset 1 already consumed
            2: "voltage",
        }
        definitions = {
            "battery_capacity_ah": {
                "data_type": "uint32",
                "scaling": 1,
                "length": 2,
            },
            "should_be_skipped": {"data_type": "uint16", "scaling": 1},
            "voltage": {"data_type": "uint16", "scaling": 0.1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        # Offset 1 should be skipped because it's part of capacity
        assert "battery_capacity_ah" in result
        assert "should_be_skipped" not in result  # This offset was consumed
        assert "voltage" in result
        assert result["battery_capacity_ah"] == 1

    def test_map_batch_missing_definition(self, service):
        """Test mapping with missing register definition (uses defaults)."""
        raw_values = [100]
        register_map = {0: "unknown_register"}
        definitions = {}

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        # Should use defaults: no scaling, uint16
        assert result["unknown_register"] == 100

    def test_map_batch_offset_exceeds_length(self, service):
        """Test mapping when offset exceeds raw values length."""
        raw_values = [100]
        register_map = {
            0: "valid",
            5: "invalid",  # Offset 5 doesn't exist
        }
        definitions = {
            "valid": {"data_type": "uint16", "scaling": 1},
            "invalid": {"data_type": "uint16", "scaling": 1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        # Should only include valid register
        assert "valid" in result
        assert "invalid" not in result

    def test_map_batch_multi_register_insufficient_values(self, service):
        """Test multi-register when not enough values available."""
        raw_values = [1]  # Only 1 value, but definition needs 2
        register_map = {0: "capacity"}
        definitions = {
            "capacity": {"data_type": "uint32", "scaling": 1, "length": 2},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        # Should skip register due to insufficient values
        assert "capacity" not in result

    def test_map_batch_empty_values(self, service):
        """Test mapping with empty values list."""
        result = service.map_batch_to_registers([], {0: "test"}, {})
        assert result == {}

    def test_map_batch_empty_register_map(self, service):
        """Test mapping with empty register map."""
        result = service.map_batch_to_registers([100], {}, {})
        assert result == {}

    # =========================================================================
    # extract_metadata Tests
    # =========================================================================

    def test_extract_metadata_complete(self, service):
        """Test metadata extraction with all fields."""
        definition = {
            "unit": "V",
            "device_class": "voltage",
            "state_class": "measurement",
            "name": "Battery Voltage",
            "description": "Current battery voltage",
        }

        metadata = service.extract_metadata("battery_voltage", definition)

        assert metadata["unit"] == "V"
        assert metadata["device_class"] == "voltage"
        assert metadata["state_class"] == "measurement"
        assert metadata["name"] == "Battery Voltage"
        assert metadata["description"] == "Current battery voltage"

    def test_extract_metadata_partial(self, service):
        """Test metadata extraction with missing fields."""
        definition = {
            "unit": "A",
        }

        metadata = service.extract_metadata("current", definition)

        assert metadata["unit"] == "A"
        assert metadata["device_class"] is None
        assert metadata["state_class"] is None
        assert metadata["name"] == "current"  # Falls back to register name
        assert metadata["description"] is None

    def test_extract_metadata_empty_definition(self, service):
        """Test metadata extraction from empty definition."""
        metadata = service.extract_metadata("test_register", {})

        assert metadata["unit"] is None
        assert metadata["device_class"] is None
        assert metadata["state_class"] is None
        assert metadata["name"] == "test_register"
        assert metadata["description"] is None

    # =========================================================================
    # validate_transformed_value Tests
    # =========================================================================

    def test_validate_transformed_value_within_range(self, service):
        """Test validation of value within min/max range."""
        definition = {"min": 0, "max": 100}
        assert service.validate_transformed_value(0, definition) is True
        assert service.validate_transformed_value(50, definition) is True
        assert service.validate_transformed_value(100, definition) is True

    def test_validate_transformed_value_below_min(self, service):
        """Test validation of value below minimum."""
        definition = {"min": 0, "max": 100}
        assert service.validate_transformed_value(-1, definition) is False
        assert service.validate_transformed_value(-50, definition) is False

    def test_validate_transformed_value_above_max(self, service):
        """Test validation of value above maximum."""
        definition = {"min": 0, "max": 100}
        assert service.validate_transformed_value(101, definition) is False
        assert service.validate_transformed_value(200, definition) is False

    def test_validate_transformed_value_no_constraints(self, service):
        """Test validation with no min/max constraints."""
        definition = {}
        assert service.validate_transformed_value(-1000, definition) is True
        assert service.validate_transformed_value(0, definition) is True
        assert service.validate_transformed_value(1000, definition) is True

    def test_validate_transformed_value_only_min(self, service):
        """Test validation with only min constraint."""
        definition = {"min": 10}
        assert service.validate_transformed_value(10, definition) is True
        assert service.validate_transformed_value(100, definition) is True
        assert service.validate_transformed_value(9, definition) is False

    def test_validate_transformed_value_only_max(self, service):
        """Test validation with only max constraint."""
        definition = {"max": 50}
        assert service.validate_transformed_value(-100, definition) is True
        assert service.validate_transformed_value(50, definition) is True
        assert service.validate_transformed_value(51, definition) is False

    # =========================================================================
    # Edge Cases and Integration Tests
    # =========================================================================

    def test_edge_case_zero_values(self, service):
        """Test handling of zero values."""
        raw_values = [0, 0, 0]
        register_map = {0: "a", 1: "b", 2: "c"}
        definitions = {
            "a": {"data_type": "uint16", "scaling": 1},
            "b": {"data_type": "int16", "scaling": 1},
            "c": {"data_type": "uint16", "scaling": 0.1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["a"] == 0
        assert result["b"] == 0
        assert result["c"] == 0.0

    def test_edge_case_max_uint16_values(self, service):
        """Test handling of maximum uint16 values."""
        raw_values = [65535, 65535]
        register_map = {0: "unsigned", 1: "signed"}
        definitions = {
            "unsigned": {"data_type": "uint16", "scaling": 1},
            "signed": {"data_type": "int16", "scaling": 1},
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["unsigned"] == 65535
        assert result["signed"] == -1

    def test_real_world_scenario_battery_monitoring(self, service):
        """Test real-world battery monitoring scenario."""
        # Simulates actual inverter data
        raw_values = [
            2400,  # Battery voltage: 240.0V
            65500,  # Battery current: -3.6A (discharging)
            500,  # Power: 500W
            8000,  # Battery SOC: 80.00%
        ]
        register_map = {
            0: "battery_voltage",
            1: "battery_current",
            2: "power",
            3: "battery_soc",
        }
        definitions = {
            "battery_voltage": {
                "data_type": "uint16",
                "scaling": 0.1,
                "unit": "V",
                "min": 0,
                "max": 1000,
            },
            "battery_current": {
                "data_type": "int16",
                "scaling": 0.1,
                "unit": "A",
                "min": -500,
                "max": 500,
            },
            "power": {
                "data_type": "uint16",
                "scaling": 1,
                "unit": "W",
                "min": 0,
                "max": 10000,
            },
            "battery_soc": {
                "data_type": "uint16",
                "scaling": 0.01,
                "unit": "%",
                "min": 0,
                "max": 100,
            },
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["battery_voltage"] == pytest.approx(240.0)
        assert result["battery_current"] == pytest.approx(-3.6)
        assert result["power"] == 500
        assert result["battery_soc"] == pytest.approx(80.0)

        # Validate all values
        for reg_name, value in result.items():
            assert service.validate_transformed_value(value, definitions[reg_name])

    def test_real_world_scenario_temperature_sensors(self, service):
        """Test real-world temperature sensor scenario with offset."""
        # Temperature sensors often use offset adjustment
        raw_values = [
            250,  # Ambient: 25.0 - 40 = -15.0°C
            650,  # Battery: 65.0 - 40 = 25.0°C
            900,  # Inverter: 90.0 - 40 = 50.0°C
        ]
        register_map = {
            0: "ambient_temp",
            1: "battery_temp",
            2: "inverter_temp",
        }
        definitions = {
            "ambient_temp": {
                "data_type": "uint16",
                "scaling": 0.1,
                "offset": -40,
                "unit": "°C",
            },
            "battery_temp": {
                "data_type": "uint16",
                "scaling": 0.1,
                "offset": -40,
                "unit": "°C",
            },
            "inverter_temp": {
                "data_type": "uint16",
                "scaling": 0.1,
                "offset": -40,
                "unit": "°C",
            },
        }

        result = service.map_batch_to_registers(
            raw_values,
            register_map,
            definitions,
        )

        assert result["ambient_temp"] == pytest.approx(-15.0)
        assert result["battery_temp"] == pytest.approx(25.0)
        assert result["inverter_temp"] == pytest.approx(50.0)
