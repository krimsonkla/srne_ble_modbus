"""Tests for ConnectionManager.

These tests verify connection lifecycle management, exponential backoff,
and failure tracking.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from custom_components.srne_inverter.infrastructure.transport import ConnectionManager
from tests.doubles.fake_transport import FakeTransport


@pytest.fixture
def fake_transport():
    """Create fake transport."""
    return FakeTransport()


@pytest.fixture
def manager(fake_transport):
    """Create connection manager with fake transport."""
    return ConnectionManager(fake_transport)


class TestConnectionManagerInitialization:
    """Test connection manager initialization."""

    def test_create_manager(self, fake_transport):
        """Test creating connection manager."""
        manager = ConnectionManager(fake_transport)
        assert manager is not None

    def test_initial_state_disconnected(self, manager):
        """Test initial state is disconnected."""
        assert manager.connection_state == "disconnected"

    def test_initial_failure_count_zero(self, manager):
        """Test initial failure count is zero."""
        info = manager.get_failure_info()
        assert info["consecutive_failures"] == 0


class TestEnsureConnected:
    """Test ensure_connected method."""

    @pytest.mark.asyncio
    async def test_ensure_connected_success(self, manager, fake_transport):
        """Test successful connection."""
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is True
        assert fake_transport.is_connected
        assert manager.connection_state == "connected"

    @pytest.mark.asyncio
    async def test_ensure_connected_already_connected(self, manager, fake_transport):
        """Test ensure_connected when already connected."""
        # Connect first time
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        # Try again
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is True
        assert manager.connection_state == "connected"

    @pytest.mark.asyncio
    async def test_ensure_connected_failure(self, manager, fake_transport):
        """Test connection failure increments failure count."""
        fake_transport.fail_next_connect()

        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is False
        assert manager.connection_state == "failed"

        info = manager.get_failure_info()
        assert info["consecutive_failures"] == 1


class TestExponentialBackoff:
    """Test exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_backoff_increases_on_failure(self, manager, fake_transport):
        """Test backoff time increases on consecutive failures."""
        fake_transport.fail_next_connect()
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        info1 = manager.get_failure_info()
        initial_backoff = info1["backoff_time"]

        fake_transport.fail_next_connect()
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        info2 = manager.get_failure_info()
        assert info2["backoff_time"] > initial_backoff

    @pytest.mark.asyncio
    async def test_backoff_resets_on_success(self, manager, fake_transport):
        """Test backoff resets after successful connection."""
        # Fail once to increase backoff
        fake_transport.fail_next_connect()
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        # Succeed
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is True
        info = manager.get_failure_info()
        assert info["consecutive_failures"] == 0
        assert info["backoff_time"] == ConnectionManager.INITIAL_BACKOFF

    @pytest.mark.asyncio
    async def test_max_consecutive_failures(self, manager, fake_transport):
        """Test max consecutive failures blocks connection."""
        # Fail MAX_CONSECUTIVE_FAILURES times
        for _ in range(ConnectionManager.MAX_CONSECUTIVE_FAILURES):
            fake_transport.fail_next_connect()
            await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        # Next attempt should be blocked
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is False
        assert manager.connection_state == "failed"


class TestConnectionLost:
    """Test handle_connection_lost."""

    @pytest.mark.asyncio
    async def test_handle_connection_lost_increments_failures(self, manager):
        """Test connection lost increments failure counter."""
        initial_info = manager.get_failure_info()

        await manager.handle_connection_lost()

        new_info = manager.get_failure_info()
        assert new_info["consecutive_failures"] > initial_info["consecutive_failures"]

    @pytest.mark.asyncio
    async def test_handle_connection_lost_updates_state(self, manager):
        """Test connection lost updates state."""
        await manager.handle_connection_lost()

        assert manager.connection_state == "reconnecting"

    @pytest.mark.asyncio
    async def test_handle_connection_lost_increases_backoff(self, manager):
        """Test connection lost increases backoff time."""
        initial_info = manager.get_failure_info()

        await manager.handle_connection_lost()

        new_info = manager.get_failure_info()
        assert new_info["backoff_time"] > initial_info["backoff_time"]


class TestConnectionState:
    """Test connection state tracking."""

    @pytest.mark.asyncio
    async def test_state_transitions(self, manager, fake_transport):
        """Test state transitions through connection lifecycle."""
        assert manager.connection_state == "disconnected"

        # Start connecting
        connect_task = asyncio.create_task(
            manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        )
        await asyncio.sleep(0)  # Let task start
        # State may be "connecting" briefly, but might transition fast

        await connect_task
        assert manager.connection_state == "connected"

    @pytest.mark.asyncio
    async def test_state_after_failure(self, manager, fake_transport):
        """Test state after connection failure."""
        fake_transport.fail_next_connect()

        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert manager.connection_state == "failed"


class TestResetFailures:
    """Test reset_failures method."""

    @pytest.mark.asyncio
    async def test_reset_failures(self, manager, fake_transport):
        """Test resetting failure tracking."""
        # Generate some failures
        fake_transport.fail_next_connect()
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        # Reset
        manager.reset_failures()

        info = manager.get_failure_info()
        assert info["consecutive_failures"] == 0
        assert info["backoff_time"] == ConnectionManager.INITIAL_BACKOFF
        assert manager.connection_state == "disconnected"


