"""Tests for RegisterValue value object."""

import pytest
from dataclasses import FrozenInstanceError
from custom_components.srne_inverter.domain.value_objects.register_value import (
    RegisterValue,
    DataType,
)


class TestRegisterValueCreation:
    """Test RegisterValue creation and validation."""

    def test_create_basic_value(self):
        """Test creating RegisterValue with basic parameters."""
        value = RegisterValue(address=0x0100, raw_value=486)
        assert value.address == 0x0100
        assert value.raw_value == 486
        assert value.data_type == DataType.UINT16
        assert value.scale == 1.0
        assert value.offset == 0

    def test_create_with_scale(self):
        """Test creating RegisterValue with scale factor."""
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            data_type=DataType.UINT16,
            scale=0.1,
        )
        assert value.scale == 0.1

    def test_create_with_offset(self):
        """Test creating RegisterValue with offset."""
        value = RegisterValue(
            address=0x0200,
            raw_value=65,
            data_type=DataType.INT16,
            offset=-40,
        )
        assert value.offset == -40

    def test_create_with_invalid_raw_value_raises_error(self):
        """Test that invalid raw value raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            RegisterValue(address=0x0100, raw_value=0x10000)

    def test_create_with_negative_raw_value_raises_error(self):
        """Test that negative raw value raises ValueError."""
        with pytest.raises(ValueError, match="must be 0-65535"):
            RegisterValue(address=0x0100, raw_value=-1)


class TestRegisterValueDecoding:
    """Test RegisterValue decoding logic."""

    def test_decode_uint16_no_scale(self):
        """Test decoding unsigned int16 without scaling."""
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            data_type=DataType.UINT16,
        )
        assert value.decoded_value == 486.0

    def test_decode_uint16_with_scale(self):
        """Test decoding unsigned int16 with scale factor."""
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            data_type=DataType.UINT16,
            scale=0.1,
        )
        assert value.decoded_value == pytest.approx(48.6)

    def test_decode_int16_positive(self):
        """Test decoding positive signed int16."""
        value = RegisterValue(
            address=0x0200,
            raw_value=100,
            data_type=DataType.INT16,
        )
        assert value.decoded_value == 100.0

    def test_decode_int16_negative(self):
        """Test decoding negative signed int16."""
        value = RegisterValue(
            address=0x0200,
            raw_value=0xFFCE,  # -50 in signed int16
            data_type=DataType.INT16,
        )
        assert value.decoded_value == -50.0

    def test_decode_with_scale_and_offset(self):
        """Test decoding with both scale and offset."""
        # Temperature sensor: (raw * 1.0) + (-40) = celsius
        value = RegisterValue(
            address=0x0300,
            raw_value=65,
            data_type=DataType.INT16,
            scale=1.0,
            offset=-40,
        )
        assert value.decoded_value == 25.0  # 65 - 40 = 25°C

    def test_decode_battery_voltage(self):
        """Test decoding realistic battery voltage value."""
        # Battery voltage: 486 * 0.1 = 48.6V
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            data_type=DataType.UINT16,
            scale=0.1,
        )
        assert value.decoded_value == pytest.approx(48.6)

    def test_decode_negative_current(self):
        """Test decoding negative battery current (discharging)."""
        # Battery current: -500 (0xFE0C) * 0.01 = -5.00A
        value = RegisterValue(
            address=0x0101,
            raw_value=0xFE0C,  # -500 in signed int16
            data_type=DataType.INT16,
            scale=0.01,
        )
        assert value.decoded_value == pytest.approx(-5.0)


class TestRegisterValueSignedConversion:
    """Test signed integer conversion methods."""

    def test_to_signed_int16_positive(self):
        """Test converting positive uint16 to signed int16."""
        result = RegisterValue._to_signed_int16(0x7FFF)
        assert result == 32767

    def test_to_signed_int16_negative(self):
        """Test converting high uint16 to negative signed int16."""
        result = RegisterValue._to_signed_int16(0xFFCE)
        assert result == -50

    def test_to_signed_int16_max_negative(self):
        """Test converting to max negative signed int16."""
        result = RegisterValue._to_signed_int16(0x8000)
        assert result == -32768

    def test_to_signed_int16_zero(self):
        """Test converting zero."""
        result = RegisterValue._to_signed_int16(0x0000)
        assert result == 0


class TestRegisterValueImmutability:
    """Test that RegisterValue is immutable."""

    def test_cannot_modify_address(self):
        """Test that address cannot be modified."""
        value = RegisterValue(address=0x0100, raw_value=486)
        with pytest.raises(FrozenInstanceError):
            value.address = 0x0200

    def test_cannot_modify_raw_value(self):
        """Test that raw_value cannot be modified."""
        value = RegisterValue(address=0x0100, raw_value=486)
        with pytest.raises(FrozenInstanceError):
            value.raw_value = 500

    def test_cannot_modify_scale(self):
        """Test that scale cannot be modified."""
        value = RegisterValue(address=0x0100, raw_value=486, scale=0.1)
        with pytest.raises(FrozenInstanceError):
            value.scale = 0.2


class TestRegisterValueFormatting:
    """Test RegisterValue formatting methods."""

    def test_to_hex_uint16(self):
        """Test converting uint16 value to hex string."""
        value = RegisterValue(address=0x0100, raw_value=486)
        assert value.to_hex() == "0x01e6"

    def test_to_hex_max_value(self):
        """Test converting max uint16 to hex."""
        value = RegisterValue(address=0x0100, raw_value=0xFFFF)
        assert value.to_hex() == "0xffff"

    def test_str_representation(self):
        """Test string representation."""
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            scale=0.1,
        )
        str_repr = str(value)
        assert "0x0100" in str_repr
        assert "486" in str_repr
        assert "48.6" in str_repr

    def test_repr_representation(self):
        """Test developer representation."""
        value = RegisterValue(
            address=0x0100,
            raw_value=486,
            data_type=DataType.UINT16,
            scale=0.1,
        )
        repr_str = repr(value)
        assert "RegisterValue" in repr_str
        assert "0x0100" in repr_str
        assert "486" in repr_str
        assert "uint16" in repr_str


class TestRegisterValueEquality:
    """Test RegisterValue equality."""

    def test_equality_same_values(self):
        """Test that values with same data are equal."""
        value1 = RegisterValue(address=0x0100, raw_value=486)
        value2 = RegisterValue(address=0x0100, raw_value=486)
        assert value1 == value2

    def test_inequality_different_address(self):
        """Test that values with different addresses are not equal."""
        value1 = RegisterValue(address=0x0100, raw_value=486)
        value2 = RegisterValue(address=0x0200, raw_value=486)
        assert value1 != value2

    def test_inequality_different_raw_value(self):
        """Test that values with different raw values are not equal."""
        value1 = RegisterValue(address=0x0100, raw_value=486)
        value2 = RegisterValue(address=0x0100, raw_value=500)
        assert value1 != value2
