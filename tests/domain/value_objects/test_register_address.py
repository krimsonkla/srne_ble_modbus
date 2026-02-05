"""Tests for RegisterAddress value object."""

import pytest
from dataclasses import FrozenInstanceError
from custom_components.srne_inverter.domain.value_objects import RegisterAddress


class TestRegisterAddressCreation:
    """Test RegisterAddress creation and validation."""

    def test_create_valid_address(self):
        """Test creating RegisterAddress with valid values."""
        addr = RegisterAddress(0x0100)
        assert addr.value == 0x0100

    def test_create_min_address(self):
        """Test creating RegisterAddress with minimum value."""
        addr = RegisterAddress(0x0000)
        assert addr.value == 0x0000

    def test_create_max_address(self):
        """Test creating RegisterAddress with maximum value."""
        addr = RegisterAddress(0xFFFF)
        assert addr.value == 0xFFFF

    def test_create_with_negative_raises_error(self):
        """Test that negative address raises ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            RegisterAddress(-1)

    def test_create_with_too_large_raises_error(self):
        """Test that address > 0xFFFF raises ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            RegisterAddress(0x10000)

    def test_create_with_non_int_raises_error(self):
        """Test that non-integer raises TypeError."""
        with pytest.raises(TypeError, match="must be int"):
            RegisterAddress("0x0100")


class TestRegisterAddressImmutability:
    """Test that RegisterAddress is immutable."""

    def test_cannot_modify_value(self):
        """Test that value cannot be modified after creation."""
        addr = RegisterAddress(0x0100)
        with pytest.raises(FrozenInstanceError):
            addr.value = 0x0200  # Should raise error

    def test_equality_based_on_value(self):
        """Test that equality is based on value, not identity."""
        addr1 = RegisterAddress(0x0100)
        addr2 = RegisterAddress(0x0100)
        assert addr1 == addr2
        assert addr1 is not addr2  # Different objects

    def test_can_use_as_dict_key(self):
        """Test that RegisterAddress can be used as dictionary key."""
        addr1 = RegisterAddress(0x0100)
        addr2 = RegisterAddress(0x0100)
        data = {addr1: "battery_voltage"}
        assert data[addr2] == "battery_voltage"  # Same key


class TestRegisterAddressConversion:
    """Test RegisterAddress conversion methods."""

    def test_to_bytes(self):
        """Test converting address to big-endian bytes."""
        addr = RegisterAddress(0x0100)
        assert addr.to_bytes() == b"\x01\x00"

    def test_to_bytes_max_value(self):
        """Test converting max address to bytes."""
        addr = RegisterAddress(0xFFFF)
        assert addr.to_bytes() == b"\xff\xff"

    def test_to_hex(self):
        """Test converting address to hex string."""
        addr = RegisterAddress(0x0100)
        assert addr.to_hex() == "0x0100"

    def test_to_hex_with_padding(self):
        """Test hex string has proper padding."""
        addr = RegisterAddress(0x00FF)
        assert addr.to_hex() == "0x00FF"

    def test_int_cast(self):
        """Test casting RegisterAddress to int."""
        addr = RegisterAddress(0x0100)
        assert int(addr) == 256

    def test_str_representation(self):
        """Test string representation."""
        addr = RegisterAddress(0x0100)
        assert "0x0100" in str(addr)

    def test_repr_representation(self):
        """Test developer representation."""
        addr = RegisterAddress(0x0100)
        repr_str = repr(addr)
        assert "RegisterAddress" in repr_str
        assert "0x0100" in repr_str


class TestRegisterAddressArithmetic:
    """Test RegisterAddress arithmetic operations."""

    def test_add_offset(self):
        """Test adding offset to address."""
        addr = RegisterAddress(0x0100)
        next_addr = addr + 1
        assert next_addr.value == 0x0101
        assert isinstance(next_addr, RegisterAddress)

    def test_subtract_offset(self):
        """Test subtracting offset from address."""
        addr = RegisterAddress(0x0100)
        prev_addr = addr - 1
        assert prev_addr.value == 0x00FF
        assert isinstance(prev_addr, RegisterAddress)

    def test_add_overflow_raises_error(self):
        """Test that adding beyond max raises ValueError."""
        addr = RegisterAddress(0xFFFF)
        with pytest.raises(ValueError):
            _ = addr + 1

    def test_subtract_underflow_raises_error(self):
        """Test that subtracting below min raises ValueError."""
        addr = RegisterAddress(0x0000)
        with pytest.raises(ValueError):
            _ = addr - 1


class TestRegisterAddressFactoryMethods:
    """Test RegisterAddress factory methods."""

    def test_from_bytes(self):
        """Test creating RegisterAddress from bytes."""
        addr = RegisterAddress.from_bytes(b"\x01\x00")
        assert addr.value == 0x0100

    def test_from_bytes_wrong_length_raises_error(self):
        """Test that wrong byte length raises ValueError."""
        with pytest.raises(ValueError, match="Expected 2 bytes"):
            RegisterAddress.from_bytes(b"\x01")

    def test_from_hex_with_prefix(self):
        """Test creating RegisterAddress from hex string with 0x prefix."""
        addr = RegisterAddress.from_hex("0x0100")
        assert addr.value == 0x0100

    def test_from_hex_without_prefix(self):
        """Test creating RegisterAddress from hex string without prefix."""
        addr = RegisterAddress.from_hex("0100")
        assert addr.value == 0x0100

    def test_from_hex_uppercase_prefix(self):
        """Test creating RegisterAddress with uppercase 0X prefix."""
        addr = RegisterAddress.from_hex("0X0100")
        assert addr.value == 0x0100


class TestRegisterAddressComparison:
    """Test RegisterAddress comparison operations."""

    def test_less_than(self):
        """Test less than comparison."""
        addr1 = RegisterAddress(0x0100)
        addr2 = RegisterAddress(0x0200)
        assert addr1 < addr2

    def test_greater_than(self):
        """Test greater than comparison."""
        addr1 = RegisterAddress(0x0200)
        addr2 = RegisterAddress(0x0100)
        assert addr1 > addr2

    def test_equality(self):
        """Test equality comparison."""
        addr1 = RegisterAddress(0x0100)
        addr2 = RegisterAddress(0x0100)
        assert addr1 == addr2

    def test_sorting(self):
        """Test that addresses can be sorted."""
        addresses = [
            RegisterAddress(0x0300),
            RegisterAddress(0x0100),
            RegisterAddress(0x0200),
        ]
        sorted_addrs = sorted(addresses)
        assert sorted_addrs[0].value == 0x0100
        assert sorted_addrs[1].value == 0x0200
        assert sorted_addrs[2].value == 0x0300
