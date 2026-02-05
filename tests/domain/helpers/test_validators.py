"""Tests for validation helper functions."""

import pytest

from custom_components.srne_inverter.domain.helpers.validators import (
    ValidationError,
    validate_not_none,
    validate_range,
    validate_register_address,
    validate_register_value,
    validate_type,
)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_is_value_error(self):
        """Test ValidationError is subclass of ValueError."""
        assert issubclass(ValidationError, ValueError)

    def test_can_raise_and_catch_as_value_error(self):
        """Test ValidationError can be caught as ValueError."""
        with pytest.raises(ValueError):
            raise ValidationError("test error")

    def test_error_message(self):
        """Test error message is preserved."""
        with pytest.raises(ValidationError, match="custom message"):
            raise ValidationError("custom message")


class TestValidateRegisterAddress:
    """Test validate_register_address function."""

    def test_valid_addresses(self):
        """Test validating valid addresses."""
        assert validate_register_address(0) == 0
        assert validate_register_address(0x0000) == 0
        assert validate_register_address(0x1234) == 4660
        assert validate_register_address(0xFFFF) == 65535
        assert validate_register_address(32768) == 32768

    def test_min_address(self):
        """Test minimum address boundary."""
        assert validate_register_address(0x0000) == 0

    def test_max_address(self):
        """Test maximum address boundary."""
        assert validate_register_address(0xFFFF) == 65535

    def test_negative_address_raises(self):
        """Test negative address raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid address"):
            validate_register_address(-1)

    def test_too_large_address_raises(self):
        """Test address > 0xFFFF raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid address.*0x10000"):
            validate_register_address(0x10000)

        with pytest.raises(ValidationError, match="Invalid address"):
            validate_register_address(100000)

    def test_non_integer_raises(self):
        """Test non-integer address raises ValidationError."""
        with pytest.raises(ValidationError, match="must be integer, got str"):
            validate_register_address("1234")

        with pytest.raises(ValidationError, match="must be integer, got float"):
            validate_register_address(12.5)

        with pytest.raises(ValidationError, match="must be integer, got NoneType"):
            validate_register_address(None)

    def test_custom_name_in_error(self):
        """Test custom parameter name appears in error message."""
        with pytest.raises(ValidationError, match="Invalid register"):
            validate_register_address(0x10000, name="register")

        with pytest.raises(ValidationError, match="Invalid start_address"):
            validate_register_address(-1, name="start_address")


class TestValidateRegisterValue:
    """Test validate_register_value function."""

    def test_valid_values(self):
        """Test validating valid values."""
        assert validate_register_value(0) == 0
        assert validate_register_value(1000) == 1000
        assert validate_register_value(32768) == 32768
        assert validate_register_value(65535) == 65535

    def test_min_value(self):
        """Test minimum value boundary."""
        assert validate_register_value(0) == 0

    def test_max_value(self):
        """Test maximum value boundary."""
        assert validate_register_value(65535) == 65535

    def test_negative_value_raises(self):
        """Test negative value raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid value.*-1"):
            validate_register_value(-1)

    def test_too_large_value_raises(self):
        """Test value > 65535 raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid value.*65536"):
            validate_register_value(65536)

        with pytest.raises(ValidationError, match="Invalid value.*100000"):
            validate_register_value(100000)

    def test_non_integer_raises(self):
        """Test non-integer value raises ValidationError."""
        with pytest.raises(ValidationError, match="must be integer, got str"):
            validate_register_value("1000")

        with pytest.raises(ValidationError, match="must be integer, got float"):
            validate_register_value(100.5)

    def test_custom_name_in_error(self):
        """Test custom parameter name appears in error message."""
        with pytest.raises(ValidationError, match="Invalid new_value"):
            validate_register_value(70000, name="new_value")


