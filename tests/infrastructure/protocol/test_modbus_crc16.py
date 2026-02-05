"""Tests for ModbusCRC16 implementation.

These tests verify the CRC-16 implementation matches the original
coordinator behavior and Modbus RTU specification.
"""

import pytest
from custom_components.srne_inverter.infrastructure.protocol import ModbusCRC16


class TestModbusCRC16Calculation:
    """Test CRC-16 calculation correctness."""

    def test_calculate_deterministic(self):
        """Verify CRC calculation is deterministic."""
        crc = ModbusCRC16()
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])

        result1 = crc.calculate(data)
        result2 = crc.calculate(data)

        assert result1 == result2

    def test_calculate_returns_uint16(self):
        """Verify CRC result is valid 16-bit unsigned integer."""
        crc = ModbusCRC16()
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])

        result = crc.calculate(data)

        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    @pytest.mark.parametrize(
        "data,expected_crc",
        [
            # Known good values from coordinator algorithm
            (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01]), 0xF685),
            (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02]), 0xF7C5),
            (bytes([0x01, 0x06, 0x01, 0x00, 0x01, 0x2C]), 0x7B88),
        ],
    )
    def test_calculate_known_values(self, data, expected_crc):
        """Verify CRC against known good values from coordinator."""
        crc = ModbusCRC16()
        result = crc.calculate(data)
        assert result == expected_crc

    def test_calculate_empty_data(self):
        """Verify CRC for empty data returns initial value."""
        crc = ModbusCRC16()
        result = crc.calculate(b"")
        assert result == 0xFFFF

    def test_calculate_single_byte(self):
        """Verify CRC calculation for single byte."""
        crc = ModbusCRC16()
        result = crc.calculate(b"\x01")
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_calculate_different_data_different_crc(self):
        """Verify different data produces different CRC."""
        crc = ModbusCRC16()
        data1 = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        data2 = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02])

        crc1 = crc.calculate(data1)
        crc2 = crc.calculate(data2)

        assert crc1 != crc2

    def test_calculate_none_raises_error(self):
        """Verify None data raises ValueError."""
        crc = ModbusCRC16()
        with pytest.raises(ValueError, match="cannot be None"):
            crc.calculate(None)


class TestModbusCRC16Validation:
    """Test CRC validation helper."""

    def test_validate_correct_crc(self):
        """Verify validate returns True for correct CRC."""
        crc = ModbusCRC16()
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        expected = 0xF685

        assert crc.validate(data, expected) is True

    def test_validate_incorrect_crc(self):
        """Verify validate returns False for incorrect CRC."""
        crc = ModbusCRC16()
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        wrong_crc = 0x1234

        assert crc.validate(data, wrong_crc) is False

    def test_validate_multiple_checks(self):
        """Verify validate works for multiple different frames."""
        crc = ModbusCRC16()

        test_cases = [
            (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01]), 0xF685),
            (bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02]), 0xF7C5),
        ]

        for data, expected_crc in test_cases:
            assert crc.validate(data, expected_crc)


class TestModbusCRC16EdgeCases:
    """Test edge cases and boundary conditions."""

    def test_calculate_max_data_size(self):
        """Verify CRC calculation with large data."""
        crc = ModbusCRC16()
        # Modbus max frame is 256 bytes
        large_data = bytes(range(256))

        result = crc.calculate(large_data)
        assert isinstance(result, int)
        assert 0 <= result <= 0xFFFF

    def test_calculate_all_zeros(self):
        """Verify CRC for data with all zeros."""
        crc = ModbusCRC16()
        data = bytes([0x00] * 10)

        result = crc.calculate(data)
        assert isinstance(result, int)

    def test_calculate_all_ones(self):
        """Verify CRC for data with all 0xFF."""
        crc = ModbusCRC16()
        data = bytes([0xFF] * 10)

        result = crc.calculate(data)
        assert isinstance(result, int)


class TestModbusCRC16InterfaceCompliance:
    """Test that ModbusCRC16 properly implements ICRC interface."""

    def test_implements_icrc_interface(self):
        """Verify ModbusCRC16 implements ICRC."""
        from custom_components.srne_inverter.domain.interfaces import ICRC

        crc = ModbusCRC16()
        assert isinstance(crc, ICRC)

    def test_has_calculate_method(self):
        """Verify calculate method exists and is callable."""
        crc = ModbusCRC16()
        assert hasattr(crc, "calculate")
        assert callable(crc.calculate)

    def test_calculate_signature(self):
        """Verify calculate accepts bytes and returns int."""
        crc = ModbusCRC16()
        result = crc.calculate(b"\x01\x02\x03")
        assert isinstance(result, int)


class TestModbusCRC16Compatibility:
    """Test compatibility with original coordinator implementation."""

    def test_matches_coordinator_algorithm(self):
        """Verify algorithm matches original coordinator.ModbusProtocol.calculate_crc16."""
        # This is implicitly tested by known_values tests,
        # but explicitly documenting the requirement
        crc = ModbusCRC16()

        # Test case from original coordinator
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        result = crc.calculate(data)

        # This is the CRC that the original coordinator produces
        assert result == 0xF685

    def test_polynomial_0xa001(self):
        """Document that implementation uses polynomial 0xA001."""
        # This is tested indirectly through known values,
        # but documenting the requirement explicitly
        crc = ModbusCRC16()

        # Known value that depends on 0xA001 polynomial
        result = crc.calculate(bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01]))
        assert result == 0xF685  # Would be different with different polynomial


class TestModbusCRC16Reusability:
    """Test that CRC calculator can be reused."""

    def test_multiple_calculations(self):
        """Verify calculator can be used multiple times."""
        crc = ModbusCRC16()

        data1 = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])
        data2 = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02])

        result1 = crc.calculate(data1)
        result2 = crc.calculate(data2)

        # Should get same results as before
        assert result1 == 0xF685
        assert result2 == 0xF7C5

    def test_no_state_corruption(self):
        """Verify calculations don't affect each other."""
        crc = ModbusCRC16()
        data = bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01])

        result1 = crc.calculate(data)
        result2 = crc.calculate(data)
        result3 = crc.calculate(data)

        assert result1 == result2 == result3
