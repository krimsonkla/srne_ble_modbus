"""Configurable select entity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from ..config_loader import get_register_definition
from .configurable_base import ConfigurableBaseEntity
from ..coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ConfigurableSelect(ConfigurableBaseEntity, SelectEntity):
    """Select entity configured from YAML."""

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_config: dict[str, Any],
    ) -> None:
        """Initialize the select.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict
            device_config: Full device configuration with registers
        """
        super().__init__(coordinator, entry, config)

        self._device_config = device_config

        # Build options mapping
        # YAML format: options: {0: "Solar First", 1: "Utility First", 2: "Battery First"}
        # Where keys are register values and values are human-readable labels
        self._options_config = config["options"]

        # Options list should contain human-readable labels
        self._attr_options = list(self._options_config.values())

        # Mappings for conversion - ensure keys are integers
        self._value_to_label = {
            int(k): v for k, v in self._options_config.items()
        }  # {0: "Solar First", ...}
        self._label_to_value = {
            v: int(k) for k, v in self._options_config.items()
        }  # {"Solar First": 0, ...}

        _LOGGER.debug(
            "Initialized select entity %s with %d options: %s",
            config.get("name"),
            len(self._attr_options),
            self._label_to_value,
        )

        # Optimistic state
        self._optimistic = config.get("optimistic", False)
        self._optimistic_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        # Prefer optimistic state during pending writes
        if self._optimistic_option is not None:
            return self._optimistic_option

        # Use confirmed state
        if not self.coordinator.data:
            return None

        # CRITICAL FIX: Use register name, not entity_id
        register_key = self._config["register"]
        raw_value = self._get_coordinator_value(register_key)

        if raw_value is None:
            _LOGGER.debug("No data for register %s", register_key)
            return None

        # CRITICAL FIX: Convert to integer (coordinator stores ints, but be defensive)
        try:
            numeric_value = int(raw_value)
        except (ValueError, TypeError) as err:
            _LOGGER.debug(
                "Invalid value type for %s: %s (type=%s) - %s",
                register_key,
                raw_value,
                type(raw_value).__name__,
                err,
            )
            return None

        # Map value to label
        display_label = self._value_to_label.get(numeric_value)

        if display_label is None:
            _LOGGER.debug(
                "Unknown value %d for %s (valid options: %s)",
                numeric_value,
                register_key,
                list(self._value_to_label.keys()),
            )
            # Fallback: show numeric value as string
            return str(numeric_value)

        _LOGGER.debug(
            "Resolved %s: numeric=%d -> label='%s'",
            register_key,
            numeric_value,
            display_label,
        )

        return display_label

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option not in self._attr_options:
            raise HomeAssistantError(f"Invalid option: {option}")

        # Get register value for the selected label
        raw_value = self._label_to_value.get(option)
        if raw_value is None:
            raise HomeAssistantError(
                f"Cannot find numeric value for option '{option}' in {self._attr_name}"
            )

        # Ensure value is an integer (critical for struct.pack in modbus write)
        try:
            value = int(raw_value)
        except (ValueError, TypeError) as err:
            raise HomeAssistantError(
                f"Invalid value type for option '{option}': {raw_value} ({type(raw_value).__name__})"
            ) from err

        # Validate value is in valid register range
        if not 0 <= value <= 0xFFFF:
            raise HomeAssistantError(
                f"Value {value} for option '{option}' is out of valid range (0-65535)"
            )

        _LOGGER.info(
            "Setting %s to: %s (value=%d, type=%s)",
            self._attr_name,
            option,
            value,
            type(value).__name__,
        )

        # Optimistic update
        if self._optimistic:
            self._optimistic_option = option
            self.async_write_ha_state()

        try:
            # Get register name
            register_name = self._config["register"]

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
                # Revert optimistic state
                if self._optimistic:
                    self._optimistic_option = None
                    self.async_write_ha_state()
                raise HomeAssistantError(
                    f"Failed to write to register 0x{register_address:04X}. Check BLE connection."
                )

            _LOGGER.info(
                "%s set to %s successfully",
                self._attr_name,
                option,
            )

        except Exception as err:
            # Revert optimistic state
            if self._optimistic:
                self._optimistic_option = None
                self.async_write_ha_state()
            _LOGGER.error("Error setting %s: %s", self._attr_name, err)
            raise

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state once confirmed
        if self._optimistic and self._optimistic_option is not None:
            # CRITICAL FIX: Use register key, not entity_id
            register_key = self._config["register"]
            confirmed_value = self._get_coordinator_value(register_key)

            if confirmed_value is not None:
                try:
                    numeric_value = int(confirmed_value)
                    confirmed_option = self._value_to_label.get(numeric_value)

                    if confirmed_option == self._optimistic_option:
                        _LOGGER.debug(
                            "Select %s confirmed: %s (value=%d)",
                            self._attr_name,
                            confirmed_option,
                            numeric_value,
                        )
                        self._optimistic_option = None
                    else:
                        _LOGGER.debug(
                            "Select %s mismatch: expected '%s', got '%s' (value=%d)",
                            self._attr_name,
                            self._optimistic_option,
                            confirmed_option,
                            numeric_value,
                        )
                        # Clear optimistic state on mismatch
                        self._optimistic_option = None
                except (ValueError, TypeError) as err:
                    _LOGGER.debug(
                        "Invalid confirmed value for %s: %s - %s",
                        self._attr_name,
                        confirmed_value,
                        err,
                    )
                    self._optimistic_option = None

        super()._handle_coordinator_update()
