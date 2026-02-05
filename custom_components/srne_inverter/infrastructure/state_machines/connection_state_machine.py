"""Connection state machine for explicit state management."""

import logging
from enum import Enum, auto
from typing import Optional, Dict, Callable

_LOGGER = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection states."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    FAILED = auto()
    BACKOFF = auto()


class ConnectionEvent(Enum):
    """Connection events that trigger state transitions."""

    CONNECT = auto()
    CONNECT_SUCCESS = auto()
    CONNECT_FAILED = auto()
    DISCONNECT = auto()
    CONNECTION_LOST = auto()
    RETRY = auto()
    BACKOFF_EXPIRED = auto()


class ConnectionStateMachine:
    """State machine for connection lifecycle management.

    Valid transitions:
        DISCONNECTED -> CONNECTING (on CONNECT)
        CONNECTING -> CONNECTED (on CONNECT_SUCCESS)
        CONNECTING -> FAILED (on CONNECT_FAILED)
        CONNECTED -> DISCONNECTED (on DISCONNECT)
        CONNECTED -> RECONNECTING (on CONNECTION_LOST)
        FAILED -> BACKOFF (on RETRY with retries remaining)
        BACKOFF -> CONNECTING (on BACKOFF_EXPIRED)
        RECONNECTING -> CONNECTING (on RETRY)

    Example:
        >>> sm = ConnectionStateMachine()
        >>> sm.transition(ConnectionEvent.CONNECT)
        True
        >>> sm.state
        <ConnectionState.CONNECTING: 2>
        >>> sm.transition(ConnectionEvent.CONNECT_SUCCESS)
        True
        >>> sm.is_connected
        True
    """

    def __init__(self):
        """Initialize state machine in DISCONNECTED state."""
        self._state = ConnectionState.DISCONNECTED
        self._previous_state: Optional[ConnectionState] = None

        # Callbacks for state changes
        self._on_state_change: Dict[ConnectionState, Callable] = {}

        # Valid transitions: (current_state, event) -> new_state
        self._transitions = {
            (
                ConnectionState.DISCONNECTED,
                ConnectionEvent.CONNECT,
            ): ConnectionState.CONNECTING,
            (
                ConnectionState.CONNECTING,
                ConnectionEvent.CONNECT_SUCCESS,
            ): ConnectionState.CONNECTED,
            (
                ConnectionState.CONNECTING,
                ConnectionEvent.CONNECT_FAILED,
            ): ConnectionState.FAILED,
            (
                ConnectionState.CONNECTED,
                ConnectionEvent.DISCONNECT,
            ): ConnectionState.DISCONNECTED,
            (
                ConnectionState.CONNECTED,
                ConnectionEvent.CONNECTION_LOST,
            ): ConnectionState.RECONNECTING,
            (ConnectionState.FAILED, ConnectionEvent.RETRY): ConnectionState.BACKOFF,
            (
                ConnectionState.BACKOFF,
                ConnectionEvent.BACKOFF_EXPIRED,
            ): ConnectionState.CONNECTING,
            (
                ConnectionState.RECONNECTING,
                ConnectionEvent.RETRY,
            ): ConnectionState.CONNECTING,
        }

    @property
    def state(self) -> ConnectionState:
        """Get current state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def is_connecting(self) -> bool:
        """Check if connection in progress."""
        return self._state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING)

    @property
    def can_connect(self) -> bool:
        """Check if connection can be initiated."""
        return self._state in (
            ConnectionState.DISCONNECTED,
            ConnectionState.FAILED,
            ConnectionState.BACKOFF,
            ConnectionState.RECONNECTING,
        )

    def transition(self, event: ConnectionEvent) -> bool:
        """Attempt state transition.

        Args:
            event: Event triggering transition

        Returns:
            True if transition valid and executed, False otherwise

        Example:
            >>> sm = ConnectionStateMachine()
            >>> sm.transition(ConnectionEvent.CONNECT)
            True
            >>> sm.state.name
            'CONNECTING'
        """
        key = (self._state, event)

        if key not in self._transitions:
            _LOGGER.debug(
                "Invalid transition: %s + %s (current: %s)",
                self._state.name,
                event.name,
                self._state.name,
            )
            return False

        new_state = self._transitions[key]
        self._change_state(new_state, event)
        return True

    def force_state(self, state: ConnectionState):
        """Force state change (bypasses validation).

        Use sparingly - prefer transition() for normal flow.

        Args:
            state: State to force
        """
        self._previous_state = self._state
        self._state = state
        _LOGGER.debug("Force state: %s -> %s", self._previous_state.name, state.name)

    def _change_state(self, new_state: ConnectionState, event: ConnectionEvent):
        """Change to new state and invoke callbacks.

        Args:
            new_state: State to transition to
            event: Event that triggered transition
        """
        self._previous_state = self._state
        self._state = new_state

        _LOGGER.debug(
            "Connection state: %s -> %s (event: %s)",
            self._previous_state.name,
            new_state.name,
            event.name,
        )

        # Invoke state change callback
        if new_state in self._on_state_change:
            try:
                self._on_state_change[new_state]()
            except Exception as err:
                _LOGGER.error("Error in state change callback: %s", err)

    def on_state(self, state: ConnectionState, callback: Callable):
        """Register callback for state entry.

        Args:
            state: State to watch
            callback: Function to call on state entry (no args)

        Example:
            >>> sm = ConnectionStateMachine()
            >>> sm.on_state(ConnectionState.CONNECTED, lambda: print("Connected!"))
        """
        self._on_state_change[state] = callback

    def reset(self):
        """Reset to initial DISCONNECTED state."""
        self._state = ConnectionState.DISCONNECTED
        self._previous_state = None

    def __str__(self) -> str:
        """String representation."""
        return f"ConnectionStateMachine(state={self._state.name})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"ConnectionStateMachine(state={self._state!r}, previous={self._previous_state!r})"
