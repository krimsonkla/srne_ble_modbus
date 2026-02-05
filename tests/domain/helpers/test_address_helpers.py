"""Tests for address helper functions."""

import pytest

from custom_components.srne_inverter.domain.helpers.address_helpers import (
    address_in_range,
    calculate_register_count,
    format_address,
    parse_address,
)


class TestParseAddress:
    """Test parse_address function."""

    def test_parse_integer_address(self):
        """Test parsing integer address."""
        assert parse_address(4660) == 4660
        assert parse_address(0x1234) == 4660
        assert parse_address(0) == 0
        assert parse_address(65535) == 65535

    def test_parse_hex_string_with_prefix(self):
        """Test parsing hex string with 0x prefix."""
        assert parse_address("0x1234") == 4660
        assert parse_address("0X1234") == 4660
        assert parse_address("0x0000") == 0
        assert parse_address("0xFFFF") == 65535

    def test_parse_hex_string_without_prefix(self):
        """Test parsing hex string without prefix."""
        assert parse_address("1234") == 4660
        assert parse_address("ABCD") == 43981
        assert parse_address("0000") == 0
        assert parse_address("FFFF") == 65535

    def test_parse_decimal_string(self):
        """Test parsing decimal string (fallback)."""
        # When hex parsing fails, falls back to decimal
        assert parse_address("12") == 18  # Hex interpretation
        # Pure decimal numbers that cannot be hex
        # Note: All numeric strings are first tried as hex

    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        assert parse_address("  0x1234  ") == 4660
        assert parse_address("  1234  ") == 4660

    def test_parse_invalid_string_raises(self):
        """Test parsing invalid string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("invalid")

        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("0xGGGG")

        with pytest.raises(ValueError, match="Invalid address format"):
            parse_address("")

    def test_parse_invalid_type_raises(self):
        """Test parsing invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Address must be str or int"):
            parse_address(None)

        with pytest.raises(ValueError, match="Address must be str or int"):
            parse_address(12.5)

        with pytest.raises(ValueError, match="Address must be str or int"):
            parse_address([])


class TestFormatAddress:
    """Test format_address function."""

    def test_format_with_prefix(self):
        """Test formatting with 0x prefix."""
        assert format_address(4660) == "0x1234"
        assert format_address(0) == "0x0000"
        assert format_address(65535) == "0xFFFF"
        assert format_address(255) == "0x00FF"

    def test_format_without_prefix(self):
        """Test formatting without prefix."""
        assert format_address(4660, prefix=False) == "1234"
        assert format_address(0, prefix=False) == "0000"
        assert format_address(65535, prefix=False) == "FFFF"

    def test_format_default_prefix(self):
        """Test default prefix is True."""
        assert format_address(4660) == "0x1234"

    def test_format_preserves_4_digits(self):
        """Test formatting always uses 4 hex digits."""
        assert format_address(1) == "0x0001"
        assert format_address(15) == "0x000F"
        assert format_address(255) == "0x00FF"
        assert format_address(4095) == "0x0FFF"


class TestAddressInRange:
    """Test address_in_range function."""

    def test_address_in_range_inclusive(self):
        """Test address within range (inclusive)."""
        assert address_in_range(0x1234, 0x1000, 0x2000)
        assert address_in_range(0x1000, 0x1000, 0x2000)  # Start boundary
        assert address_in_range(0x2000, 0x1000, 0x2000)  # End boundary

    def test_address_in_range_exclusive(self):
        """Test address within range (exclusive end)."""
        assert address_in_range(0x1234, 0x1000, 0x2000, inclusive=False)
        assert address_in_range(0x1000, 0x1000, 0x2000, inclusive=False)
        assert not address_in_range(0x2000, 0x1000, 0x2000, inclusive=False)

    def test_address_out_of_range_below(self):
        """Test address below range."""
        assert not address_in_range(0x0FFF, 0x1000, 0x2000)
        assert not address_in_range(0, 0x1000, 0x2000)

    def test_address_out_of_range_above(self):
        """Test address above range."""
        assert not address_in_range(0x2001, 0x1000, 0x2000)
        assert not address_in_range(0xFFFF, 0x1000, 0x2000)

    def test_single_address_range(self):
        """Test range with single address."""
        assert address_in_range(0x1000, 0x1000, 0x1000)
        assert not address_in_range(0x1001, 0x1000, 0x1000)


class TestCalculateRegisterCount:
    """Test calculate_register_count function."""

    def test_calculate_count_basic(self):
        """Test basic register count calculation."""
        assert calculate_register_count(0x1000, 0x1009) == 10
        assert calculate_register_count(0x0000, 0x0000) == 1
        assert calculate_register_count(0x1000, 0x1000) == 1

    def test_calculate_count_large_range(self):
        """Test large range calculation."""
        assert calculate_register_count(0x0000, 0x00FF) == 256
        assert calculate_register_count(0x0000, 0xFFFF) == 65536

    def test_calculate_count_typical_batch(self):
        """Test typical batch sizes."""
        assert calculate_register_count(0x1000, 0x101D) == 30  # 30 registers
        assert calculate_register_count(0x3000, 0x3063) == 100  # 100 registers


class TestIntegration:
    """Integration tests for address helpers."""

    def test_parse_and_format_roundtrip(self):
        """Test parsing and formatting roundtrip."""
        original = 0x1234
        formatted = format_address(original)
        parsed = parse_address(formatted)
        assert parsed == original

    def test_parse_format_various_inputs(self):
        """Test parse and format with various inputs."""
        test_cases = [
            ("0x0000", 0),
            ("0x1234", 4660),
            ("0xFFFF", 65535),
            ("ABCD", 43981),
        ]

        for input_str, expected_int in test_cases:
            parsed = parse_address(input_str)
            assert parsed == expected_int

            formatted = format_address(parsed)
            reparsed = parse_address(formatted)
            assert reparsed == expected_int

    def test_range_with_parsed_addresses(self):
        """Test range checking with parsed addresses."""
        start = parse_address("0x1000")
        end = parse_address("0x2000")
        test = parse_address("0x1234")

        assert address_in_range(test, start, end)

    def test_count_with_parsed_addresses(self):
        """Test count calculation with parsed addresses."""
        start = parse_address("0x1000")
        end = parse_address("0x1009")

        count = calculate_register_count(start, end)
        assert count == 10
