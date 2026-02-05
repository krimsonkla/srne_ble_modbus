"""Device entity representing the inverter device.

A Device is an entity that represents the physical SRNE inverter with its
configuration and state.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from ..value_objects import DeviceState


@dataclass
class Device:
    """Domain entity representing an SRNE inverter device.

    A Device encapsulates:
    - Device identification (address, model, serial number)
    - Device configuration (settings, capabilities)
    - Device state (operational state, connection status)
    - Register definitions for this device model

    Attributes:
        address: BLE MAC address or device identifier
        name: Human-readable device name
        model: Device model (e.g., "HF2420")
        serial_number: Device serial number
        firmware_version: Firmware version string
        state: Current operational state
        is_connected: Whether device is currently connected
        registers: List of available registers for this device
        config: Device-specific configuration

    Example:
        >>> device = Device(
        ...     address="AA:BB:CC:DD:EE:FF",
        ...     name="Solar Inverter",
        ...     model="HF2420",
        ...     state=DeviceState.AC_OPERATION,
        ... )
        >>> assert device.is_operational
        >>> device.update_state(DeviceState.STANDBY)
        >>> assert not device.is_operational
    """

    # Identity
    address: str
    name: str
    model: str = ""
    serial_number: str = ""
    firmware_version: str = ""

    # State
    state: DeviceState = DeviceState.UNKNOWN
    is_connected: bool = False

    # Configuration
    registers: List[Any] = field(default_factory=list)  # List[Register]
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate device attributes."""
        if not self.address:
            raise ValueError("Device address cannot be empty")
        if not self.name:
            raise ValueError("Device name cannot be empty")

    @property
    def is_operational(self) -> bool:
        """Check if device is in operational state.

        Returns:
            True if device is actively working

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> device.state = DeviceState.AC_OPERATION
            >>> assert device.is_operational
        """
        return self.state.is_operational if self.state else False

    @property
    def is_error(self) -> bool:
        """Check if device is in error state.

        Returns:
            True if device has encountered an error

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> device.state = DeviceState.ERROR
            >>> assert device.is_error
        """
        return self.state.is_error if self.state else False

    @property
    def allows_writes(self) -> bool:
        """Check if device state allows register writes.

        Returns:
            True if register writes are allowed

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> device.state = DeviceState.STANDBY
            >>> assert device.allows_writes
        """
        return self.state.allows_writes if self.state else False

    def update_state(self, new_state: DeviceState) -> None:
        """Update device operational state.

        Args:
            new_state: New device state

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> device.update_state(DeviceState.AC_OPERATION)
            >>> assert device.state == DeviceState.AC_OPERATION
        """
        self.state = new_state

    def update_connection_status(self, connected: bool) -> None:
        """Update device connection status.

        Args:
            connected: True if device is connected

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> device.update_connection_status(True)
            >>> assert device.is_connected
        """
        self.is_connected = connected

    def get_register_by_name(self, name: str) -> Optional[Any]:
        """Get register by name.

        Args:
            name: Register name to find

        Returns:
            Register if found, None otherwise

        Example:
            >>> from .register import Register
            >>> from ..value_objects import RegisterAddress
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> reg = Register(RegisterAddress(0x0100), "battery_voltage")
            >>> device.registers = [reg]
            >>> found = device.get_register_by_name("battery_voltage")
            >>> assert found == reg
        """
        for register in self.registers:
            if register.name == name:
                return register
        return None

    def get_register_by_address(self, address: int) -> Optional[Any]:
        """Get register by address.

        Args:
            address: Register address to find

        Returns:
            Register if found, None otherwise

        Example:
            >>> from .register import Register
            >>> from ..value_objects import RegisterAddress
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter")
            >>> reg = Register(RegisterAddress(0x0100), "battery_voltage")
            >>> device.registers = [reg]
            >>> found = device.get_register_by_address(0x0100)
            >>> assert found == reg
        """
        for register in self.registers:
            if int(register.address) == address:
                return register
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary representation.

        Returns:
            Dictionary with device attributes

        Example:
            >>> device = Device("AA:BB:CC:DD:EE:FF", "Inverter", model="HF2420")
            >>> data = device.to_dict()
            >>> assert data["address"] == "AA:BB:CC:DD:EE:FF"
            >>> assert data["model"] == "HF2420"
        """
        return {
            "address": self.address,
            "name": self.name,
            "model": self.model,
            "serial_number": self.serial_number,
            "firmware_version": self.firmware_version,
            "state": self.state.value if self.state else 0,
            "state_name": self.state.name if self.state else "UNKNOWN",
            "is_connected": self.is_connected,
            "is_operational": self.is_operational,
            "is_error": self.is_error,
            "allows_writes": self.allows_writes,
            "register_count": len(self.registers),
            "config": self.config,
        }

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Device({self.name} @ {self.address}, "
            f"model={self.model}, state={self.state.name})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"Device(address={self.address!r}, name={self.name!r}, "
            f"model={self.model!r}, state={self.state!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on address (entity identity).

        Two devices are the same if they have the same address,
        regardless of other attributes.

        Args:
            other: Object to compare with

        Returns:
            True if same address, False otherwise
        """
        if not isinstance(other, Device):
            return False
        return self.address == other.address

    def __hash__(self) -> int:
        """Hash based on address for use in sets/dicts."""
        return hash(self.address)
