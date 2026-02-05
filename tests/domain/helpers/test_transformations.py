"""Tests for transformation helper functions."""

import pytest

from custom_components.srne_inverter.domain.helpers.transformations import (
    apply_precision,
    apply_scaling,
    convert_to_signed_int16,
    convert_to_unsigned_int16,
    encode_register_value,
    process_register_value,
)


class TestApplyScaling:
    """Test apply_scaling function."""

    def test_scale_identity(self):
        """Test scaling by 1.0 (identity)."""
        assert apply_scaling(100) == 100.0
        assert apply_scaling(0) == 0.0
        assert apply_scaling(65535) == 65535.0

    def test_scale_multiply(self):
        """Test scaling up (multiplying)."""
        assert apply_scaling(100, 2.0) == 200.0
        assert apply_scaling(50, 10.0) == 500.0

    def test_scale_divide(self):
        """Test scaling down (dividing)."""
        assert apply_scaling(100, 0.1) == 10.0
        assert apply_scaling(1000, 0.01) == 10.0

    def test_scale_with_float_value(self):
        """Test scaling with float input."""
        assert apply_scaling(12.5, 2.0) == 25.0

    def test_scale_with_zero(self):
        """Test scaling zero."""
        assert apply_scaling(0, 100.0) == 0.0

    def test_scale_returns_float(self):
        """Test scaling always returns float."""
        result = apply_scaling(100)
        assert isinstance(result, float)


class TestApplyPrecision:
    """Test apply_precision function."""

    def test_precision_default(self):
        """Test default precision (2 decimal places)."""
        assert apply_precision(12.3456) == 12.35
        assert apply_precision(12.3449) == 12.34

    def test_precision_zero(self):
        """Test rounding to integer."""
        assert apply_precision(12.7, 0) == 13.0
        assert apply_precision(12.4, 0) == 12.0

    def test_precision_one(self):
        """Test rounding to 1 decimal place."""
        assert apply_precision(12.34, 1) == 12.3
        assert apply_precision(12.36, 1) == 12.4

    def test_precision_three(self):
        """Test rounding to 3 decimal places."""
        assert apply_precision(12.34567, 3) == 12.346

    def test_precision_already_rounded(self):
        """Test value already at precision."""
        assert apply_precision(12.5, 1) == 12.5
        assert apply_precision(10.0, 2) == 10.0


class TestConvertToSignedInt16:
    """Test convert_to_signed_int16 function."""

    def test_positive_values(self):
        """Test positive values remain positive."""
        assert convert_to_signed_int16(0) == 0
        assert convert_to_signed_int16(1) == 1
        assert convert_to_signed_int16(100) == 100
        assert convert_to_signed_int16(32767) == 32767

    def test_max_positive(self):
        """Test maximum positive value (0x7FFF = 32767)."""
        assert convert_to_signed_int16(0x7FFF) == 32767

    def test_min_negative(self):
        """Test minimum negative value (0x8000 = -32768)."""
        assert convert_to_signed_int16(0x8000) == -32768

    def test_negative_one(self):
        """Test -1 (0xFFFF)."""
        assert convert_to_signed_int16(0xFFFF) == -1

    def test_negative_values(self):
        """Test various negative values."""
        assert convert_to_signed_int16(0xFFFE) == -2
        assert convert_to_signed_int16(0xFF00) == -256
        assert convert_to_signed_int16(0x8001) == -32767


class TestConvertToUnsignedInt16:
    """Test convert_to_unsigned_int16 function."""

    def test_positive_values(self):
        """Test positive values remain positive."""
        assert convert_to_unsigned_int16(0) == 0
        assert convert_to_unsigned_int16(1) == 1
        assert convert_to_unsigned_int16(100) == 100
        assert convert_to_unsigned_int16(32767) == 32767

    def test_max_positive(self):
        """Test maximum positive signed value."""
        assert convert_to_unsigned_int16(32767) == 0x7FFF

    def test_min_negative(self):
        """Test minimum negative value (-32768)."""
        assert convert_to_unsigned_int16(-32768) == 0x8000

    def test_negative_one(self):
        """Test -1 converts to 0xFFFF."""
        assert convert_to_unsigned_int16(-1) == 0xFFFF

    def test_negative_values(self):
        """Test various negative values."""
        assert convert_to_unsigned_int16(-2) == 0xFFFE
        assert convert_to_unsigned_int16(-256) == 0xFF00
        assert convert_to_unsigned_int16(-32767) == 0x8001

    def test_masks_to_16_bits(self):
        """Test result is masked to 16 bits."""
        # Even if input is somehow larger, mask to 16 bits
        result = convert_to_unsigned_int16(100000)
        assert 0 <= result <= 0xFFFF


class TestConversionRoundtrip:
    """Test conversion roundtrips."""

    def test_signed_unsigned_roundtrip(self):
        """Test converting signed->unsigned->signed."""
        test_values = [0, 1, -1, 100, -100, 32767, -32768]
        for value in test_values:
            unsigned = convert_to_unsigned_int16(value)
            signed = convert_to_signed_int16(unsigned)
            assert signed == value

    def test_unsigned_signed_roundtrip(self):
        """Test converting unsigned->signed->unsigned."""
        test_values = [0, 1, 100, 0x7FFF, 0x8000, 0xFFFF]
        for value in test_values:
            signed = convert_to_signed_int16(value)
            unsigned = convert_to_unsigned_int16(signed)
            assert unsigned == value


class TestProcessRegisterValue:
    """Test process_register_value function."""

    def test_no_transformation(self):
        """Test with default parameters (no transformation)."""
        assert process_register_value(1000) == 1000.0

    def test_uint16_data_type(self):
        """Test unsigned 16-bit data type."""
        assert process_register_value(1000, data_type="uint16") == 1000.0
        assert process_register_value(65535, data_type="uint16") == 65535.0

    def test_int16_data_type(self):
        """Test signed 16-bit data type."""
        assert process_register_value(0x7FFF, data_type="int16") == 32767.0
        assert process_register_value(0x8000, data_type="int16") == -32768.0
        assert process_register_value(0xFFFF, data_type="int16") == -1.0

    def test_with_scaling(self):
        """Test with scaling factor."""
        assert process_register_value(1000, scale=0.1) == 100.0
        assert process_register_value(500, scale=2.0) == 1000.0

    def test_with_offset(self):
        """Test with offset."""
        assert process_register_value(100, offset=10) == 110.0
        assert process_register_value(100, offset=-10) == 90.0

    def test_with_precision(self):
        """Test with precision rounding."""
        # Scale 1000 by 0.003 = 3.0 (should round to 3.00 with precision=2)
        assert process_register_value(1000, scale=0.003, precision=2) == 3.0

        # More complex: scale creates decimals, precision rounds
        assert process_register_value(1234, scale=0.1, precision=1) == 123.4

    def test_combined_transformations(self):
        """Test with all transformations combined."""
        # Raw: 1000
        # Offset: 1000 + 10 = 1010
        # Scale: 1010 * 0.1 = 101.0
        # Precision: round(101.0, 2) = 101.0
        assert process_register_value(1000, offset=10, scale=0.1, precision=2) == 101.0

    def test_int16_with_scaling(self):
        """Test signed conversion with scaling."""
        # 0x8000 = -32768 in signed
        # -32768 * 0.1 = -3276.8
        assert process_register_value(0x8000, data_type="int16", scale=0.1) == -3276.8


