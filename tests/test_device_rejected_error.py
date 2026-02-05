"""Test for DeviceRejectedCommandError handling.

This test verifies that the custom exception is properly handled
by the error handler decorator without logging a stack trace.
"""

import logging
import pytest
from unittest.mock import MagicMock

from custom_components.srne_inverter.domain.exceptions import DeviceRejectedCommandError
from custom_components.srne_inverter.infrastructure.decorators import (
    handle_transport_errors,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock(spec=logging.Logger)


class TestDeviceRejectedCommandError:
    """Test suite for DeviceRejectedCommandError exception handling."""

    @pytest.mark.asyncio
    async def test_device_rejected_error_logged_without_stack_trace(self, mock_logger):
        """Test that DeviceRejectedCommandError is logged without exc_info."""

        @handle_transport_errors("Test operation", logger=mock_logger, reraise=False)
        async def test_func():
            raise DeviceRejectedCommandError("Batch contains unsupported register")

        # Execute function
        await test_func()

        # Verify error was logged
        assert mock_logger.error.called

        # Verify the error call did NOT include exc_info=True
        call_args = mock_logger.error.call_args
        assert call_args is not None

        # Check that exc_info was not passed (or was passed as False)
        if len(call_args) > 1 and "exc_info" in call_args[1]:
            assert call_args[1]["exc_info"] is not True

        # Verify the log message format
        log_message = call_args[0][0]
        assert "Test operation device error:" in log_message

    @pytest.mark.asyncio
    async def test_device_rejected_error_reraises_when_configured(self, mock_logger):
        """Test that DeviceRejectedCommandError is re-raised when reraise=True."""

        @handle_transport_errors("Test operation", logger=mock_logger, reraise=True)
        async def test_func():
            raise DeviceRejectedCommandError("Batch contains unsupported register")

        # Verify exception is re-raised
        with pytest.raises(
            DeviceRejectedCommandError, match="Batch contains unsupported register"
        ):
            await test_func()

        # Verify error was still logged
        assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_other_exceptions_still_log_with_stack_trace(self, mock_logger):
        """Test that other exceptions still get logged with stack traces."""

        @handle_transport_errors("Test operation", logger=mock_logger, reraise=False)
        async def test_func():
            raise ValueError("Unexpected error")

        # Execute function
        await test_func()

        # Verify error was logged
        assert mock_logger.error.called

        # Verify the error call DID include exc_info=True
        call_args = mock_logger.error.call_args
        assert call_args is not None
        assert len(call_args) > 1
        assert call_args[1].get("exc_info") is True

        # Verify the log message format
        log_message = call_args[0][0]
        assert "Test operation unexpected error:" in log_message

    @pytest.mark.asyncio
    async def test_exception_message_preserved(self, mock_logger):
        """Test that the exception message is preserved in logs."""
        error_message = "Batch contains unsupported register (dash error pattern)"

        @handle_transport_errors("BLE send", logger=mock_logger, reraise=False)
        async def test_func():
            raise DeviceRejectedCommandError(error_message)

        # Execute function
        await test_func()

        # Verify the full error message is in the log
        call_args = mock_logger.error.call_args
        log_call = " ".join(str(arg) for arg in call_args[0])
        assert error_message in log_call
