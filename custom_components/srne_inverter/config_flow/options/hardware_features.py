"""Hardware features and user preferences options flow steps.

This module provides options for:
- Hardware Feature Overrides: Allow users to override auto-detected hardware features
- User Preferences: Show/hide optional entity groups based on system configuration
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class HardwareFeaturesMixin:
    """Mixin for hardware features and user preferences options flow steps."""

    async def async_step_hardware_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure hardware feature overrides."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Extract feature overrides from user input
            feature_overrides = {}
            for key in [
                "grid_tie",
                "diesel_mode",
                "three_phase",
                "split_phase",
                "parallel_operation",
                "timed_operation",
                "advanced_output",
                "customized_models",
            ]:
                if key in user_input:
                    feature_overrides[key] = user_input[key]

            # Update config entry data with overrides
            new_data = {
                **self.config_entry.data,
                "feature_overrides": feature_overrides,
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )

            _LOGGER.info("Hardware feature overrides updated: %s", feature_overrides)

            # Reload integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            # Show success message
            return self.async_show_form(
                step_id="hardware_features",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "description": (
                        "✅ Success!\n\n"
                        "Hardware feature overrides saved.\n"
                        "Integration has been reloaded.\n\n"
                        "Entity visibility updated based on your settings.\n\n"
                        "ℹ️ Close this dialog to return to menu"
                    )
                },
            )

        # Get detected features (or defaults)
        detected_features = self.config_entry.data.get("detected_features", {})
        feature_overrides = self.config_entry.data.get("feature_overrides", {})

        # Build schema with detected values and overrides
        schema_dict = {}

        feature_descriptions = {
            "grid_tie": "Grid-tied operation (export to grid)",
            "diesel_mode": "Diesel generator mode",
            "three_phase": "Three-phase power system",
            "split_phase": "Split-phase (120V/240V) system",
            "parallel_operation": "Parallel inverter operation",
            "timed_operation": "Time-based charging/discharging",
            "advanced_output": "Advanced output control",
            "customized_models": "Custom inverter models",
        }

        for feature, description in feature_descriptions.items():
            # Use override if exists, otherwise use detected value, fallback to False
            current_value = feature_overrides.get(
                feature, detected_features.get(feature, False)
            )
            was_detected = detected_features.get(feature, False)
            is_overridden = feature in feature_overrides

            label = feature.replace("_", " ").title()
            if was_detected and not is_overridden:
                label += " (Detected)"
            elif is_overridden:
                label += " (Override)"

            schema_dict[vol.Optional(feature, default=current_value)] = cv.boolean

        schema = vol.Schema(schema_dict)

        detected_count = sum(1 for v in detected_features.values() if v)
        total_features = len(detected_features)

        return self.async_show_form(
            step_id="hardware_features",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "🔧 HARDWARE FEATURE OVERRIDES\n\n"
                    f"Auto-detected: {detected_count}/{total_features} features\n\n"
                    "You can override the automatic hardware detection here.\n"
                    "This is useful if:\n"
                    "• Detection failed or is incorrect\n"
                    "• You want to hide certain features\n"
                    "• You're testing with different configurations\n\n"
                    "✓ Features marked '(Detected)' were auto-detected\n"
                    "⚠️ Features marked '(Override)' are manually set\n\n"
                    "Disabling a feature will hide all related entities.\n"
                    "Enabling a feature will show entities if supported by inverter.\n\n"
                    "💡 TIP: Use 'Re-detect Hardware' to reset to auto-detection\n\n"
                    "ℹ️ Submit to save changes, or close dialog to cancel"
                ),
            },
        )

    async def async_step_user_preferences(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure user preference groups (show/hide optional entities)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Save user preferences to options
            new_options = {**self.config_entry.options, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, options=new_options
            )

            _LOGGER.info("User preferences updated: %s", user_input)

            # Reload integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            # Show success message
            return self.async_show_form(
                step_id="user_preferences",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "description": (
                        "✅ Success!\n\n"
                        "User preferences saved.\n"
                        "Integration has been reloaded.\n\n"
                        "Entity visibility updated based on your preferences.\n\n"
                        "ℹ️ Close this dialog to return to menu"
                    )
                },
            )

        # Get current preferences (default to enabled)
        current_options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    "show_equalization_settings",
                    default=current_options.get("show_equalization_settings", True),
                ): cv.boolean,
                vol.Optional(
                    "show_pv2_settings",
                    default=current_options.get("show_pv2_settings", True),
                ): cv.boolean,
                vol.Optional(
                    "show_pv_settings",
                    default=current_options.get("show_pv_settings", True),
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="user_preferences",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    "👤 USER PREFERENCES\n\n"
                    "Show or hide optional entity groups based on your system configuration.\n\n"
                    "🔋 EQUALIZATION SETTINGS:\n"
                    "Battery equalization charge settings (voltage, time, interval).\n"
                    "Only applicable to lead-acid batteries.\n"
                    "Hide if using lithium batteries or if not needed.\n\n"
                    "☀️ PV2 SETTINGS:\n"
                    "Second PV panel monitoring (voltage, current, power).\n"
                    "Only applicable if you have dual PV inputs.\n"
                    "Hide if using single PV array.\n\n"
                    "☀️ PV SETTINGS:\n"
                    "All solar panel monitoring and configuration.\n"
                    "Hide if not using solar panels (AC-only, generator-only systems).\n\n"
                    "💡 These settings control visibility only - they don't affect inverter operation.\n"
                    "Hiding groups reduces clutter in your entity list.\n\n"
                    "ℹ️ Submit to save changes, or close dialog to cancel"
                ),
            },
        )
