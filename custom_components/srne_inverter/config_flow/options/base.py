"""Base options flow handler with shared utilities.

This module provides the base SRNEOptionsFlowHandler class with shared functionality
for all options flow steps. It includes:

- Dynamic schema building from YAML configuration
- User input validation and parsing
- Register value conversion and scaling
- Write operations to inverter via coordinator
- Main menu navigation

The base handler is extended by mixins for specific option categories:
- BatteryOptionsMixin: Battery configuration and management
- InverterOptionsMixin: Inverter output settings
- IntegrationOptionsMixin: Integration settings and features
- ExpertOptionsMixin: Expert settings and presets

Architecture:
    Uses the ConfigFlowSchemaBuilder for dynamic form generation based on YAML
    configuration. Validation and register writes happen through the coordinator,
    maintaining separation of concerns.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from ..helpers.schema_builder import ConfigFlowSchemaBuilder
from ..base import ConfigFlowValidationMixin
from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SRNEOptionsFlowHandler(config_entries.OptionsFlow, ConfigFlowValidationMixin):
    """Handle options flow for SRNE Inverter."""

    def __init__(self) -> None:
        """Initialize options flow.

        Note: self.config_entry is automatically provided by the parent
        OptionsFlow class as a property after instantiation by the framework.
        """
        self._current_section: str | None = None
        self._schema_builder: ConfigFlowSchemaBuilder | None = None

        # Initialize dynamic schema builder
        # Config will be loaded lazily when first accessed
        self._schema_builder = ConfigFlowSchemaBuilder()

    def _build_dynamic_schema(self, page_id: str) -> vol.Schema | None:
        """Build schema dynamically using YAML configuration.

        Args:
            page_id: Page identifier from config_pages in entities_pilot.yaml

        Returns:
            Voluptuous schema if schema builder is available, None otherwise
        """
        if not self._schema_builder:
            return None

        # Get current values from coordinator (only for options flow, not during onboarding)
        # During onboarding, config_entry doesn't exist yet, so we use empty defaults
        if not hasattr(self, "config_entry") or self.config_entry is None:
            # Onboarding flow - use empty defaults
            return None

        # Coordinator is stored in hass.data[DOMAIN][entry_id]["coordinator"]
        data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        coordinator = data.get("coordinator") if data else None
        if not coordinator:
            return None

        # Check if coordinator has data attribute (it's a coordinator object, not a dict)
        # Note: coordinator.data can be an empty dict {} during normal operation,
        # only fail if it's None (not initialized)
        if not hasattr(coordinator, "data") or coordinator.data is None:
            return None

        try:
            # Build schema with current values as defaults
            schema = self._schema_builder.build_schema(
                page_id, current_values=coordinator.data
            )
            return schema
        except Exception as e:
            _LOGGER.error("Error building dynamic schema for %s: %s", page_id, str(e))
            return None

    def _validate_dynamic_input(
        self, page_id: str, user_input: dict[str, Any], all_values: dict[str, Any]
    ) -> tuple[bool, dict[str, str]]:
        """Validate user input using dynamic validation rules.

        Args:
            page_id: Page identifier
            user_input: User input from form
            all_values: All current configuration values

        Returns:
            Tuple of (is_valid, error_dict)
        """
        if not self._schema_builder:
            return (True, {})

        try:
            return self._schema_builder.validate_user_input(
                page_id, user_input, all_values
            )
        except Exception as e:
            _LOGGER.error("Error validating dynamic input for %s: %s", page_id, str(e))
            return (True, {})

    def _parse_dynamic_input(
        self, user_input: dict[str, Any]
    ) -> dict[str, int | float | bool]:
        """Parse user input values to raw register values.

        Args:
            user_input: User input from form (scaled values)

        Returns:
            Dictionary of raw register values (unscaled)
        """
        if not self._schema_builder:
            return user_input

        try:
            return self._schema_builder.parse_user_input(user_input)
        except Exception as e:
            _LOGGER.error("Error parsing dynamic input: %s", str(e))
            return user_input

    async def _write_config_to_inverter(
        self, user_input: dict[str, Any], device_config: dict[str, Any]
    ) -> dict[str, str]:
        """Write configuration values to inverter registers.

        Args:
            user_input: User input dict with field names and values
            device_config: Device configuration with register definitions

        Returns:
            Dict of field_name -> error_key for any failed writes
        """
        errors = {}

        # Get coordinator (stored in hass.data[DOMAIN][entry_id]["coordinator"])
        data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        coordinator = data.get("coordinator") if data else None
        if not coordinator:
            _LOGGER.error("Coordinator not found, cannot write to inverter")
            return {"base": "coordinator_not_found"}

        registers_def = device_config.get("registers", {})

        # Write each field that maps to a writable register
        for field_name, value in user_input.items():
            # Skip special fields that aren't registers
            if field_name in [
                "clear_failed_registers",
                "expert_acknowledgment",
                "expert_mode_acknowledged",
            ]:
                continue

            # Find matching register definition
            reg_def = registers_def.get(field_name)
            if not reg_def:
                _LOGGER.debug("No register definition for field: %s", field_name)
                continue

            # Only write to writable registers
            reg_type = reg_def.get("type", "read")
            if reg_type not in ["write", "read_write"]:
                _LOGGER.debug("Skipping read-only register: %s", field_name)
                continue

            # Get register address
            address = reg_def.get("address")
            if address is None:
                _LOGGER.debug("Register %s has no address", field_name)
                continue

            # Convert hex string to int if needed
            if isinstance(address, str):
                address = int(address, 16 if address.startswith("0x") else 10)

            # Convert value to register format
            try:
                register_value = self._convert_value_to_register(value, reg_def)
            except (ValueError, TypeError) as err:
                _LOGGER.error("Failed to convert value for %s: %s", field_name, err)
                errors[field_name] = "invalid_value"
                continue

            # Write to inverter
            _LOGGER.info(
                "Writing %s = %s to register 0x%04X (raw value: %s)",
                field_name,
                value,
                address,
                register_value,
            )

            try:
                success = await coordinator.async_write_register(
                    address, register_value
                )

                if not success:
                    _LOGGER.error(
                        "Failed to write %s to register 0x%04X", field_name, address
                    )
                    errors[field_name] = "write_failed"
            except Exception as err:
                _LOGGER.error(
                    "Exception writing %s to register 0x%04X: %s",
                    field_name,
                    address,
                    err,
                )
                errors[field_name] = "write_failed"

        return errors

    def _convert_value_to_register(self, value: Any, reg_def: dict[str, Any]) -> int:
        """Convert user input value to raw register value.

        Args:
            value: User input value (float, int, str, bool)
            reg_def: Register definition with scaling, data_type, etc.

        Returns:
            Raw register value as integer
        """
        # Handle boolean values
        if isinstance(value, bool):
            return 1 if value else 0

        # Handle select options (string -> int mapping)
        if isinstance(value, str):
            # Check if register has values/options mapping
            values = reg_def.get("values", {})
            if values:
                # Find the key that matches this label
                for key, label in values.items():
                    if label == value:
                        return int(key)
            # If no mapping found, try to parse as int
            return int(value)

        # Handle numeric values with scaling
        scaling = reg_def.get("scaling", 1)
        if scaling != 1:
            # Unscale the value (e.g., 14.4V -> 144 with 0.1 scaling)
            return int(round(value / scaling))

        return int(value)

    async def _handle_form_submission_dynamic(
        self, page_id: str, user_input: dict[str, Any]
    ) -> tuple[bool, dict[str, str]]:
        """Handle form submission with dynamic validation and parsing.

        Args:
            page_id: Page identifier
            user_input: User input from form

        Returns:
            Tuple of (success, errors)
        """
        if not self._schema_builder:
            return (False, {})

        # Get current values (coordinator stored in hass.data[DOMAIN][entry_id]["coordinator"])
        data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        coordinator = data.get("coordinator") if data else None
        all_values = (
            {**coordinator.data, **user_input}
            if coordinator and coordinator.data
            else user_input
        )

        # Validate input
        is_valid, error_dict = self._validate_dynamic_input(
            page_id, user_input, all_values
        )

        if not is_valid:
            return (False, error_dict)

        # Parse input to raw register values
        parsed_input = self._parse_dynamic_input(user_input)

        # Write to inverter first (if coordinator available)
        if coordinator and hasattr(coordinator, "_device_config"):
            write_errors = await self._write_config_to_inverter(
                parsed_input, coordinator._device_config
            )
            if write_errors:
                return (False, write_errors)

        # Only save locally if writes succeeded (or no coordinator)
        new_options = {**self.config_entry.options, **parsed_input}
        self.hass.config_entries.async_update_entry(
            self.config_entry, options=new_options
        )

        return (True, {})

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options (main menu)."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "battery_config": "Battery Configuration (Inverter)",
                "battery_management": "Battery Management (Inverter)",
                "inverter_output": "Inverter Output (Inverter)",
                "expert": "Expert Settings (Inverter)",
                "integration": "Integration Settings",
                "update_interval": "Update Interval",
                "features": "Features (Sensors & Entities)",
                "hardware_features": "Hardware Features (Override Detection)",
                "user_preferences": "User Preferences (Show/Hide Groups)",
                "redetect_hardware": "Re-detect Hardware Features",
                "presets": "Configuration Presets",
            },
        )