class TestFailureInfo:
    """Test get_failure_info method."""

    def test_get_failure_info_structure(self, manager):
        """Test failure info has expected structure."""
        info = manager.get_failure_info()

        assert "consecutive_failures" in info
        assert "backoff_time" in info
        assert "last_attempt" in info
        assert "state" in info

    @pytest.mark.asyncio
    async def test_failure_info_updated(self, manager, fake_transport):
        """Test failure info is updated after attempts."""
        initial_info = manager.get_failure_info()

        fake_transport.fail_next_connect()
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        new_info = manager.get_failure_info()
        assert new_info["consecutive_failures"] > initial_info["consecutive_failures"]
        assert new_info["last_attempt"] > initial_info["last_attempt"]


class TestInterfaceCompliance:
    """Test ConnectionManager implements IConnectionManager."""

    def test_implements_interface(self, manager):
        """Test ConnectionManager implements IConnectionManager."""
        from custom_components.srne_inverter.domain.interfaces import IConnectionManager

        assert isinstance(manager, IConnectionManager)

    def test_has_required_methods(self, manager):
        """Test manager has all required methods."""
        assert hasattr(manager, "ensure_connected")
        assert hasattr(manager, "handle_connection_lost")
        assert hasattr(manager, "connection_state")

        assert callable(manager.ensure_connected)
        assert callable(manager.handle_connection_lost)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_connect_with_exception(self, manager):
        """Test handling of connection exceptions."""
        # Create transport that raises exception
        bad_transport = Mock()
        bad_transport.connect = AsyncMock(side_effect=Exception("Connection error"))
        bad_transport.is_connected = False

        bad_manager = ConnectionManager(bad_transport)

        success = await bad_manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is False
        assert bad_manager.connection_state == "failed"

    @pytest.mark.asyncio
    async def test_multiple_consecutive_failures(self, manager, fake_transport):
        """Test multiple consecutive failures."""
        for i in range(3):
            fake_transport.fail_next_connect()
            success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
            assert success is False

            info = manager.get_failure_info()
            assert info["consecutive_failures"] == i + 1


class TestReconnectingStateDeadlock:
    """Test fix for RECONNECTING state deadlock issue.

    Verifies that after connection is lost and state transitions to RECONNECTING,
    subsequent ensure_connected() calls can successfully reconnect instead of
    being blocked by the "Cannot connect in state: RECONNECTING" error.
    """

    @pytest.mark.asyncio
    async def test_can_reconnect_from_reconnecting_state(self, manager, fake_transport):
        """Test that ensure_connected() works when in RECONNECTING state."""
        # First, establish a connection
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        assert success is True
        assert manager.connection_state == "connected"

        # Simulate connection loss - this transitions to RECONNECTING
        await manager.handle_connection_lost()
        assert manager.connection_state == "reconnecting"

        # Now attempt reconnection - this should succeed instead of failing
        # with "Cannot connect in state: RECONNECTING"
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        assert success is True
        assert manager.connection_state == "connected"

    @pytest.mark.asyncio
    async def test_reconnecting_state_allows_connection_attempts(
        self, manager, fake_transport
    ):
        """Test that RECONNECTING state is included in can_connect states."""
        # Establish connection
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        assert manager.is_connected

        # Lose connection
        await manager.handle_connection_lost()
        assert manager.connection_state == "reconnecting"

        # Verify can_connect is True for RECONNECTING state
        from custom_components.srne_inverter.infrastructure.state_machines import (
            ConnectionState,
        )

        assert manager._state_machine.state == ConnectionState.RECONNECTING
        assert manager._state_machine.can_connect is True

    @pytest.mark.asyncio
    async def test_reconnecting_uses_retry_event(self, manager, fake_transport):
        """Test that RECONNECTING state uses RETRY event to transition to CONNECTING."""
        from custom_components.srne_inverter.infrastructure.state_machines import (
            ConnectionState,
            ConnectionEvent,
        )

        # Set up connection and lose it
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        await manager.handle_connection_lost()
        assert manager._state_machine.state == ConnectionState.RECONNECTING

        # Manually test the transition - RETRY event should work
        result = manager._state_machine.transition(ConnectionEvent.RETRY)
        assert result is True
        assert manager._state_machine.state == ConnectionState.CONNECTING

    @pytest.mark.asyncio
    async def test_reconnect_after_backoff_period(self, manager, fake_transport):
        """Test automatic reconnection after backoff period expires."""
        # Establish and lose connection
        await manager.ensure_connected("AA:BB:CC:DD:EE:FF")
        await manager.handle_connection_lost()

        initial_info = manager.get_failure_info()
        assert initial_info["consecutive_failures"] == 1
        assert initial_info["state"] == "reconnecting"

        # Wait for backoff and reconnect
        await asyncio.sleep(manager._backoff_time)
        success = await manager.ensure_connected("AA:BB:CC:DD:EE:FF")

        assert success is True
        assert manager.connection_state == "connected"
        # Failures should reset on successful reconnection
        final_info = manager.get_failure_info()
        assert final_info["consecutive_failures"] == 0
