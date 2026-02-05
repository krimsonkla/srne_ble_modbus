"""Tests for connection decorator."""

import pytest
from unittest.mock import AsyncMock, Mock
from dataclasses import dataclass

from custom_components.srne_inverter.infrastructure.decorators.connection_decorator import (
    require_connection,
)


@dataclass
class TestResult:
    success: bool
    error: str = ""
    data: dict = None


class TestRequireConnection:
    """Test connection decorator."""

    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """Test decorator with successful connection."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True

            @require_connection(address_param="address")
            async def method(self, address: str) -> str:
                return f"Connected to {address}"

        obj = TestClass()
        result = await obj.method("AA:BB:CC:DD:EE:FF")

        assert result == "Connected to AA:BB:CC:DD:EE:FF"
        obj._connection_manager.ensure_connected.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF"
        )

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test decorator with connection failure."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = False

            @require_connection(address_param="address")
            async def method(self, address: str) -> TestResult:
                return TestResult(success=True)

        obj = TestClass()
        result = await obj.method("AA:BB:CC:DD:EE:FF")

        assert result.success is False
        assert "Failed to connect" in result.error

    @pytest.mark.asyncio
    async def test_missing_address_raises_error(self):
        """Test decorator raises error when address not provided."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()

            @require_connection(address_param="address")
            async def method(self) -> str:
                return "result"

        obj = TestClass()
        with pytest.raises(ValueError, match="No address provided"):
            await obj.method()

    @pytest.mark.asyncio
    async def test_address_from_kwargs(self):
        """Test decorator extracts address from kwargs."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True

            @require_connection(address_param="device_address")
            async def method(self, device_address: str, other_param: int) -> str:
                return f"Connected with {other_param}"

        obj = TestClass()
        result = await obj.method(device_address="AA:BB:CC:DD:EE:FF", other_param=42)

        assert result == "Connected with 42"
        obj._connection_manager.ensure_connected.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF"
        )

    @pytest.mark.asyncio
    async def test_address_from_positional_args(self):
        """Test decorator extracts address from positional args."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True

            @require_connection(address_param="device_address")
            async def method(self, device_address: str, other_param: int = 0) -> str:
                return f"Result {other_param}"

        obj = TestClass()
        result = await obj.method("AA:BB:CC:DD:EE:FF", 99)

        assert result == "Result 99"
        obj._connection_manager.ensure_connected.assert_called_once_with(
            "AA:BB:CC:DD:EE:FF"
        )

    @pytest.mark.asyncio
    async def test_auto_disconnect_disabled(self):
        """Test that auto_disconnect=False doesn't disconnect."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True
                self._transport = Mock()
                self._transport.is_connected = True
                self._transport.disconnect = AsyncMock()

            @require_connection(address_param="address", auto_disconnect=False)
            async def method(self, address: str) -> str:
                return "done"

        obj = TestClass()
        await obj.method("AA:BB:CC:DD:EE:FF")

        # Should NOT call disconnect
        obj._transport.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_disconnect_enabled(self):
        """Test that auto_disconnect=True disconnects after operation."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True
                self._transport = Mock()
                self._transport.is_connected = True
                self._transport.disconnect = AsyncMock()

            @require_connection(address_param="address", auto_disconnect=True)
            async def method(self, address: str) -> str:
                return "done"

        obj = TestClass()
        result = await obj.method("AA:BB:CC:DD:EE:FF")

        assert result == "done"
        # Should call disconnect
        obj._transport.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_failure_raises_runtime_error(self):
        """Test decorator raises RuntimeError when connection fails and no Result type."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = False

            @require_connection(address_param="address")
            async def method(self, address: str) -> str:
                return "result"

        obj = TestClass()
        with pytest.raises(RuntimeError, match="Failed to connect"):
            await obj.method("AA:BB:CC:DD:EE:FF")

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""

        class TestClass:
            def __init__(self):
                self._connection_manager = AsyncMock()
                self._connection_manager.ensure_connected.return_value = True

            @require_connection(address_param="address")
            async def my_method(self, address: str) -> str:
                """This is my method docstring."""
                return "result"

        obj = TestClass()
        assert obj.my_method.__name__ == "my_method"
        assert "docstring" in obj.my_method.__doc__
