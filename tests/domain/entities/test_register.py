"""Tests for Register entity."""

import pytest
from custom_components.srne_inverter.domain.entities import Register
from custom_components.srne_inverter.domain.value_objects import RegisterAddress
from custom_components.srne_inverter.domain.value_objects.register_value import DataType


class TestRegisterCreation:
    """Test Register entity creation."""

    def test_create_basic_register(self):
        """Test creating register with minimal parameters."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
        )
        assert register.name == "battery_voltage"
        assert register.address.value == 0x0100
        assert register.data_type == DataType.UINT16
        assert register.scale == 1.0
        assert register.read_only is True

    def test_create_register_with_scale(self):
        """Test creating register with scale factor."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            scale=0.1,
            unit="V",
        )
        assert register.scale == 0.1
        assert register.unit == "V"

    def test_create_writable_register(self):
        """Test creating writable register."""
        register = Register(
            address=RegisterAddress(0x0200),
            name="battery_charge_current",
            read_only=False,
            min_value=0.0,
            max_value=100.0,
        )
        assert register.read_only is False
        assert register.min_value == 0.0
        assert register.max_value == 100.0


class TestRegisterDecoding:
    """Test Register value decoding."""

    def test_decode_uint16_value(self):
        """Test decoding unsigned int16 value."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            scale=0.1,
        )
        value = register.decode_value(486)
        assert value.decoded_value == pytest.approx(48.6)

    def test_decode_int16_negative_value(self):
        """Test decoding negative signed int16 value."""
        register = Register(
            address=RegisterAddress(0x0101),
            name="battery_current",
            data_type=DataType.INT16,
            scale=0.01,
        )
        value = register.decode_value(0xFE0C)  # -500
        assert value.decoded_value == pytest.approx(-5.0)

    def test_decode_with_offset(self):
        """Test decoding with offset."""
        register = Register(
            address=RegisterAddress(0x0200),
            name="temperature",
            data_type=DataType.INT16,
            offset=-40,
        )
        value = register.decode_value(65)
        assert value.decoded_value == 25.0  # 65 - 40


class TestRegisterEncoding:
    """Test Register value encoding."""

    def test_encode_uint16_value(self):
        """Test encoding unsigned int16 value."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            scale=0.1,
            read_only=False,
            min_value=40.0,
            max_value=60.0,
        )
        raw = register.encode_value(48.6)
        assert raw == 486

    def test_encode_read_only_raises_error(self):
        """Test that encoding read-only register raises error."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            read_only=True,
        )
        with pytest.raises(ValueError, match="read-only"):
            register.encode_value(48.6)

    def test_encode_out_of_range_raises_error(self):
        """Test that encoding out-of-range value raises error."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            read_only=False,
            min_value=40.0,
            max_value=60.0,
        )
        with pytest.raises(ValueError, match="out of valid range"):
            register.encode_value(80.0)


class TestRegisterValidation:
    """Test Register value validation."""

    def test_is_valid_value_within_range(self):
        """Test that value within range is valid."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            min_value=40.0,
            max_value=60.0,
        )
        assert register.is_valid_value(48.6)
        assert register.is_valid_value(40.0)
        assert register.is_valid_value(60.0)

    def test_is_valid_value_out_of_range(self):
        """Test that value outside range is invalid."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            min_value=40.0,
            max_value=60.0,
        )
        assert not register.is_valid_value(39.9)
        assert not register.is_valid_value(60.1)

    def test_is_valid_value_no_limits(self):
        """Test validation with no limits always passes."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
        )
        assert register.is_valid_value(-1000.0)
        assert register.is_valid_value(1000.0)


class TestRegisterSerialization:
    """Test Register serialization."""

    def test_to_dict(self):
        """Test converting register to dictionary."""
        register = Register(
            address=RegisterAddress(0x0100),
            name="battery_voltage",
            scale=0.1,
            unit="V",
            description="Battery voltage",
        )
        data = register.to_dict()
        assert data["address"] == 0x0100
        assert data["name"] == "battery_voltage"
        assert data["scale"] == 0.1
        assert data["unit"] == "V"

    def test_from_dict(self):
        """Test creating register from dictionary."""
        data = {
            "address": 0x0100,
            "name": "battery_voltage",
            "data_type": "uint16",
            "scale": 0.1,
            "unit": "V",
        }
        register = Register.from_dict(data)
        assert register.address.value == 0x0100
        assert register.name == "battery_voltage"
        assert register.scale == 0.1


class TestRegisterEquality:
    """Test Register equality (entity identity)."""

    def test_equality_same_address(self):
        """Test that registers with same address are equal."""
        reg1 = Register(RegisterAddress(0x0100), "battery_voltage")
        reg2 = Register(RegisterAddress(0x0100), "different_name")
        assert reg1 == reg2  # Same address = same entity

    def test_inequality_different_address(self):
        """Test that registers with different addresses are not equal."""
        reg1 = Register(RegisterAddress(0x0100), "battery_voltage")
        reg2 = Register(RegisterAddress(0x0101), "battery_voltage")
        assert reg1 != reg2

    def test_can_use_as_dict_key(self):
        """Test that registers can be used as dictionary keys."""
        reg1 = Register(RegisterAddress(0x0100), "battery_voltage")
        reg2 = Register(RegisterAddress(0x0100), "battery_voltage")
        data = {reg1: "value1"}
        assert data[reg2] == "value1"  # Same key
