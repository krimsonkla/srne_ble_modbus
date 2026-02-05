"""Battery configuration options flow steps.

This module provides the BatteryOptionsMixin for handling battery-related
configuration options:

- Battery Configuration: Basic battery settings (voltage, capacity, type)
- Battery Management: Charge currents, SOC thresholds, battery chemistry

Both steps support:
- Dynamic schema building from YAML (with fallback to hardcoded schema)
- Live data from inverter as default values
- Validation before writing to inverter
- Direct register writes through coordinator

Safety:
    All battery settings are validated to ensure they match the actual battery
    chemistry and capacity to prevent damage to the battery system.
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


class BatteryOptionsMixin:
    """Mixin for battery-related options flow steps."""

    async def async_step_battery_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure battery configuration (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Try dynamic validation and submission first
                if self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "battery_config", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
            except ValueError as err:
                errors["base"] = str(err)
                _LOGGER.error("Validation error in essential settings: %s", err)

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("battery_config")

        if dynamic_schema is not None:
            # Check if dynamic schema has any actual fields (not empty)
            has_fields = len(dynamic_schema.schema) > 0

            if not has_fields:
                # No battery settings available - show info message
                _LOGGER.info(
                    "No battery config settings available from device - page hidden"
                )
                return self.async_show_form(
                    step_id="battery_config",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "description": (
                            "ℹ️ NO BATTERY CONFIGURATION SETTINGS AVAILABLE\n\n"
                            "No battery configuration settings could be read from your inverter.\n"
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
                step_id="battery_config",
                data_schema=dynamic_schema,
                errors=errors,
                description_placeholders={
                    "description": (
                        "Configure battery settings (YAML-driven schema).\n\n"
                        "✓ Values shown are current inverter readings\n"
                        "⚠️ CRITICAL: Settings must match your battery system\n"
                        "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                    ),
                },
            )

    async def async_step_battery_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure battery management (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Try dynamic validation and submission first
                if self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "battery_management", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
            except ValueError as err:
                errors["base"] = str(err)
                _LOGGER.error(
                    "Validation error in battery_management settings: %s", err
                )

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("battery_management")

        if dynamic_schema is not None:
            # Check if dynamic schema has any actual fields (not empty)
            has_fields = len(dynamic_schema.schema) > 0

            if not has_fields:
                # No battery management settings available - show info message
                _LOGGER.info(
                    "No battery management settings available from device - page hidden"
                )
                return self.async_show_form(
                    step_id="battery_management",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "description": (
                            "ℹ️ NO BATTERY MANAGEMENT SETTINGS AVAILABLE\n\n"
                            "No battery management settings could be read from your inverter.\n"
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
                step_id="battery_management",
                data_schema=dynamic_schema,
                errors=errors,
                description_placeholders={
                    "description": (
                        "Configure battery management settings (YAML-driven schema).\n\n"
                        "✓ Values shown are current inverter readings\n"
                        "⚠️ Battery type must match your battery chemistry\n"
                        "⚠️ Charge currents and SOC thresholds will be validated\n"
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
                step_id="battery_management",
                data_schema=vol.Schema({}),
                errors={"base": "no_inverter_data"},
                description_placeholders={
                    "description": "⚠️ Cannot read settings from inverter. Check connection and try again."
                },
            )

        # Build dynamic schema - only include fields with available data
        schema_dict = {}

        if "max_charge_current" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "max_charge_current",
                    default=coordinator.data["max_charge_current"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=200,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="A",
                )
            )

        if "max_ac_charge_current" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "max_ac_charge_current",
                    default=coordinator.data["max_ac_charge_current"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=200,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="A",
                )
            )

        if "pv_max_charge_current" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "pv_max_charge_current",
                    default=coordinator.data["pv_max_charge_current"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=150,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="A",
                )
            )

        if "discharge_stop_soc" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "discharge_stop_soc",
                    default=coordinator.data["discharge_stop_soc"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            )

        if "low_soc_alarm" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "low_soc_alarm",
                    default=coordinator.data["low_soc_alarm"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            )

        if "switch_to_ac_soc" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "switch_to_ac_soc",
                    default=coordinator.data["switch_to_ac_soc"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            )

        if "switch_to_battery_soc" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "switch_to_battery_soc",
                    default=coordinator.data["switch_to_battery_soc"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            )

        if "battery_type" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "battery_type",
                    default=coordinator.data["battery_type"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value="user_defined", label="User Defined"
                        ),
                        selector.SelectOptionDict(
                            value="sld", label="Sealed Lead Acid"
                        ),
                        selector.SelectOptionDict(
                            value="fld", label="Flooded Lead Acid"
                        ),
                        selector.SelectOptionDict(value="gel", label="GEL"),
                        selector.SelectOptionDict(
                            value="lifepo4_x14", label="LiFePO4 x14"
                        ),
                        selector.SelectOptionDict(
                            value="lifepo4_x15", label="LiFePO4 x15"
                        ),
                        selector.SelectOptionDict(
                            value="lifepo4_x16", label="LiFePO4 x16"
                        ),
                        selector.SelectOptionDict(
                            value="lifepo4_x7", label="LiFePO4 x7"
                        ),
                        selector.SelectOptionDict(
                            value="lifepo4_x8", label="LiFePO4 x8"
                        ),
                        selector.SelectOptionDict(
                            value="lifepo4_x9", label="LiFePO4 x9"
                        ),
                        selector.SelectOptionDict(
                            value="ternary_x7", label="Ternary Lithium x7"
                        ),
                        selector.SelectOptionDict(
                            value="ternary_x8", label="Ternary Lithium x8"
                        ),
                        selector.SelectOptionDict(
                            value="ternary_x13", label="Ternary Lithium x13"
                        ),
                        selector.SelectOptionDict(
                            value="ternary_x14", label="Ternary Lithium x14"
                        ),
                        selector.SelectOptionDict(
                            value="user_lithium", label="User-defined Lithium"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(schema_dict)

        available_count = len(schema_dict)

        return self.async_show_form(
            step_id="battery_management",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    f"Configure battery management settings (showing {available_count} available settings from inverter).\n\n"
                    "✓ Values shown are current inverter readings\n"
                    "⚠️ Battery type must match your battery chemistry\n"
                    "⚠️ SOC thresholds should be in ascending order\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )
