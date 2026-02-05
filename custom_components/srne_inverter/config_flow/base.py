"""Base classes and shared utilities for config flow."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)


# Configuration presets for common use cases
CONFIGURATION_PRESETS = {
    "off_grid_solar": {
        "name": "Off-Grid Solar",
        "description": "Optimized for standalone solar + battery systems",
        "icon": "mdi:solar-power",
        "required_features": [],  # No special features required
        "settings": {
            "output_priority": "2",  # SBU
            "charge_source_priority": "3",  # PV Only
            "discharge_stop_soc": 20,
            "switch_to_ac_soc": 10,
            "switch_to_battery_soc": 100,
        },
    },
    "rv_solar_generator": {
        "name": "RV/Trailer Solar + Generator",
        "description": "Solar priority with generator backup for RVs and trailers",
        "icon": "mdi:rv-truck",
        "required_features": [],  # No special features required
        "settings": {
            "output_priority": "2",  # SBU (Solar-Battery-Utility/Generator)
            "charge_source_priority": "0",  # PV Priority with AC backup allowed
            "discharge_stop_soc": 20,  # Stop discharging at 20%
            "switch_to_ac_soc": 30,  # Switch to generator at 30% (more buffer than pure off-grid)
            "switch_to_battery_soc": 80,  # Switch back to battery at 80%
        },
    },
    "grid_tied": {
        "name": "Grid-Tied Solar",
        "description": "Grid backup with solar priority",
        "icon": "mdi:transmission-tower",
        "required_features": ["grid_tie"],  # Requires grid-tie capability
        "settings": {
            "output_priority": "0",  # Solar First
            "charge_source_priority": "0",  # PV Priority (AC backup)
            "discharge_stop_soc": 10,
            "switch_to_ac_soc": 20,
            "switch_to_battery_soc": 80,
        },
    },
    "ups_mode": {
        "name": "UPS Mode",
        "description": "Grid power with battery backup",
        "icon": "mdi:battery-charging",
        "required_features": [],
        "settings": {
            "output_priority": "1",  # Mains First
            "charge_source_priority": "1",  # AC Priority
            "discharge_stop_soc": 20,
        },
    },
    "time_of_use": {
        "name": "Time-of-Use Optimization",
        "description": "Charge during cheap hours, discharge during peak",
        "icon": "mdi:clock-outline",
        "required_features": ["timed_operation"],  # Requires timed operation
        "settings": {
            "charge_source_priority": "2",  # Hybrid
        },
    },
}


class ConfigFlowValidationMixin:
    """Mixin providing common validation methods for config flows."""

    @staticmethod
    def validate_battery_settings(settings: dict[str, Any]) -> bool:
        """Validate battery settings.

        Args:
            settings: Dictionary of battery settings

        Returns:
            True if valid

        Raises:
            ValueError: If settings are invalid
        """
        # Validate battery voltage
        battery_voltage = settings.get("battery_voltage")
        if battery_voltage and battery_voltage not in [12, 24, 48]:
            raise ValueError(
                f"Battery voltage must be 12V, 24V, or 48V. Got: {battery_voltage}V"
            )

        # Validate SoC percentages
        discharge_stop_soc = settings.get("discharge_stop_soc")
        if discharge_stop_soc is not None:
            if not 0 <= discharge_stop_soc <= 100:
                raise ValueError(
                    f"Discharge stop SoC must be 0-100%. Got: {discharge_stop_soc}%"
                )

        switch_to_ac_soc = settings.get("switch_to_ac_soc")
        if switch_to_ac_soc is not None:
            if not 0 <= switch_to_ac_soc <= 100:
                raise ValueError(
                    f"Switch to AC SoC must be 0-100%. Got: {switch_to_ac_soc}%"
                )

        switch_to_battery_soc = settings.get("switch_to_battery_soc")
        if switch_to_battery_soc is not None:
            if not 0 <= switch_to_battery_soc <= 100:
                raise ValueError(
                    f"Switch to battery SoC must be 0-100%. Got: {switch_to_battery_soc}%"
                )

        # Validate capacity
        battery_capacity_ah = settings.get("battery_capacity_ah")
        if battery_capacity_ah is not None:
            if battery_capacity_ah <= 0:
                raise ValueError(
                    f"Battery capacity must be positive. Got: {battery_capacity_ah}Ah"
                )

        return True

    @staticmethod
    def validate_inverter_output_settings(settings: dict[str, Any]) -> bool:
        """Validate inverter output settings.

        Args:
            settings: Dictionary of inverter output settings

        Returns:
            True if valid

        Raises:
            ValueError: If settings are invalid
        """
        # Validate output voltage
        output_voltage = settings.get("output_voltage")
        if output_voltage and output_voltage not in [100, 110, 120, 127, 220, 230, 240]:
            raise ValueError(
                f"Output voltage must be one of: 100, 110, 120, 127, 220, 230, 240V. "
                f"Got: {output_voltage}V"
            )

        # Validate frequency
        output_frequency = settings.get("output_frequency")
        if output_frequency and output_frequency not in [50, 60]:
            raise ValueError(
                f"Output frequency must be 50Hz or 60Hz. Got: {output_frequency}Hz"
            )

        return True

    @staticmethod
    def validate_essential_settings(settings: dict[str, Any]) -> bool:
        """Validate essential settings that must always be present.

        Args:
            settings: Dictionary of essential settings

        Returns:
            True if valid

        Raises:
            ValueError: If settings are invalid
        """
        required_fields = ["battery_voltage", "battery_capacity_ah"]

        for field in required_fields:
            if field not in settings or settings[field] is None:
                raise ValueError(f"Required field missing: {field}")

        return True


def get_options_flow_handler() -> config_entries.OptionsFlow:
    """Factory function to create options flow handler.

    This is used by SRNEConfigFlow.async_get_options_flow().
    Separated to avoid circular imports.

    Returns:
        Instance of SRNEOptionsFlowHandler
    """
    from .options import SRNEOptionsFlowHandler

    return SRNEOptionsFlowHandler()