class TestValidateRange:
    """Test validate_range function."""

    def test_value_in_range(self):
        """Test value within range passes."""
        assert validate_range(50, 0, 100) == 50
        assert validate_range(0, 0, 100) == 0
        assert validate_range(100, 0, 100) == 100

    def test_value_at_boundaries(self):
        """Test values at range boundaries pass."""
        assert validate_range(0, 0, 10) == 0
        assert validate_range(10, 0, 10) == 10

    def test_float_values(self):
        """Test range validation with floats."""
        assert validate_range(5.5, 0.0, 10.0) == 5.5
        assert validate_range(0.0, 0.0, 10.0) == 0.0
        assert validate_range(10.0, 0.0, 10.0) == 10.0

    def test_negative_ranges(self):
        """Test range validation with negative values."""
        assert validate_range(-5, -10, 0) == -5
        assert validate_range(-10, -10, 10) == -10
        assert validate_range(0, -10, 10) == 0

    def test_value_below_min_raises(self):
        """Test value below minimum raises ValidationError."""
        with pytest.raises(ValidationError, match="value -1 out of range \\[0, 100\\]"):
            validate_range(-1, 0, 100)

    def test_value_above_max_raises(self):
        """Test value above maximum raises ValidationError."""
        with pytest.raises(
            ValidationError, match="value 101 out of range \\[0, 100\\]"
        ):
            validate_range(101, 0, 100)

    def test_custom_name_in_error(self):
        """Test custom parameter name appears in error message."""
        with pytest.raises(ValidationError, match="temperature 150 out of range"):
            validate_range(150, 0, 100, name="temperature")


class TestValidateNotNone:
    """Test validate_not_none function."""

    def test_non_none_values_pass(self):
        """Test non-None values pass validation."""
        assert validate_not_none(0) == 0
        assert validate_not_none("") == ""
        assert validate_not_none(False) is False
        assert validate_not_none([]) == []
        assert validate_not_none({}) == {}

    def test_none_raises(self):
        """Test None raises ValidationError."""
        with pytest.raises(ValidationError, match="value cannot be None"):
            validate_not_none(None)

    def test_custom_name_in_error(self):
        """Test custom parameter name appears in error message."""
        with pytest.raises(ValidationError, match="config cannot be None"):
            validate_not_none(None, name="config")


class TestValidateType:
    """Test validate_type function."""

    def test_correct_type_passes(self):
        """Test correct type passes validation."""
        assert validate_type("hello", str) == "hello"
        assert validate_type(123, int) == 123
        assert validate_type(12.5, float) == 12.5
        assert validate_type(True, bool) is True
        assert validate_type([], list) == []
        assert validate_type({}, dict) == {}

    def test_wrong_type_raises(self):
        """Test wrong type raises ValidationError."""
        with pytest.raises(ValidationError, match="value must be str, got int"):
            validate_type(123, str)

        with pytest.raises(ValidationError, match="value must be int, got str"):
            validate_type("123", int)

        with pytest.raises(ValidationError, match="value must be list, got dict"):
            validate_type({}, list)

    def test_none_type_raises(self):
        """Test None raises ValidationError for non-optional types."""
        with pytest.raises(ValidationError, match="value must be str, got NoneType"):
            validate_type(None, str)

    def test_custom_name_in_error(self):
        """Test custom parameter name appears in error message."""
        with pytest.raises(ValidationError, match="config must be dict, got str"):
            validate_type("not a dict", dict, name="config")

    def test_subclass_passes(self):
        """Test subclass instances pass validation."""
        # bool is subclass of int
        assert validate_type(True, int) is True
        assert validate_type(False, int) is False


class TestIntegration:
    """Integration tests for validators."""

    def test_chaining_validators(self):
        """Test chaining multiple validators."""

        def validate_temperature(value: int) -> int:
            """Validate temperature sensor value."""
            validate_type(value, int, "temperature")
            validate_register_value(value, "temperature")
            validate_range(value, 0, 100, "temperature")
            return value

        assert validate_temperature(50) == 50

        with pytest.raises(ValidationError, match="temperature must be int"):
            validate_temperature("50")

        with pytest.raises(ValidationError, match="temperature.*out of range"):
            validate_temperature(150)

    def test_validators_preserve_type(self):
        """Test validators return the same type."""
        # Integer validation
        result = validate_register_address(0x1234)
        assert isinstance(result, int)
        assert result == 4660

        # Float validation
        result = validate_range(5.5, 0.0, 10.0)
        assert isinstance(result, float)
        assert result == 5.5

    def test_validation_error_backward_compatibility(self):
        """Test ValidationError is compatible with ValueError catching."""

        def old_style_validation(value: int):
            """Old code that catches ValueError."""
            try:
                validate_register_address(value)
            except ValueError:
                return "caught as ValueError"

        assert old_style_validation(0x10000) == "caught as ValueError"
