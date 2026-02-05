"""Tests for error handling decorator."""

import asyncio
import logging
import pytest

from custom_components.srne_inverter.infrastructure.decorators.error_handler import (
    handle_transport_errors,
)


class TestHandleTransportErrors:
    """Test error handling decorator."""

    @pytest.mark.asyncio
    async def test_successful_async_execution(self):
        """Test decorator with successful async function."""

        @handle_transport_errors("test operation")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_error_reraise(self):
        """Test timeout error with reraise=True."""

        @handle_transport_errors("test operation", reraise=True)
        async def test_func():
            raise asyncio.TimeoutError("timeout")

        with pytest.raises(asyncio.TimeoutError):
            await test_func()

    @pytest.mark.asyncio
    async def test_timeout_error_no_reraise(self):
        """Test timeout error with reraise=False."""

        @handle_transport_errors(
            "test operation", reraise=False, default_return="default"
        )
        async def test_func():
            raise asyncio.TimeoutError("timeout")

        result = await test_func()
        assert result == "default"

    @pytest.mark.asyncio
    async def test_generic_exception_logged(self, caplog):
        """Test that exceptions are logged."""

        @handle_transport_errors("test operation", reraise=False)
        async def test_func():
            raise ValueError("test error")

        with caplog.at_level(logging.ERROR):
            await test_func()

        assert "test operation unexpected error" in caplog.text
        assert "test error" in caplog.text

    def test_sync_function_support(self):
        """Test decorator works with sync functions."""

        @handle_transport_errors("sync operation", reraise=False, default_return=42)
        def test_func():
            raise ValueError("error")

        result = test_func()
        assert result == 42

    @pytest.mark.asyncio
    async def test_custom_logger(self, caplog):
        """Test using custom logger."""
        custom_logger = logging.getLogger("custom")

        @handle_transport_errors("test op", logger=custom_logger, reraise=False)
        async def test_func():
            raise ValueError("error")

        with caplog.at_level(logging.ERROR):
            await test_func()

        assert "custom" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_with_timeout_kwarg(self, caplog):
        """Test timeout error logs timeout value from kwargs."""

        @handle_transport_errors("test operation", reraise=False)
        async def test_func(timeout=5.0):
            raise asyncio.TimeoutError("timeout")

        with caplog.at_level(logging.WARNING):
            await test_func(timeout=3.0)

        assert "timed out after 3.0s" in caplog.text

    @pytest.mark.asyncio
    async def test_bleak_error_handling(self, caplog):
        """Test BleakError is caught and logged."""
        from bleak.exc import BleakError

        @handle_transport_errors("test operation", reraise=False)
        async def test_func():
            raise BleakError("BLE failed")

        with caplog.at_level(logging.ERROR):
            result = await test_func()

        assert result is None
        assert "BLE error" in caplog.text
        assert "BLE failed" in caplog.text

    @pytest.mark.asyncio
    async def test_function_with_args_and_kwargs(self):
        """Test decorator preserves function arguments."""

        @handle_transport_errors("test operation")
        async def test_func(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await test_func("x", "y", c="z")
        assert result == "x-y-z"

    def test_sync_exception_handling(self, caplog):
        """Test sync function exception handling."""

        @handle_transport_errors("sync operation", reraise=False, default_return=None)
        def test_func():
            raise RuntimeError("sync error")

        with caplog.at_level(logging.ERROR):
            result = test_func()

        assert result is None
        assert "sync operation error" in caplog.text
        assert "sync error" in caplog.text
