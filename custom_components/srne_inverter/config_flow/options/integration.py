"""Integration settings options flow steps.

This module provides the IntegrationOptionsMixin for handling integration-level
settings that don't directly control the inverter hardware:

- Inverter password for write operations
- Polling interval and communication timeouts
- Entity type filtering (enable/disable sensors, selects, numbers)
- Feature categories (diagnostic, calculated, energy dashboard)
- Failed register cache management

Configuration Categories:
    - Integration Settings: Password, communication, logging
    - Update Interval: Polling frequency
    - Features: Enable/disable entity types and categories

The failed register cache can be cleared to force a re-scan of all registers,
useful after firmware updates or when troubleshooting connectivity issues.
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


class IntegrationOptionsMixin:
    """Mixin for integration settings-related options flow steps."""

    async def async_step_integration(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure integration settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Check if user requested to clear failed registers
                if user_input.pop("clear_failed_registers", False):
                    coordinator = self.hass.data.get(DOMAIN, {}).get(
                        self.config_entry.entry_id
                    )
                    if coordinator:
                        _LOGGER.info("User requested to clear failed register cache")
                        try:
                            await coordinator.clear_failed_registers()
                            # Show success message and return to menu
                            return self.async_show_form(
                                step_id="integration",
                                data_schema=vol.Schema({}),
                                description_placeholders={
                                    "description": (
                                        "✅ Success!\n\n"
                                        "Failed register cache cleared.\n"
                                        "All registers will be re-scanned on next update.\n\n"
                                        "Check logs for re-scan progress.\n\n"
                                        "ℹ️ Close this dialog to return to menu"
                                    )
                                },
                            )
                        except Exception as err:
                            errors["base"] = "clear_failed_error"
                            _LOGGER.error("Failed to clear register cache: %s", err)
                    else:
                        errors["base"] = "coordinator_not_found"
                        _LOGGER.error("Coordinator not found, cannot clear cache")

                # Save options changes
                new_options = {**self.config_entry.options, **user_input}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, options=new_options
                )

                # Save password to config_entry.data if provided
                if "inverter_password" in user_input:
                    password_value = user_input["inverter_password"]
                    new_data = {
                        **self.config_entry.data,
                        "inverter_password": password_value,
                    }
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )
                    _LOGGER.info("Inverter password updated: %s", password_value)

                # Return to main menu
                return await self.async_step_init()
            except ValueError as err:
                errors["base"] = str(err)
                _LOGGER.error("Validation error in integration settings: %s", err)

        current_options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    "inverter_password",
                    description={
                        "suggested_value": self.config_entry.data.get(
                            "inverter_password", 1111
                        )
                    },
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=9999999)),
                vol.Optional(
                    "polling_interval",
                    default=current_options.get("polling_interval", 30),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=300,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    "command_delay_write",
                    default=current_options.get("command_delay_write", 0.1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=5.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    "batch_read_delay",
                    default=current_options.get("batch_read_delay", 0.1),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=2.0,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(
                    "connection_timeout",
                    default=current_options.get("connection_timeout", 2000),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1000,
                        max=10000,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="ms",
                    )
                ),
                vol.Optional(
                    "retry_attempts",
                    default=current_options.get("retry_attempts", 3),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    "log_modbus_traffic",
                    default=current_options.get("log_modbus_traffic", False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    "clear_failed_registers",
                    default=False,
                    description={"suggested_value": False},
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="integration",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "Configure integration settings.\n\n"
                    "🔐 INVERTER PASSWORD:\n"
                    "Optional password for writing configuration registers.\n"
                    "Common defaults:\n"
                    "  • 4321 - Menu/Setting Password\n"
                    "  • 0000 - Grid Parameter Password\n"
                    "  • 111111 or 1111 - Software/App Password\n"
                    "Set to 0 if no password required.\n"
                    "Required for battery type, voltages, and other critical settings.\n\n"
                    "⚙️ COMMUNICATION SETTINGS:\n"
                    "These settings control how the integration communicates with the inverter.\n"
                    "Default values are optimized for BLE performance.\n"
                    "Only modify if experiencing connection issues.\n\n"
                    "⚠️ CLEAR FAILED REGISTERS:\n"
                    "Check this box to clear the cached list of unsupported registers.\n"
                    "This forces a re-scan of ALL registers on next update.\n"
                    "Useful after firmware updates or for troubleshooting.\n\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )

    async def async_step_update_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure polling interval."""
        if user_input is not None:
            # Save changes
            new_options = {**self.config_entry.options, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=new_options
            )
            # Return to main menu
            return await self.async_step_init()

        current_interval = self.config_entry.options.get("update_interval", 60)

        schema = vol.Schema(
            {
                vol.Optional(
                    "update_interval",
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=300)),
            }
        )

        return self.async_show_form(
            step_id="update_interval",
            data_schema=schema,
            description_placeholders={
                "current_interval": str(current_interval),
            },
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enable/disable feature categories."""
        if user_input is not None:
            # Save changes
            new_options = {**self.config_entry.options, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=new_options
            )
            # Return to main menu
            return await self.async_step_init()

        current_options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    "enable_diagnostic_sensors",
                    default=current_options.get("enable_diagnostic_sensors", True),
                ): cv.boolean,
                vol.Optional(
                    "enable_calculated_sensors",
                    default=current_options.get("enable_calculated_sensors", True),
                ): cv.boolean,
                vol.Optional(
                    "enable_energy_dashboard",
                    default=current_options.get("enable_energy_dashboard", True),
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="features",
            data_schema=schema,
            description_placeholders={
                "description": (
                    "Enable or disable feature categories.\n\n"
                    "NOTE: Number and Select entities are now automatically controlled by hardware detection.\n"
                    "Use the 'Re-detect Hardware' option if your inverter's capabilities have changed.\n\n"
                    "• Diagnostic Sensors: Temperature, fault codes, etc.\n"
                    "• Calculated Sensors: Efficiency, ratios, derived metrics\n"
                    "• Energy Dashboard: Integration with Home Assistant Energy\n\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )

    async def async_step_redetect_hardware(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Re-detect hardware features after firmware update or hardware change."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if user confirmed re-detection
            if user_input.get("confirm_redetection", False):
                _LOGGER.info("User requested hardware feature re-detection")

                try:
                    # Get coordinator
                    coordinator_data = self.hass.data.get(DOMAIN, {}).get(
                        self.config_entry.entry_id
                    )
                    if not coordinator_data:
                        errors["base"] = "coordinator_not_found"
                        _LOGGER.error("Coordinator not found for re-detection")
                    else:
                        coordinator = coordinator_data.get("coordinator")
                        if not coordinator:
                            errors["base"] = "coordinator_not_found"
                            _LOGGER.error("Coordinator not found in data dict")
                        else:
                            # Import detector
                            from ...onboarding.detection import FeatureDetector

                            # Run detection
                            detector = FeatureDetector(coordinator)
                            detected = await detector.detect_all_features()

                            _LOGGER.info(
                                "Hardware re-detection complete: %d/%d features detected",
                                sum(detected.values()),
                                len(detected),
                            )

                            # Update config entry with new detected features
                            new_data = {
                                **self.config_entry.data,
                                "detected_features": detected,
                                "detection_timestamp": __import__("time").strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                ),
                            }
                            self.hass.config_entries.async_update_entry(
                                self.config_entry,
                                data=new_data,
                            )

                            # Reload integration to apply new features
                            _LOGGER.info("Reloading integration with updated features")
                            await self.hass.config_entries.async_reload(
                                self.config_entry.entry_id
                            )

                            # Show success message
                            return self.async_show_form(
                                step_id="redetect_hardware",
                                data_schema=vol.Schema({}),
                                description_placeholders={
                                    "description": (
                                        "✅ Success!\n\n"
                                        f"Hardware re-detection complete.\n"
                                        f"Detected {sum(detected.values())}/{len(detected)} features.\n\n"
                                        "Features detected:\n"
                                        + "\n".join(
                                            f"  {'✓' if v else '✗'} {k.replace('_', ' ').title()}"
                                            for k, v in detected.items()
                                        )
                                        + "\n\n"
                                        "Integration has been reloaded with new features.\n"
                                        "Check your entities list to see changes.\n\n"
                                        "ℹ️ Close this dialog to return to menu"
                                    )
                                },
                            )

                except Exception as err:
                    errors["base"] = "redetection_failed"
                    _LOGGER.error(
                        "Hardware re-detection failed: %s", err, exc_info=True
                    )
            else:
                # User didn't confirm, return to menu
                return await self.async_step_init()

        # Show confirmation form
        schema = vol.Schema(
            {
                vol.Required("confirm_redetection", default=False): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="redetect_hardware",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "🔄 RE-DETECT HARDWARE FEATURES\n\n"
                    "This will:\n"
                    "1. Probe your inverter to detect available features\n"
                    "2. Update which entities are visible/hidden\n"
                    "3. Reload the integration with new settings\n\n"
                    "When to use:\n"
                    "• After inverter firmware update\n"
                    "• After hardware modifications\n"
                    "• If entities are missing or incorrect\n\n"
                    "⏱️ Detection takes ~5-10 seconds\n\n"
                    "⚠️ The integration will reload during this process.\n\n"
                    "✓ Check the box below to confirm and start re-detection\n\n"
                    "ℹ️ Submit to proceed, or close dialog to cancel"
                ),
            },
        )
