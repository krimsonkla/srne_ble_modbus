"""State machine for SRNE Inverter onboarding flow."""

from __future__ import annotations

from enum import Enum
import logging

_LOGGER = logging.getLogger(__name__)


class OnboardingState(Enum):
    """States in the onboarding flow."""

    DEVICE_SCAN = "device_scan"
    DEVICE_SELECTED = "device_selected"
    WELCOME = "welcome"
    USER_LEVEL = "user_level"
    HARDWARE_DETECTION = "hardware_detection"
    DETECTION_REVIEW = "detection_review"
    PRESET_SELECTION = "preset_selection"
    MANUAL_CONFIG = "manual_config"
    VALIDATION = "validation"
    REVIEW = "review"
    WRITE_SETTINGS = "write_settings"
    COMPLETE = "complete"

    # Error/recovery states
    DETECTION_FAILED = "detection_failed"
    WRITE_FAILED = "write_failed"


class OnboardingStateMachine:
    """State machine managing onboarding flow transitions.

    This implements a simple finite state machine with validation
    of state transitions and support for back navigation.
    """

    # Define valid state transitions
    TRANSITIONS = {
        OnboardingState.DEVICE_SCAN: [OnboardingState.DEVICE_SELECTED],
        OnboardingState.DEVICE_SELECTED: [OnboardingState.WELCOME],
        OnboardingState.WELCOME: [
            OnboardingState.USER_LEVEL,
            OnboardingState.DEVICE_SCAN,
        ],
        OnboardingState.USER_LEVEL: [
            OnboardingState.HARDWARE_DETECTION,
            OnboardingState.WELCOME,
        ],
        OnboardingState.HARDWARE_DETECTION: [
            OnboardingState.DETECTION_REVIEW,
            OnboardingState.DETECTION_FAILED,
            OnboardingState.USER_LEVEL,
        ],
        OnboardingState.DETECTION_REVIEW: [
            OnboardingState.PRESET_SELECTION,  # basic users
            OnboardingState.MANUAL_CONFIG,  # advanced/expert users
            OnboardingState.HARDWARE_DETECTION,  # retry
        ],
        OnboardingState.DETECTION_FAILED: [
            OnboardingState.HARDWARE_DETECTION,  # retry
            OnboardingState.MANUAL_CONFIG,  # skip detection
        ],
        OnboardingState.PRESET_SELECTION: [
            OnboardingState.VALIDATION,
            OnboardingState.MANUAL_CONFIG,  # custom option
            OnboardingState.DETECTION_REVIEW,
        ],
        OnboardingState.MANUAL_CONFIG: [
            OnboardingState.VALIDATION,
            OnboardingState.DETECTION_REVIEW,
        ],
        OnboardingState.VALIDATION: [
            OnboardingState.REVIEW,
            OnboardingState.PRESET_SELECTION,  # if errors, go back
            OnboardingState.MANUAL_CONFIG,  # if errors, go back
        ],
        OnboardingState.REVIEW: [
            OnboardingState.WRITE_SETTINGS,
            OnboardingState.VALIDATION,  # edit
        ],
        OnboardingState.WRITE_SETTINGS: [
            OnboardingState.COMPLETE,
            OnboardingState.WRITE_FAILED,
        ],
        OnboardingState.WRITE_FAILED: [
            OnboardingState.WRITE_SETTINGS,  # retry
            OnboardingState.REVIEW,  # go back
        ],
        OnboardingState.COMPLETE: [],  # terminal state
    }

    def __init__(self) -> None:
        """Initialize the state machine."""
        self.current_state = OnboardingState.DEVICE_SCAN
        self.history: list[OnboardingState] = [OnboardingState.DEVICE_SCAN]

    def transition(self, to_state: OnboardingState) -> bool:
        """Validate and execute state transition.

        Args:
            to_state: Target state

        Returns:
            True if transition was successful, False otherwise
        """
        if not self.can_transition(to_state):
            _LOGGER.warning(
                "Invalid state transition attempted: %s -> %s",
                self.current_state.value,
                to_state.value,
            )
            return False

        _LOGGER.info(
            "State transition: %s -> %s",
            self.current_state.value,
            to_state.value,
        )
        self.current_state = to_state
        self.history.append(to_state)
        return True

    def can_transition(self, to_state: OnboardingState) -> bool:
        """Check if transition to target state is valid.

        Args:
            to_state: Target state

        Returns:
            True if transition is allowed
        """
        valid_transitions = self.TRANSITIONS.get(self.current_state, [])
        return to_state in valid_transitions

    def get_next_states(self) -> list[OnboardingState]:
        """Get list of valid next states from current state.

        Returns:
            List of states that can be transitioned to
        """
        return self.TRANSITIONS.get(self.current_state, [])

    def can_go_back(self) -> bool:
        """Check if back navigation is possible.

        Returns:
            True if there are previous states to return to
        """
        return len(self.history) > 1

    def go_back(self) -> OnboardingState | None:
        """Navigate to previous state.

        Returns:
            Previous state if navigation was successful, None otherwise
        """
        if not self.can_go_back():
            _LOGGER.warning("Cannot go back - no previous states")
            return None

        # Remove current state from history
        self.history.pop()

        # Get previous state
        previous_state = self.history[-1]
        self.current_state = previous_state

        _LOGGER.info("Navigated back to state: %s", previous_state.value)
        return previous_state

    def reset(self) -> None:
        """Reset state machine to initial state."""
        self.current_state = OnboardingState.DEVICE_SCAN
        self.history = [OnboardingState.DEVICE_SCAN]
        _LOGGER.info("State machine reset to initial state")
