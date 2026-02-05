"""Tests for value codec strategies."""

import pytest

from custom_components.srne_inverter.domain.strategies.value_codec_strategy import (
    CodecFactory,
    UInt16Codec,
    Int16Codec,
    BoolCodec,
)


class TestUInt16Codec:
    """Test unsigned 16-bit codec."""

    def test_decode_no_scale_no_offset(self):
        """Test basic decode."""
        codec = UInt16Codec()
        assert codec.decode(2500) == 2500

    def test_decode_with_scale(self):
        """Test decode with scaling."""
        codec = UInt16Codec()
        assert codec.decode(2500, scale=0.1) == 250.0

    def test_decode_with_offset(self):
        """Test decode with offset."""
        codec = UInt16Codec()
        # (2400 + 100) * 0.1 = 250.0
        assert codec.decode(2400, scale=0.1, offset=100) == 250.0

    def test_encode_basic(self):
        """Test basic encode."""
        codec = UInt16Codec()
        assert codec.encode(250.0, scale=0.1) == 2500

    def test_roundtrip(self):
        """Test encode-decode roundtrip."""
        codec = UInt16Codec()
        original = 12345
        decoded = codec.decode(original, scale=0.1, offset=10)
        encoded = codec.encode(decoded, scale=0.1, offset=10)
        assert encoded == original


class TestInt16Codec:
    """Test signed 16-bit codec."""

    def test_decode_positive(self):
        """Test decode positive value."""
        codec = Int16Codec()
        assert codec.decode(100, scale=0.1) == 10.0

    def test_decode_negative(self):
        """Test decode negative value (two's complement)."""
        codec = Int16Codec()
        # 0xFFEC = -20 in int16
        assert codec.decode(0xFFEC, scale=0.1) == -2.0

    def test_encode_positive(self):
        """Test encode positive value."""
        codec = Int16Codec()
        assert codec.encode(10.0, scale=0.1) == 100

    def test_encode_negative(self):
        """Test encode negative value."""
        codec = Int16Codec()
        # -2.0 with scale 0.1 = -20 = 0xFFEC
        assert codec.encode(-2.0, scale=0.1) == 0xFFEC

    def test_roundtrip_negative(self):
        """Test roundtrip with negative value."""
        codec = Int16Codec()
        original = 0xFFF6  # -10 in int16
        decoded = codec.decode(original, scale=1.0)
        encoded = codec.encode(decoded, scale=1.0)
        assert encoded == original


class TestBoolCodec:
    """Test boolean codec."""

    def test_decode_zero_is_false(self):
        """Test zero decodes to False."""
        codec = BoolCodec()
        assert codec.decode(0) is False

    def test_decode_nonzero_is_true(self):
        """Test non-zero decodes to True."""
        codec = BoolCodec()
        assert codec.decode(1) is True
        assert codec.decode(255) is True
        assert codec.decode(0xFFFF) is True

    def test_encode_false_is_zero(self):
        """Test False encodes to 0."""
        codec = BoolCodec()
        assert codec.encode(False) == 0

    def test_encode_true_is_one(self):
        """Test True encodes to 1."""
        codec = BoolCodec()
        assert codec.encode(True) == 1

    def test_roundtrip(self):
        """Test encode-decode roundtrip."""
        codec = BoolCodec()
        assert codec.decode(codec.encode(True)) is True
        assert codec.decode(codec.encode(False)) is False


class TestCodecFactory:
    """Test codec factory."""

    def test_get_uint16_codec(self):
        """Test getting uint16 codec."""
        codec = CodecFactory.get_codec("uint16")
        assert isinstance(codec, UInt16Codec)

    def test_get_int16_codec(self):
        """Test getting int16 codec."""
        codec = CodecFactory.get_codec("int16")
        assert isinstance(codec, Int16Codec)

    def test_get_bool_codec(self):
        """Test getting bool codec."""
        codec = CodecFactory.get_codec("bool")
        assert isinstance(codec, BoolCodec)

    def test_case_insensitive(self):
        """Test factory is case-insensitive."""
        assert isinstance(CodecFactory.get_codec("UINT16"), UInt16Codec)
        assert isinstance(CodecFactory.get_codec("Int16"), Int16Codec)

    def test_unknown_type_raises_error(self):
        """Test unknown type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown data type"):
            CodecFactory.get_codec("unknown")

    def test_get_supported_types(self):
        """Test getting supported types."""
        types = CodecFactory.get_supported_types()
        assert "uint16" in types
        assert "int16" in types
        assert "bool" in types

    def test_register_custom_codec(self):
        """Test registering custom codec."""
        from custom_components.srne_inverter.domain.strategies.value_codec_strategy import (
            ValueCodecStrategy,
        )

        class CustomCodec(ValueCodecStrategy):
            def decode(self, raw_value, scale=1.0, offset=0):
                return raw_value * 2

            def encode(self, display_value, scale=1.0, offset=0):
                return int(display_value / 2)

        CodecFactory.register_codec("custom", CustomCodec())
        codec = CodecFactory.get_codec("custom")
        assert codec.decode(100) == 200
