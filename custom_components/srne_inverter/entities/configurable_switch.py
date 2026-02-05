# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""Configurable switch entity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from ..config_loader import get_register_definition
from .configurable_base import ConfigurableBaseEntity
from ..coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ConfigurableSwitch(ConfigurableBaseEntity, SwitchEntity):
    """Switch entity configured from YAML."""

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_config: dict[str, Any],
    ) -> None:
        """Initialize the switch.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict
            device_config: Full device configuration with registers
        """
        super().__init__(coordinator, entry, config)

        self._device_config = device_config

        # Set switch-specific attributes
        if device_class := config.get("device_class"):
            try:
                self._attr_device_class = SwitchDeviceClass(device_class.upper())
            except (ValueError, AttributeError):
                try:
                    self._attr_device_class = SwitchDeviceClass(device_class)
                except ValueError:
                    _LOGGER.debug(
                        "Invalid device_class '%s' for switch %s",
                        device_class,
                        self._attr_name,
                    )

        # Optimistic state handling (always enabled like manual switch)
        self._optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if switch is on."""
        # Prefer optimistic state during pending writes
        if self._optimistic_state is not None:
            return self._optimistic_state

        # Get confirmed state
        return self._get_confirmed_state()

    def _get_confirmed_state(self) -> bool | None:
        """Get confirmed state from coordinator data."""
        if not self.coordinator.data:
            return None

        # Check if using state_key (e.g., machine_state) with state_mapping
        if state_key := self._config.get("state_key"):
            state_value = self._get_coordinator_value(state_key)

            if state_value is None:
                return None

            # Check state mapping
            # Note: YAML 1.1 parses "on"/"off" as booleans True/False
            if state_mapping := self._config.get("state_mapping"):
                # Try both string keys and boolean keys (YAML quirk)
                on_values = state_mapping.get("on", state_mapping.get(True, []))
                off_values = state_mapping.get("off", state_mapping.get(False, []))

                if state_value in on_values:
                    return True
                elif state_value in off_values:
                    return False
                else:
                    return None  # Unknown state
        # Check if using separate state register
        elif state_register := self._config.get("state_register"):
            state_key = f"state_{self._config['entity_id']}"
            state_value = self._get_coordinator_value(state_key)

            if state_value is None:
                return None

            # Check state mapping
            # Note: YAML 1.1 parses "on"/"off" as booleans True/False
            if state_mapping := self._config.get("state_mapping"):
                # Try both string keys and boolean keys (YAML quirk)
                on_values = state_mapping.get("on", state_mapping.get(True, []))
                off_values = state_mapping.get("off", state_mapping.get(False, []))

                if state_value in on_values:
                    return True
                elif state_value in off_values:
                    return False
                else:
                    return None  # Unknown state
        else:
            # Use direct register value
            data_key = self._config["entity_id"]
            value = self._get_coordinator_value(data_key)

            if value is None:
                return None

            on_value = self._config["on_value"]
            return value == on_value

        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_write_value(self._config["on_value"], True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_write_value(self._config["off_value"], False)

    async def _async_write_value(self, value: int, optimistic_state: bool) -> None:
        """Write value to register.

        Args:
            value: Value to write
            optimistic_state: Optimistic state to set (True=ON, False=OFF)
        """
        _LOGGER.info(
            "Setting %s to %s (value=%d)",
            self._attr_name,
            "ON" if optimistic_state else "OFF",
            value,
        )

        # Optimistic update for instant UI feedback (always enabled like manual switch)
        self._optimistic_state = optimistic_state
        self.async_write_ha_state()

        try:
            # Get register name
            register_name = self._config.get("command_register") or self._config.get(
                "register"
            )
            if not register_name:
                raise HomeAssistantError("No register configured for switch")

            # Look up register definition
            reg_def = get_register_definition(self._device_config, register_name)
            if not reg_def:
                raise HomeAssistantError(
                    f"Register definition '{register_name}' not found"
                )

            # Get register address from definition
            register_address = reg_def.get("_address_int") or reg_def["address"]

            # Write to register
            success = await self.coordinator.async_write_register(
                register_address, value
            )

            if not success:
                # Revert optimistic state on failure
                self._optimistic_state = None
                self.async_write_ha_state()
                raise HomeAssistantError(
                    f"Failed to write to register 0x{register_address:04X}. Check BLE connection."
                )

            _LOGGER.info(
                "%s command sent successfully to register 0x%04X",
                self._attr_name,
                register_address,
            )

        except Exception as err:
            # Revert optimistic state on error
            self._optimistic_state = None
            self.async_write_ha_state()
            _LOGGER.error("Error setting %s: %s", self._attr_name, err)
            raise

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state once confirmed (matches manual switch behavior)
        if self._optimistic_state is not None:
            confirmed = self._get_confirmed_state()
            if confirmed is not None and confirmed == self._optimistic_state:
                _LOGGER.debug(
                    "Switch %s state confirmed: %s",
                    self._attr_name,
                    confirmed,
                )
                self._optimistic_state = None

        super()._handle_coordinator_update()
