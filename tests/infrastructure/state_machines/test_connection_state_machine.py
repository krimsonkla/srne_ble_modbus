"""Tests for connection state machine."""

import pytest
from unittest.mock import Mock

from custom_components.srne_inverter.infrastructure.state_machines.connection_state_machine import (
    ConnectionStateMachine,
    ConnectionState,
    ConnectionEvent,
)


class TestConnectionStateMachine:
    """Test connection state machine."""

    def test_initial_state_is_disconnected(self):
        """Test state machine starts in DISCONNECTED."""
        sm = ConnectionStateMachine()
        assert sm.state == ConnectionState.DISCONNECTED
        assert not sm.is_connected
        assert not sm.is_connecting

    def test_transition_connect(self):
        """Test DISCONNECTED -> CONNECTING transition."""
        sm = ConnectionStateMachine()
        assert sm.transition(ConnectionEvent.CONNECT)
        assert sm.state == ConnectionState.CONNECTING
        assert sm.is_connecting

    def test_transition_connect_success(self):
        """Test CONNECTING -> CONNECTED transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        assert sm.transition(ConnectionEvent.CONNECT_SUCCESS)
        assert sm.state == ConnectionState.CONNECTED
        assert sm.is_connected

    def test_transition_connect_failed(self):
        """Test CONNECTING -> FAILED transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        assert sm.transition(ConnectionEvent.CONNECT_FAILED)
        assert sm.state == ConnectionState.FAILED
        assert not sm.is_connected

    def test_invalid_transition_returns_false(self):
        """Test invalid transitions return False."""
        sm = ConnectionStateMachine()
        # Can't go to CONNECTED from DISCONNECTED directly
        assert not sm.transition(ConnectionEvent.CONNECT_SUCCESS)
        assert sm.state == ConnectionState.DISCONNECTED

    def test_disconnect_from_connected(self):
        """Test CONNECTED -> DISCONNECTED transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)

        assert sm.transition(ConnectionEvent.DISCONNECT)
        assert sm.state == ConnectionState.DISCONNECTED

    def test_connection_lost_reconnecting(self):
        """Test CONNECTED -> RECONNECTING transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)

        assert sm.transition(ConnectionEvent.CONNECTION_LOST)
        assert sm.state == ConnectionState.RECONNECTING
        assert sm.is_connecting

    def test_state_callbacks(self):
        """Test state change callbacks are invoked."""
        sm = ConnectionStateMachine()
        callback = Mock()

        sm.on_state(ConnectionState.CONNECTED, callback)

        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)

        callback.assert_called_once()

    def test_can_connect_property(self):
        """Test can_connect property."""
        sm = ConnectionStateMachine()
        assert sm.can_connect  # DISCONNECTED

        sm.transition(ConnectionEvent.CONNECT)
        assert not sm.can_connect  # CONNECTING

        sm.transition(ConnectionEvent.CONNECT_SUCCESS)
        assert not sm.can_connect  # CONNECTED

    def test_reset(self):
        """Test reset returns to DISCONNECTED."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)

        sm.reset()
        assert sm.state == ConnectionState.DISCONNECTED

    def test_str_representation(self):
        """Test string representation."""
        sm = ConnectionStateMachine()
        assert "DISCONNECTED" in str(sm)

    def test_force_state(self):
        """Test force_state bypasses validation."""
        sm = ConnectionStateMachine()
        sm.force_state(ConnectionState.CONNECTED)
        assert sm.is_connected

    def test_backoff_transition(self):
        """Test FAILED -> BACKOFF transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_FAILED)

        assert sm.transition(ConnectionEvent.RETRY)
        assert sm.state == ConnectionState.BACKOFF

    def test_backoff_expired_transition(self):
        """Test BACKOFF -> CONNECTING transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_FAILED)
        sm.transition(ConnectionEvent.RETRY)

        assert sm.transition(ConnectionEvent.BACKOFF_EXPIRED)
        assert sm.state == ConnectionState.CONNECTING

    def test_reconnecting_retry(self):
        """Test RECONNECTING -> CONNECTING transition."""
        sm = ConnectionStateMachine()
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)
        sm.transition(ConnectionEvent.CONNECTION_LOST)

        assert sm.transition(ConnectionEvent.RETRY)
        assert sm.state == ConnectionState.CONNECTING

    def test_callback_exception_handling(self):
        """Test callback exceptions are caught and logged."""
        sm = ConnectionStateMachine()

        def failing_callback():
            raise RuntimeError("Callback error")

        sm.on_state(ConnectionState.CONNECTED, failing_callback)

        # Should not raise, exception should be logged
        sm.transition(ConnectionEvent.CONNECT)
        sm.transition(ConnectionEvent.CONNECT_SUCCESS)

        # State should still be updated despite callback failure
        assert sm.is_connected

    def test_repr(self):
        """Test developer representation."""
        sm = ConnectionStateMachine()
        repr_str = repr(sm)
        assert "ConnectionStateMachine" in repr_str
        assert "DISCONNECTED" in repr_str