class TestEncodeRegisterValue:
    """Test encode_register_value function."""

    def test_no_transformation(self):
        """Test encoding with default parameters."""
        assert encode_register_value(1000.0) == 1000
        assert encode_register_value(100) == 100

    def test_uint16_data_type(self):
        """Test encoding unsigned values."""
        assert encode_register_value(1000.0, data_type="uint16") == 1000
        assert encode_register_value(65535.0, data_type="uint16") == 65535

    def test_int16_data_type(self):
        """Test encoding signed values."""
        assert encode_register_value(32767.0, data_type="int16") == 0x7FFF
        assert encode_register_value(-32768.0, data_type="int16") == 0x8000
        assert encode_register_value(-1.0, data_type="int16") == 0xFFFF

    def test_with_scaling(self):
        """Test encoding with scaling."""
        assert encode_register_value(100.0, scale=0.1) == 1000
        assert encode_register_value(1000.0, scale=2.0) == 500

    def test_with_offset(self):
        """Test encoding with offset."""
        assert encode_register_value(110.0, offset=10) == 100
        assert encode_register_value(90.0, offset=-10) == 100

    def test_combined_transformations(self):
        """Test encoding with all transformations."""
        # Display: 101.0
        # Unscale: 101.0 / 0.1 = 1010
        # Remove offset: 1010 - 10 = 1000
        assert encode_register_value(101.0, offset=10, scale=0.1) == 1000

    def test_int16_with_scaling(self):
        """Test encoding signed values with scaling."""
        # Display: -3276.8
        # Unscale: -3276.8 / 0.1 = -32768
        # Convert to unsigned: -32768 -> 0x8000
        assert encode_register_value(-3276.8, data_type="int16", scale=0.1) == 0x8000

    def test_rounds_to_nearest_int(self):
        """Test encoding rounds to nearest integer."""
        assert encode_register_value(100.4, scale=0.1) == 1004
        assert encode_register_value(100.5, scale=0.1) == 1005
        assert encode_register_value(100.6, scale=0.1) == 1006


class TestProcessEncodeRoundtrip:
    """Test process and encode roundtrip."""

    def test_basic_roundtrip(self):
        """Test basic decode->encode roundtrip."""
        raw = 1000
        processed = process_register_value(raw)
        encoded = encode_register_value(processed)
        assert encoded == raw

    def test_roundtrip_with_scaling(self):
        """Test roundtrip with scaling."""
        raw = 1000
        scale = 0.1
        processed = process_register_value(raw, scale=scale)
        encoded = encode_register_value(processed, scale=scale)
        assert encoded == raw

    def test_roundtrip_with_offset_and_scale(self):
        """Test roundtrip with offset and scale."""
        raw = 1000
        offset = 10
        scale = 0.1
        processed = process_register_value(raw, offset=offset, scale=scale)
        encoded = encode_register_value(processed, offset=offset, scale=scale)
        assert encoded == raw

    def test_roundtrip_int16(self):
        """Test roundtrip with signed data type."""
        raw = 0x8000  # -32768 signed
        data_type = "int16"
        processed = process_register_value(raw, data_type=data_type)
        encoded = encode_register_value(processed, data_type=data_type)
        assert encoded == raw

    def test_roundtrip_all_transformations(self):
        """Test roundtrip with all transformations."""
        raw = 1234
        data_type = "int16"
        offset = 5
        scale = 0.1
        processed = process_register_value(
            raw, data_type=data_type, offset=offset, scale=scale
        )
        encoded = encode_register_value(
            processed, data_type=data_type, offset=offset, scale=scale
        )
        assert encoded == raw


class TestIntegration:
    """Integration tests for transformations."""

    def test_temperature_sensor_conversion(self):
        """Test typical temperature sensor conversion."""
        # Raw value: 235 (23.5°C with scale 0.1)
        raw = 235
        temp = process_register_value(raw, scale=0.1, precision=1)
        assert temp == 23.5

        # Encode back
        encoded = encode_register_value(temp, scale=0.1)
        assert encoded == raw

    def test_signed_power_conversion(self):
        """Test signed power value (can be negative for battery discharge)."""
        # Raw value: 0xFFFE = -2 (signed), -20W with scale 10
        raw = 0xFFFE
        power = process_register_value(raw, data_type="int16", scale=10, precision=0)
        assert power == -20.0

        # Encode back
        encoded = encode_register_value(power, data_type="int16", scale=10)
        assert encoded == raw

    def test_voltage_with_offset(self):
        """Test voltage conversion with offset."""
        # Some sensors report voltage as offset from baseline
        raw = 100
        voltage = process_register_value(raw, offset=2000, scale=0.01, precision=2)
        assert voltage == 21.0  # (100 + 2000) * 0.01 = 21.0

        # Encode back
        encoded = encode_register_value(voltage, offset=2000, scale=0.01)
        assert encoded == raw
