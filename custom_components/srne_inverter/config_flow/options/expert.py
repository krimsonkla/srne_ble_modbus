"""Expert settings and presets options flow steps.

This module provides the ExpertOptionsMixin for advanced configuration:

Expert Settings:
    - Grid voltage thresholds (low/high)
    - Grid frequency thresholds (low/high)
    - Other advanced parameters that can damage equipment if misconfigured

Configuration Presets:
    - Off-Grid Solar: Optimized for standalone solar + battery
    - Grid-Tied: Grid backup with solar priority
    - UPS Mode: Grid power with battery backup
    - Time-of-Use: Charge during cheap hours, discharge during peak

Safety:
    Expert settings require explicit acknowledgment before changes can be saved.
    All changes are logged for audit purposes. Incorrect values can damage
    equipment or violate grid connection requirements.

Presets:
    Configuration presets provide quick setup for common use cases. They update
    multiple settings at once while preserving other user configurations.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from ..base import CONFIGURATION_PRESETS
from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ExpertOptionsMixin:
    """Mixin for expert settings and presets options flow steps."""

    async def async_step_expert(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure expert settings (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Require acknowledgment
            if not user_input.get("expert_mode_acknowledged", False):
                errors["base"] = "expert_acknowledgment_required"
            else:
                try:
                    # Try dynamic validation and submission first
                    if self._schema_builder:
                        # Remove acknowledgment from input before processing
                        register_input = {
                            k: v
                            for k, v in user_input.items()
                            if k != "expert_mode_acknowledged"
                        }
                        success, error_dict = (
                            await self._handle_form_submission_dynamic(
                                "expert_settings", register_input
                            )
                        )
                        if success:
                            return await self.async_step_init()
                        errors.update(error_dict)
                    else:
                        # Fallback approach
                        # Get coordinator for device config and write access
                        # Coordinator is stored in hass.data[DOMAIN][entry_id]["coordinator"]
                        data = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
                        coordinator = data.get("coordinator") if data else None
                        if coordinator and hasattr(coordinator, "_device_config"):
                            # Remove acknowledgment from input before writing
                            register_input = {
                                k: v
                                for k, v in user_input.items()
                                if k != "expert_mode_acknowledged"
                            }
                            # Write to inverter first
                            write_errors = await self._write_config_to_inverter(
                                register_input, coordinator._device_config
                            )
                            if write_errors:
                                errors.update(write_errors)

                        # Only save locally if writes succeeded (or no coordinator)
                        if not errors:
                            new_options = {**self.config_entry.options, **user_input}
                            self.hass.config_entries.async_update_entry(
                                self.config_entry, options=new_options
                            )
                            # Return to main menu
                            return await self.async_step_init()
                except ValueError as err:
                    errors["base"] = str(err)
                    _LOGGER.error("Validation error in expert settings: %s", err)

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("expert_settings")

        if dynamic_schema is not None:
            # Check if dynamic schema has any actual fields (not empty)
            has_fields = len(dynamic_schema.schema) > 0

            if not has_fields:
                # No expert settings available - show info message and return to menu
                _LOGGER.info("No expert settings available from device - page hidden")
                return self.async_show_form(
                    step_id="expert",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "description": (
                            "ℹ️ NO EXPERT SETTINGS AVAILABLE\n\n"
                            "No expert settings could be read from your inverter.\n"
                            "This can happen if:\n"
                            "• The registers haven't been read yet\n"
                            "• Your inverter model doesn't support these settings\n"
                            "• The registers are disabled by hardware features\n\n"
                            "Try:\n"
                            "• Wait for the next data update\n"
                            "• Check 'Integration Settings' → 'Clear Failed Registers'\n"
                            "• Use 'Re-detect Hardware Features'\n\n"
                            "ℹ️ Close this dialog to return to menu"
                        )
                    },
                )

            # Add expert mode acknowledgment to dynamic schema
            schema_dict = {
                vol.Required("expert_mode_acknowledged", default=False): cv.boolean,
            }
            # Merge with dynamic schema fields
            for key, value in dynamic_schema.schema.items():
                schema_dict[key] = value

            expert_schema = vol.Schema(schema_dict)

            # Use dynamic schema from YAML
            return self.async_show_form(
                step_id="expert",
                data_schema=expert_schema,
                errors=errors,
                description_placeholders={
                    "description": (
                        "⚠️ EXPERT SETTINGS (YAML-driven schema)\n\n"
                        "These settings can DAMAGE equipment if configured incorrectly.\n"
                        "Only proceed if you fully understand the implications.\n\n"
                        "✓ Values shown are current inverter readings\n"
                        "⚠️ All changes are logged for audit purposes\n\n"
                        "You must acknowledge the warning to continue.\n\n"
                        "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                    ),
                },
            )

        # Fallback to hardcoded schema if dynamic unavailable
        # During onboarding, config_entry doesn't exist yet - skip coordinator checks
        if hasattr(self, "config_entry") and self.config_entry is not None:
            # Coordinator is stored in hass.data[DOMAIN][entry_id]["coordinator"]
            data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
            coordinator = data.get("coordinator") if data else None
        else:
            coordinator = None

        # Check if coordinator has data
        # Note: coordinator.data can be an empty dict {} during normal operation,
        # only fail if coordinator is missing or data is None (not initialized)
        if (
            not coordinator
            or not hasattr(coordinator, "data")
            or coordinator.data is None
        ):
            return self.async_show_form(
                step_id="expert",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "expert_mode_acknowledged", default=False
                        ): cv.boolean,
                    }
                ),
                errors={"base": "no_inverter_data"},
                description_placeholders={
                    "description": "⚠️ Cannot read settings from inverter. Check connection and try again."
                },
            )

        # Build dynamic schema - only include fields with available data
        schema_dict = {}

        # Always require expert mode acknowledgment
        schema_dict[vol.Required("expert_mode_acknowledged", default=False)] = (
            cv.boolean
        )

        if "grid_voltage_low" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "grid_voltage_low",
                    default=coordinator.data["grid_voltage_low"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=90,
                    max=280,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="V",
                )
            )

        if "grid_voltage_high" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "grid_voltage_high",
                    default=coordinator.data["grid_voltage_high"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=90,
                    max=280,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="V",
                )
            )

        if "grid_frequency_low" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "grid_frequency_low",
                    default=coordinator.data["grid_frequency_low"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=45,
                    max=65,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="Hz",
                )
            )

        if "grid_frequency_high" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "grid_frequency_high",
                    default=coordinator.data["grid_frequency_high"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=45,
                    max=65,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="Hz",
                )
            )

        schema = vol.Schema(schema_dict)

        available_count = len(
            [k for k in schema_dict.keys() if k.schema != "expert_mode_acknowledged"]
        )

        return self.async_show_form(
            step_id="expert",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    f"⚠️ EXPERT SETTINGS (showing {available_count} available settings from inverter)\n\n"
                    "These settings can DAMAGE equipment if configured incorrectly.\n"
                    "Only proceed if you fully understand the implications.\n\n"
                    "✓ Values shown are current inverter readings\n"
                    "⚠️ All changes are logged for audit purposes\n\n"
                    "You must acknowledge the warning to continue.\n\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )

    async def async_step_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Apply configuration preset."""
        errors: dict[str, str] = {}

        if user_input is not None:
            preset_key = user_input.get("preset")
            if preset_key and preset_key in CONFIGURATION_PRESETS:
                preset = CONFIGURATION_PRESETS[preset_key]
                preset_settings = preset["settings"].copy()

                # Merge with current options
                new_options = {**self.config_entry.options, **preset_settings}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=new_options
                )

                # Return to main menu
                return await self.async_step_init()
            else:
                errors["base"] = "invalid_preset"

        # Build preset selection
        preset_options = [
            selector.SelectOptionDict(
                value=key, label=f"{preset['name']} - {preset['description']}"
            )
            for key, preset in CONFIGURATION_PRESETS.items()
        ]

        schema = vol.Schema(
            {
                vol.Required("preset"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=preset_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="presets",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "Apply a configuration preset for common use cases.\n\n"
                    "This will update multiple settings at once.\n"
                    "Your current settings will be preserved where not specified."
                ),
            },
        )
