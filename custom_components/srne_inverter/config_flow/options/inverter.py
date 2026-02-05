"""Inverter output configuration options flow steps.

This module provides the InverterOptionsMixin for handling inverter output
configuration:

- Output voltage and frequency selection
- AC input range (narrow/wide)
- Charge source priority (PV/AC/Hybrid/PV-only)
- Output priority (Solar first/Mains first/SBU)
- Power saving mode

Critical Safety:
    Output voltage and frequency MUST match your regional grid standards:
    - North America: 120V, 60Hz
    - Europe/UK: 230V, 50Hz
    - Japan: 100V, 50Hz or 60Hz

    Incorrect settings can damage connected equipment.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class InverterOptionsMixin:
    """Mixin for inverter output-related options flow steps."""

    async def async_step_inverter_output(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure inverter output (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Try dynamic validation and submission first
                if self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "inverter_output", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
                else:
                    # Fallback validation path
                    validated = await self.validate_inverter_output_settings(user_input)
                    if validated:
                        # Get coordinator for device config and write access
                        # Coordinator is stored in hass.data[DOMAIN][entry_id]["coordinator"]
                        data = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
                        coordinator = data.get("coordinator") if data else None
                        if coordinator and hasattr(coordinator, "_device_config"):
                            # Write to inverter first
                            write_errors = await self._write_config_to_inverter(
                                user_input, coordinator._device_config
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
                _LOGGER.error("Validation error in inverter_output settings: %s", err)

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("inverter_output")

        if dynamic_schema is not None:
            # Check if dynamic schema has any actual fields (not empty)
            has_fields = len(dynamic_schema.schema) > 0

            if not has_fields:
                # No inverter settings available - show info message and return to menu
                _LOGGER.info(
                    "No inverter output settings available from device - page hidden"
                )
                return self.async_show_form(
                    step_id="inverter_output",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "description": (
                            "ℹ️ NO INVERTER OUTPUT SETTINGS AVAILABLE\n\n"
                            "No inverter output settings could be read from your inverter.\n"
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

            # Use dynamic schema from YAML
            return self.async_show_form(
                step_id="inverter_output",
                data_schema=dynamic_schema,
                errors=errors,
                description_placeholders={
                    "description": (
                        "Configure inverter output settings (YAML-driven schema).\n\n"
                        "✓ Values shown are current inverter readings\n"
                        "⚠️ CRITICAL: Output voltage and frequency must match your region\n"
                        "  • North America: 120V, 60Hz\n"
                        "  • Europe: 230V, 50Hz\n"
                        "  • UK: 230V, 50Hz\n"
                        "  • Japan: 100V, 50Hz/60Hz\n"
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
                step_id="inverter_output",
                data_schema=vol.Schema({}),
                errors={"base": "no_inverter_data"},
                description_placeholders={
                    "description": "⚠️ Cannot read settings from inverter. Check connection and try again."
                },
            )

        # Build dynamic schema - only include fields with available data
        schema_dict = {}

        if "output_voltage" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "output_voltage",
                    default=coordinator.data["output_voltage"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["100", "110", "120", "127", "220", "230", "240"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        if "output_frequency" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "output_frequency",
                    default=coordinator.data["output_frequency"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["50", "60"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        if "ac_input_range" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "ac_input_range",
                    default=coordinator.data["ac_input_range"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value="narrow", label="Narrow (UPS Mode)"
                        ),
                        selector.SelectOptionDict(
                            value="wide", label="Wide (Appliance Mode)"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        if "charge_source_priority" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "charge_source_priority",
                    default=coordinator.data["charge_source_priority"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value="pv_priority", label="PV Priority (AC Backup)"
                        ),
                        selector.SelectOptionDict(
                            value="ac_priority", label="AC Priority"
                        ),
                        selector.SelectOptionDict(value="hybrid", label="Hybrid Mode"),
                        selector.SelectOptionDict(value="pv_only", label="PV Only"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        if "power_saving_mode" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "power_saving_mode",
                    default=coordinator.data["power_saving_mode"],
                )
            ] = cv.boolean

        if "output_priority" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "output_priority",
                    default=coordinator.data["output_priority"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="0", label="Solar First"),
                        selector.SelectOptionDict(value="1", label="Mains First"),
                        selector.SelectOptionDict(
                            value="2", label="SBU (Solar-Battery-Utility)"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(schema_dict)

        available_count = len(schema_dict)

        return self.async_show_form(
            step_id="inverter_output",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    f"Configure inverter output settings (showing {available_count} available settings from inverter).\n\n"
                    "✓ Values shown are current inverter readings\n"
                    "⚠️ CRITICAL: Output voltage and frequency must match your region\n"
                    "  • North America: 120V, 60Hz\n"
                    "  • Europe: 230V, 50Hz\n"
                    "  • UK: 230V, 50Hz\n"
                    "  • Japan: 100V, 50Hz/60Hz\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )
