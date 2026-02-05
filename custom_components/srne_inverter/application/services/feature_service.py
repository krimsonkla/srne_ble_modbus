# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text

"""Feature validation service for hardware features."""

from __future__ import annotations

from typing import Any


class FeatureService:
    """Service for validating hardware features and register availability.

    Single responsibility: Check if registers are enabled based on
    hardware feature flags and address ranges.
    """

    def __init__(self, device_config: dict[str, Any]) -> None:
        """Initialize feature service.

        Args:
            device_config: Device configuration with features and feature_ranges
        """
        device = device_config.get("device", {})
        self._features = device.get("features", {})
        self._feature_ranges = device.get("feature_ranges", {})
        self._disabled_addresses = self._build_disabled_address_set()

    def _build_disabled_address_set(self) -> set[int]:
        """Build set of disabled register addresses.

        Returns:
            Set of disabled register addresses
        """
        disabled = set()

        for feature_name, feature_enabled in self._features.items():
            if not feature_enabled:
                for range_def in self._feature_ranges.get(feature_name, []):
                    start = range_def.get("start")
                    end = range_def.get("end")

                    # Normalize hex strings to int
                    if isinstance(start, str):
                        start = int(start, 16 if start.startswith("0x") else 10)
                    if isinstance(end, str):
                        end = int(end, 16 if end.startswith("0x") else 10)

                    disabled.update(range(start, end + 1))

        return disabled

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled.

        Args:
            feature_name: Name of the feature

        Returns:
            True if feature is enabled, False otherwise
        """
        return self._features.get(feature_name, False)

    def is_address_enabled(self, address: int) -> bool:
        """Check if a register address is enabled (not in disabled range).

        Args:
            address: Register address

        Returns:
            True if address is enabled, False if in disabled feature range
        """
        return address not in self._disabled_addresses

    def is_register_enabled_by_features(
        self, config: dict[str, Any], register_name: str
    ) -> bool:
        """Check if a register is enabled by hardware features.

        Args:
            config: Full device configuration
            register_name: Register name to check

        Returns:
            True if register is in enabled feature range or no feature restriction,
            False if register is in disabled feature range
        """
        reg_def = config.get("registers", {}).get(register_name)
        if not reg_def:
            return True  # Unknown register, assume enabled

        address = reg_def.get("address")
        if address is None:
            return True

        # Normalize hex strings to int
        if isinstance(address, str):
            address = int(address, 16 if address.startswith("0x") else 10)

        return self.is_address_enabled(address)

    def get_disabled_registers(self, registers: dict[str, Any]) -> set[str]:
        """Get set of register names that are disabled by features.

        Args:
            registers: Dictionary of register definitions

        Returns:
            Set of register names in disabled feature ranges
        """
        disabled = set()

        for reg_name, reg_def in registers.items():
            address = reg_def.get("address")
            if address is None:
                continue

            # Normalize hex strings to int
            if isinstance(address, str):
                address = int(address, 16 if address.startswith("0x") else 10)

            if not self.is_address_enabled(address):
                disabled.add(reg_name)

        return disabled
