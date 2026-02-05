"""Tests for domain interface definitions.

These tests verify that interfaces are properly defined and can be
implemented by concrete classes.
"""

import pytest
from abc import ABC
from custom_components.srne_inverter.domain.interfaces import (
    ICRC,
    IProtocol,
    ITransport,
    IConnectionManager,
    IRepository,
    IFailedRegisterRepository,
    IBatchStrategy,
)


class TestInterfaceDefinitions:
    """Test that all interfaces are properly defined."""

    def test_icrc_is_abstract(self):
        """Verify ICRC is an abstract base class."""
        assert issubclass(ICRC, ABC)

        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            ICRC()

    def test_iprotocol_is_abstract(self):
        """Verify IProtocol is an abstract base class."""
        assert issubclass(IProtocol, ABC)

        with pytest.raises(TypeError):
            IProtocol()

    def test_itransport_is_abstract(self):
        """Verify ITransport is an abstract base class."""
        assert issubclass(ITransport, ABC)

        with pytest.raises(TypeError):
            ITransport()

    def test_iconnection_manager_is_abstract(self):
        """Verify IConnectionManager is an abstract base class."""
        assert issubclass(IConnectionManager, ABC)

        with pytest.raises(TypeError):
            IConnectionManager()

    def test_irepository_is_abstract(self):
        """Verify IRepository is an abstract base class."""
        assert issubclass(IRepository, ABC)

        with pytest.raises(TypeError):
            IRepository()

    def test_ifailed_register_repository_is_abstract(self):
        """Verify IFailedRegisterRepository is an abstract base class."""
        assert issubclass(IFailedRegisterRepository, ABC)

        with pytest.raises(TypeError):
            IFailedRegisterRepository()

    def test_ibatch_strategy_is_abstract(self):
        """Verify IBatchStrategy is an abstract base class."""
        assert issubclass(IBatchStrategy, ABC)

        with pytest.raises(TypeError):
            IBatchStrategy()


class TestInterfaceContracts:
    """Test that interfaces define expected methods."""

    def test_icrc_has_calculate_method(self):
        """Verify ICRC defines calculate method."""
        assert hasattr(ICRC, "calculate")
        assert callable(getattr(ICRC, "calculate"))

    def test_iprotocol_has_required_methods(self):
        """Verify IProtocol defines all required methods."""
        required_methods = [
            "build_read_command",
            "build_write_command",
            "decode_response",
        ]
        for method in required_methods:
            assert hasattr(IProtocol, method)
            assert callable(getattr(IProtocol, method))

    def test_itransport_has_required_methods(self):
        """Verify ITransport defines all required methods."""
        required_methods = ["connect", "disconnect", "send"]
        for method in required_methods:
            assert hasattr(ITransport, method)
            assert callable(getattr(ITransport, method))

        # Also has is_connected property
        assert hasattr(ITransport, "is_connected")

    def test_iconnection_manager_has_required_methods(self):
        """Verify IConnectionManager defines all required methods."""
        required_methods = [
            "ensure_connected",
            "handle_connection_lost",
        ]
        for method in required_methods:
            assert hasattr(IConnectionManager, method)
            assert callable(getattr(IConnectionManager, method))

        assert hasattr(IConnectionManager, "connection_state")

    def test_irepository_has_crud_methods(self):
        """Verify IRepository defines CRUD methods."""
        required_methods = ["add", "get", "update", "remove", "list_all"]
        for method in required_methods:
            assert hasattr(IRepository, method)
            assert callable(getattr(IRepository, method))

    def test_ifailed_register_repository_has_required_methods(self):
        """Verify IFailedRegisterRepository defines all required methods."""
        required_methods = [
            "load",
            "save",
            "add_failed",
            "remove_failed",
            "clear",
            "is_failed",
        ]
        for method in required_methods:
            assert hasattr(IFailedRegisterRepository, method)
            assert callable(getattr(IFailedRegisterRepository, method))

    def test_ibatch_strategy_has_required_methods(self):
        """Verify IBatchStrategy defines all required methods."""
        required_methods = ["build_batches", "split_batch"]
        for method in required_methods:
            assert hasattr(IBatchStrategy, method)
            assert callable(getattr(IBatchStrategy, method))

        # Also has properties
        assert hasattr(IBatchStrategy, "max_batch_size")
        assert hasattr(IBatchStrategy, "strategy_name")


class TestConcreteImplementations:
    """Test that concrete implementations can implement interfaces."""

    def test_can_implement_icrc(self):
        """Verify a concrete class can implement ICRC."""

        class MockCRC(ICRC):
            def calculate(self, data: bytes) -> int:
                return 0x1234

        crc = MockCRC()
        assert crc.calculate(b"\x01\x02\x03") == 0x1234

    def test_can_implement_iprotocol(self):
        """Verify a concrete class can implement IProtocol."""

        class MockProtocol(IProtocol):
            def build_read_command(self, start_address: int, count: int) -> bytes:
                return b"\x01\x03"

            def build_write_command(self, address: int, value: int) -> bytes:
                return b"\x01\x06"

            def decode_response(self, response: bytes) -> dict:
                return {0x0100: 486}

        protocol = MockProtocol()
        assert protocol.build_read_command(0x0100, 1) == b"\x01\x03"
        assert protocol.decode_response(b"test") == {0x0100: 486}

    async def test_can_implement_itransport(self):
        """Verify a concrete class can implement ITransport."""

        class MockTransport(ITransport):
            def __init__(self):
                self._connected = False

            async def connect(self, address: str) -> bool:
                self._connected = True
                return True

            async def disconnect(self) -> None:
                self._connected = False

            async def send(self, data: bytes, timeout: float = 5.0) -> bytes:
                return b"response"

            @property
            def is_connected(self) -> bool:
                return self._connected

        transport = MockTransport()
        assert not transport.is_connected
        await transport.connect("test")
        assert transport.is_connected
        response = await transport.send(b"test")
        assert response == b"response"

    async def test_can_implement_ifailed_register_repository(self):
        """Verify a concrete class can implement IFailedRegisterRepository."""

        class MockRepository(IFailedRegisterRepository):
            def __init__(self):
                self._failed = set()

            async def load(self) -> set:
                return self._failed.copy()

            async def save(self, registers: set) -> None:
                self._failed = registers.copy()

            async def add_failed(self, address: int) -> None:
                self._failed.add(address)

            async def remove_failed(self, address: int) -> None:
                self._failed.discard(address)

            async def clear(self) -> None:
                self._failed.clear()

            async def is_failed(self, address: int) -> bool:
                return address in self._failed

        repo = MockRepository()
        assert await repo.load() == set()

        await repo.add_failed(0x0100)
        assert await repo.is_failed(0x0100)

        await repo.remove_failed(0x0100)
        assert not await repo.is_failed(0x0100)
