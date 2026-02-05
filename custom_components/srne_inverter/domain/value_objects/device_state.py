"""DeviceState value object.

Represents the operational state of the inverter device.
"""

from enum import IntEnum


class DeviceState(IntEnum):
    """Inverter operational states.

    These states map to the "machine_state" register value from the device.
    Understanding these states is critical for:
    - Determining if device is operational
    - Deciding if certain operations are allowed (e.g., writes)
    - Providing accurate status to users

    State Transitions:
        STANDBY → SOFT_START → AC_OPERATION
                              → INVERTER_OPERATION
        Any state → MANUAL_SHUTDOWN → STANDBY
        Any state → ERROR → (requires reset)

    Reference: SRNE HF Series Communication Protocol v1.2
    """

    # Normal operational states
    STANDBY = 1  # Device powered but not active
    GRID_CHECK = 2  # Checking grid parameters
    SOFT_START = 3  # Starting up (0-60s)
    AC_OPERATION = 4  # Operating from AC/grid power
    INVERTER_OPERATION = 5  # Operating in inverter mode (battery)
    SELF_TEST = 6  # Running self-diagnostics
    BATTERY_CHARGE = 7  # Actively charging battery

    # Shutdown states
    MANUAL_SHUTDOWN = 9  # User-initiated shutdown
    OVERLOAD_PROTECTION = 10  # Shutdown due to overload
    TEMPERATURE_PROTECTION = 11  # Shutdown due to temperature
    OVERVOLTAGE_PROTECTION = 12  # Shutdown due to overvoltage
    UNDERVOLTAGE_PROTECTION = 13  # Shutdown due to undervoltage

    # Error states
    ERROR = 99  # General error state
    UNKNOWN = 0  # Unknown/invalid state

    @property
    def is_operational(self) -> bool:
        """Check if device is in operational state.

        Returns:
            True if device is actively working (AC or inverter operation)

        Example:
            >>> DeviceState.AC_OPERATION.is_operational
            True
            >>> DeviceState.STANDBY.is_operational
            False
        """
        return self in (
            DeviceState.AC_OPERATION,
            DeviceState.INVERTER_OPERATION,
            DeviceState.BATTERY_CHARGE,
        )

    @property
    def is_error(self) -> bool:
        """Check if device is in error state.

        Returns:
            True if device has encountered an error

        Example:
            >>> DeviceState.ERROR.is_error
            True
            >>> DeviceState.OVERLOAD_PROTECTION.is_error
            True
        """
        return self in (
            DeviceState.ERROR,
            DeviceState.OVERLOAD_PROTECTION,
            DeviceState.TEMPERATURE_PROTECTION,
            DeviceState.OVERVOLTAGE_PROTECTION,
            DeviceState.UNDERVOLTAGE_PROTECTION,
        )

    @property
    def is_shutdown(self) -> bool:
        """Check if device is shutdown (error or manual).

        Returns:
            True if device is in any shutdown state

        Example:
            >>> DeviceState.MANUAL_SHUTDOWN.is_shutdown
            True
            >>> DeviceState.AC_OPERATION.is_shutdown
            False
        """
        return self.is_error or self == DeviceState.MANUAL_SHUTDOWN

    @property
    def is_transitional(self) -> bool:
        """Check if device is in transitional state.

        Transitional states are temporary and shouldn't last long.
        If device is stuck in these states, it may indicate a problem.

        Returns:
            True if state is transitional

        Example:
            >>> DeviceState.SOFT_START.is_transitional
            True
            >>> DeviceState.SELF_TEST.is_transitional
            True
        """
        return self in (
            DeviceState.GRID_CHECK,
            DeviceState.SOFT_START,
            DeviceState.SELF_TEST,
        )

    @property
    def allows_writes(self) -> bool:
        """Check if device state allows register writes.

        Some states (like SOFT_START) may not be safe for configuration
        changes.

        Returns:
            True if register writes are allowed in this state

        Example:
            >>> DeviceState.STANDBY.allows_writes
            True
            >>> DeviceState.SOFT_START.allows_writes
            False
        """
        # Don't allow writes during transitional or error states
        return not (self.is_transitional or self.is_error)

    def get_display_name(self) -> str:
        """Get human-readable state name.

        Returns:
            Display-friendly state name

        Example:
            >>> DeviceState.AC_OPERATION.get_display_name()
            'AC Operation'
            >>> DeviceState.OVERLOAD_PROTECTION.get_display_name()
            'Overload Protection'
        """
        # Convert enum name to title case with spaces
        return self.name.replace("_", " ").title()

    def get_description(self) -> str:
        """Get detailed state description.

        Returns:
            Description of what the state means

        Example:
            >>> desc = DeviceState.AC_OPERATION.get_description()
            >>> assert "grid power" in desc.lower()
        """
        descriptions = {
            DeviceState.STANDBY: "Device is powered but inactive",
            DeviceState.GRID_CHECK: "Checking grid voltage and frequency",
            DeviceState.SOFT_START: "Starting up (0-60 seconds)",
            DeviceState.AC_OPERATION: "Operating from grid power",
            DeviceState.INVERTER_OPERATION: "Operating from battery (inverter mode)",
            DeviceState.SELF_TEST: "Running self-diagnostics",
            DeviceState.BATTERY_CHARGE: "Actively charging battery",
            DeviceState.MANUAL_SHUTDOWN: "Manually shut down by user",
            DeviceState.OVERLOAD_PROTECTION: "Shut down due to overload",
            DeviceState.TEMPERATURE_PROTECTION: "Shut down due to high temperature",
            DeviceState.OVERVOLTAGE_PROTECTION: "Shut down due to overvoltage",
            DeviceState.UNDERVOLTAGE_PROTECTION: "Shut down due to undervoltage",
            DeviceState.ERROR: "Device encountered an error",
            DeviceState.UNKNOWN: "Unknown or invalid state",
        }
        return descriptions.get(self, "No description available")

    @classmethod
    def from_register_value(cls, value: int) -> "DeviceState":
        """Create DeviceState from register value.

        Args:
            value: Machine state register value (0-99)

        Returns:
            Corresponding DeviceState, or UNKNOWN if invalid

        Example:
            >>> state = DeviceState.from_register_value(4)
            >>> assert state == DeviceState.AC_OPERATION
            >>> unknown = DeviceState.from_register_value(999)
            >>> assert unknown == DeviceState.UNKNOWN
        """
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN

    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.get_display_name()} ({self.value})"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"DeviceState.{self.name}"
