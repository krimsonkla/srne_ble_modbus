"""Tests for WriteRegisterUseCase.

Phase 2 Week 6: Application Layer Testing (Day 27)
"""

import pytest
from unittest.mock import AsyncMock, Mock

from custom_components.srne_inverter.application.use_cases.write_register_use_case import (
    WriteRegisterUseCase,
    WriteRegisterResult,
)


class TestWriteRegisterUseCase:
    """Test suite for WriteRegisterUseCase."""

    @pytest.fixture
    def mock_transport(self):
        """Create mock transport."""
        mock = Mock()
        mock.send = AsyncMock()
        return mock

    @pytest.fixture
    def mock_protocol(self):
        """Create mock protocol."""
        mock = Mock()
        mock.build_write_command = Mock(return_value=b"\x01\x06\x01\x00\x01\x2c")
        mock.decode_response = Mock()
        return mock

    @pytest.fixture
    def use_case(self, mock_transport, mock_protocol):
        """Create use case with mocked dependencies."""
        return WriteRegisterUseCase(mock_transport, mock_protocol)

    @pytest.mark.asyncio
    async def test_execute_successful_write(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test successful register write."""
        # Arrange
        mock_protocol.decode_response.return_value = {
            "register": 0x0100,
            "value": 5000,
        }

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is True
        assert result.error == ""
        assert result.register == 0x0100
        assert result.value == 5000
        mock_transport.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_invalid_register_raises(self, use_case):
        """Test that invalid register raises ValueError."""
        with pytest.raises(ValueError, match="Invalid register address"):
            await use_case.execute(register=0x10000, value=100)  # Too high

    @pytest.mark.asyncio
    async def test_execute_invalid_value_raises(self, use_case):
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid register value"):
            await use_case.execute(register=0x0100, value=70000)  # Too high

    @pytest.mark.asyncio
    async def test_execute_protected_register_with_password(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test writing protected register with password authentication."""
        # Arrange
        mock_protocol.decode_response.side_effect = [
            {"register": 0xE203, "value": 4321},  # Auth success
            {"register": 0xE003, "value": 5000},  # Write success
        ]

        # Act
        result = await use_case.execute(
            register=0xE003,  # Protected range
            value=5000,
            password=4321,
        )

        # Assert
        assert result.success is True
        assert mock_transport.send.call_count == 2  # Auth + Write

    @pytest.mark.asyncio
    async def test_execute_protected_register_auth_failure(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test authentication failure for protected register."""
        # Arrange
        mock_protocol.decode_response.return_value = {
            "error": 0x05  # Incorrect password
        }

        # Act
        result = await use_case.execute(
            register=0xE003,
            value=5000,
            password=1234,  # Wrong password
        )

        # Assert
        assert result.success is False
        assert "Authentication failed" in result.error
        assert result.error_code == 0x05

    @pytest.mark.asyncio
    async def test_execute_write_error_permission_denied(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test permission denied error (0x0B)."""
        # Arrange
        mock_protocol.decode_response.return_value = {"error": 0x0B}

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is False
        assert "Permission denied" in result.error
        assert result.error_code == 0x0B

    @pytest.mark.asyncio
    async def test_execute_write_error_illegal_address(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test illegal data address error (0x02)."""
        # Arrange
        mock_protocol.decode_response.return_value = {"error": 0x02}

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is False
        assert "Illegal data address" in result.error
        assert result.error_code == 0x02

    @pytest.mark.asyncio
    async def test_execute_write_error_value_out_of_range(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test value out of range error (0x03)."""
        # Arrange
        mock_protocol.decode_response.return_value = {"error": 0x03}

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is False
        assert "out of range" in result.error
        assert result.error_code == 0x03

    @pytest.mark.asyncio
    async def test_execute_write_error_read_only(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test read-only register error (0x07)."""
        # Arrange
        mock_protocol.decode_response.return_value = {"error": 0x07}

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is False
        assert "Read-only" in result.error
        assert result.error_code == 0x07

    @pytest.mark.asyncio
    async def test_execute_communication_timeout(
        self, use_case, mock_transport, mock_protocol
    ):
        """Test communication timeout."""
        # Arrange
        mock_transport.send.side_effect = TimeoutError("Timeout")

        # Act
        result = await use_case.execute(register=0x0100, value=5000)

        # Assert
        assert result.success is False
        assert "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_is_protected_register(self, use_case):
        """Test protected register detection."""
        assert use_case._is_protected_register(0xE000) is True
        assert use_case._is_protected_register(0xE0FF) is True
        assert use_case._is_protected_register(0xE080) is True
        assert use_case._is_protected_register(0x0100) is False
        assert use_case._is_protected_register(0xE100) is False


class TestWriteRegisterResult:
    """Test WriteRegisterResult dataclass."""

    def test_create_successful_result(self):
        """Test creating successful result."""
        result = WriteRegisterResult(
            success=True,
            register=0x0100,
            value=5000,
        )

        assert result.success is True
        assert result.error == ""
        assert result.error_code is None
        assert result.register == 0x0100
        assert result.value == 5000

    def test_create_failed_result(self):
        """Test creating failed result."""
        result = WriteRegisterResult(
            success=False,
            error="Permission denied",
            error_code=0x0B,
            register=0x0100,
            value=5000,
        )

        assert result.success is False
        assert result.error == "Permission denied"
        assert result.error_code == 0x0B
