"""Preset manager for SRNE Inverter configuration presets."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ..const import COMMAND_DELAY_WRITE, DOMAIN
from .configuration_preset import ConfigurationPreset

if TYPE_CHECKING:
    from ..coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# BUILT-IN PRESETS
# ============================================================================

OFF_GRID_SOLAR = ConfigurationPreset(
    id="off_grid_solar",
    name="Off-Grid Solar",
    description="Optimized for standalone solar + battery systems with no grid connection",
    icon="mdi:solar-power",
    settings={
        "output_priority": 2,  # SBU (Solar → Battery → Utility)
        "charge_source_priority": 3,  # PV Only - no AC charging
        "discharge_stop_soc": 20,  # Allow deeper discharge (no grid backup)
        "switch_to_ac_soc": 10,  # Rarely use grid (emergency only)
        "switch_to_battery_soc": 100,  # Return to battery immediately
        "pv_power_priority": 0,  # Charge battery first (ensure overnight power)
        "max_ac_charge_current": 0,  # Disable AC charging
    },
    use_cases=[
        "Remote areas with no grid connection",
        "Off-grid cabins, RVs, and tiny homes",
        "Maximum solar self-consumption",
        "Remote monitoring stations or equipment",
    ],
    warnings=[
        "Ensure battery capacity is adequate for nighttime use",
        "Solar panels must be sized to fully charge batteries during daylight",
        "Grid will only be used as emergency backup (below 10% SOC)",
        "Consider battery temperature protection for extreme climates",
    ],
)

GRID_TIED_SOLAR = ConfigurationPreset(
    id="grid_tied_solar",
    name="Grid-Tied Solar",
    description="Grid backup with solar priority for maximum solar usage",
    icon="mdi:transmission-tower",
    settings={
        "output_priority": 0,  # Solar First - prioritize solar power
        "charge_source_priority": 0,  # PV Priority (AC backup available)
        "discharge_stop_soc": 10,  # Shallow discharge (grid available)
        "switch_to_ac_soc": 20,  # Switch to grid at moderate SOC
        "switch_to_battery_soc": 80,  # Return to battery when well-charged
        "pv_power_priority": 1,  # Load priority (use solar immediately)
    },
    use_cases=[
        "Grid-connected homes with reliable utility service",
        "Maximum solar usage to reduce electricity bills",
        "Net metering or feed-in tariff systems",
        "Areas with stable grid but high electricity costs",
    ],
    warnings=[
        "Requires stable grid connection for proper operation",
        "Check local regulations for grid-tie requirements",
        "Verify net metering availability with your utility",
        "Battery serves primarily for backup, not daily cycling",
    ],
)

UPS_MODE = ConfigurationPreset(
    id="ups_mode",
    name="UPS Mode",
    description="Grid power with battery backup for critical equipment protection",
    icon="mdi:battery-charging",
    settings={
        "output_priority": 1,  # Mains First - grid primary power source
        "charge_source_priority": 1,  # AC Priority - fast grid charging
        "discharge_stop_soc": 20,  # Protect battery from deep discharge
        "ac_input_range": 1,  # Narrow tolerance (UPS mode, 170-280V)
        "switch_to_ac_soc": 30,  # Return to grid quickly
        "switch_to_battery_soc": 90,  # Keep battery charged
    },
    use_cases=[
        "Critical equipment protection (servers, medical devices)",
        "Areas with frequent but short grid outages",
        "Battery as emergency backup only",
        "Home office or small business continuity",
    ],
    warnings=[
        "Battery will only discharge during grid outages",
        "Ensure battery stays charged for emergencies",
        "Narrow AC input range may switch to battery more frequently",
        "Not suitable for reducing electricity bills (grid always primary)",
    ],
)

TIME_OF_USE = ConfigurationPreset(
    id="time_of_use",
    name="Time-of-Use Optimization",
    description="Charge during cheap hours, discharge during peak rates to save money",
    icon="mdi:clock-time-four",
    settings={
        "output_priority": 2,  # SBU - prioritize battery during peak hours
        "charge_source_priority": 2,  # Hybrid - use both PV and AC
        "timed_charge_enable": True,  # Enable timed charging
        "charge_start_time_1": 256,  # 01:00 (1*256 + 0) - cheap night rate
        "charge_end_time_1": 1536,  # 06:00 (6*256 + 0) - before peak
        "timed_discharge_enable": True,  # Enable timed discharging
        "discharge_start_time_1": 4352,  # 17:00 (17*256 + 0) - peak rate start
        "discharge_end_time_1": 5376,  # 21:00 (21*256 + 0) - peak rate end
        "discharge_stop_soc": 15,  # Preserve some battery for emergencies
        "switch_to_ac_soc": 10,  # Allow deep discharge during peak hours
        "switch_to_battery_soc": 90,  # Return to battery when charged
    },
    use_cases=[
        "Electricity providers with time-of-use (TOU) rates",
        "Save $50-100+ per month on electricity bills",
        "Peak shaving and demand management",
        "Commercial applications with demand charges",
    ],
    warnings=[
        "Requires understanding of your utility rate schedule",
        "Time settings must match your peak/off-peak hours",
        "System time must be synchronized with inverter",
        "Review and adjust times when daylight saving changes",
        "Battery cycling will be increased - ensure battery warranty allows",
    ],
)

BATTERY_ONLY = ConfigurationPreset(
    id="battery_only",
    name="Battery-Only (No PV)",
    description="Battery-first operation with AC charging only - no solar panels",
    icon="mdi:battery-heart",
    settings={
        "output_priority": 2,  # SBU (Battery → Utility) - battery is primary power
        "charge_source_priority": 1,  # AC Priority - charge from grid when available
        "discharge_stop_soc": 25,  # Protect battery from deep discharge
        "switch_to_ac_soc": 30,  # Switch to AC when battery gets low
        "switch_to_battery_soc": 85,  # Return to battery when charged enough
        "pv_power_priority": 0,  # Charge battery first (though no PV exists)
    },
    use_cases=[
        "Systems without solar panels (battery + grid only)",
        "Intermittent grid power - use battery when grid is unavailable",
        "Reduce peak demand by running on battery during high-usage periods",
        "Emergency backup power with automatic charging when grid returns",
    ],
    warnings=[
        "No solar charging - battery will only charge from AC grid",
        "Grid must be available periodically to recharge batteries",
        "Battery will discharge to loads continuously when grid is unavailable",
        "Size battery capacity for expected grid outage duration",
        "Monitor battery SOC regularly to prevent over-discharge",
        "Consider adding solar panels for more sustainable operation",
    ],
)


# ============================================================================
# PRESET MANAGER
# ============================================================================


class PresetManager:
    """Manage configuration presets for SRNE Inverter.

    Provides built-in presets for common use cases and allows users to create
    custom presets by saving their current configuration.
    """

    def __init__(
        self, hass: HomeAssistant, coordinator: SRNEDataUpdateCoordinator
    ) -> None:
        """Initialize preset manager.

        Args:
            hass: Home Assistant instance
            coordinator: SRNE data update coordinator
        """
        self._hass = hass
        self._coordinator = coordinator
        self._presets: dict[str, ConfigurationPreset] = {}
        self._custom_presets_file = Path(
            hass.config.path(f"{DOMAIN}_custom_presets.json")
        )

        # Load built-in presets
        self._load_builtin_presets()

        # Load custom presets from file
        self._load_custom_presets()

    def _load_builtin_presets(self) -> None:
        """Load built-in configuration presets."""
        for preset in [OFF_GRID_SOLAR, GRID_TIED_SOLAR, UPS_MODE, TIME_OF_USE, BATTERY_ONLY]:
            self._presets[preset.id] = preset
            _LOGGER.debug("Loaded built-in preset: %s", preset.name)

    def _load_custom_presets(self) -> None:
        """Load custom presets from JSON file."""
        if not self._custom_presets_file.exists():
            _LOGGER.debug("No custom presets file found")
            return

        try:
            with open(self._custom_presets_file, encoding="utf-8") as file:
                data = json.load(file)

            for preset_data in data.get("presets", []):
                preset = ConfigurationPreset.from_dict(preset_data)
                preset.is_custom = True
                self._presets[preset.id] = preset
                _LOGGER.info("Loaded custom preset: %s", preset.name)

        except (json.JSONDecodeError, OSError, KeyError) as err:
            _LOGGER.error("Failed to load custom presets: %s", err)

    def _save_custom_presets(self) -> None:
        """Save custom presets to JSON file."""
        custom_presets = [
            preset.to_dict() for preset in self._presets.values() if preset.is_custom
        ]

        try:
            self._custom_presets_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self._custom_presets_file, "w", encoding="utf-8") as file:
                json.dump({"presets": custom_presets}, file, indent=2)

            _LOGGER.info("Saved %d custom presets", len(custom_presets))

        except OSError as err:
            _LOGGER.error("Failed to save custom presets: %s", err)
            raise HomeAssistantError(f"Failed to save custom presets: {err}") from err

    def get_preset(self, preset_id: str) -> ConfigurationPreset | None:
        """Get preset by ID.

        Args:
            preset_id: Preset identifier

        Returns:
            ConfigurationPreset if found, None otherwise
        """
        return self._presets.get(preset_id)

    def list_presets(self, include_custom: bool = True) -> list[ConfigurationPreset]:
        """Get all available presets.

        Args:
            include_custom: Whether to include custom presets

        Returns:
            List of configuration presets
        """
        presets = list(self._presets.values())

        if not include_custom:
            presets = [p for p in presets if not p.is_custom]

        # Sort: built-in first, then custom, alphabetically within each group
        presets.sort(key=lambda p: (p.is_custom, p.name))

        return presets

    async def apply_preset(
        self,
        preset_id: str,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Apply configuration preset to inverter.

        Args:
            preset_id: Preset identifier to apply
            overrides: Optional dictionary of setting overrides

        Returns:
            Dictionary with application results:
            - success: Whether all settings applied successfully
            - applied: List of successfully applied settings
            - failed: List of settings that failed to apply
            - skipped: List of settings skipped due to overrides

        Raises:
            ValueError: If preset not found
            HomeAssistantError: If critical error occurs during application
        """
        preset = self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")

        _LOGGER.info("Applying preset: %s", preset.name)

        # Merge preset settings with overrides
        settings = preset.settings.copy()
        if overrides:
            settings.update(overrides)
            _LOGGER.debug("Applied overrides: %s", overrides)

        # Validate settings before applying
        validation_errors = await self._validate_settings(settings)
        if validation_errors:
            raise HomeAssistantError(
                f"Preset validation failed: {', '.join(validation_errors)}"
            )

        # Apply settings to inverter
        applied = []
        failed = []

        for setting_name, value in settings.items():
            try:
                # Map setting name to register address
                register = self._get_register_for_setting(setting_name)
                if register is None:
                    _LOGGER.debug("Unknown setting: %s", setting_name)
                    failed.append((setting_name, "Unknown register"))
                    continue

                # Encode value for register (handle scaling, etc.)
                encoded_value = self._encode_setting_value(setting_name, value)

                # Write to inverter
                success = await self._coordinator.async_write_register(
                    register, encoded_value
                )

                if success:
                    applied.append(setting_name)
                    _LOGGER.debug(
                        "Applied setting %s = %s (register 0x%04X = 0x%04X)",
                        setting_name,
                        value,
                        register,
                        encoded_value,
                    )
                    # Enforce command delay
                    await asyncio.sleep(COMMAND_DELAY_WRITE)
                else:
                    failed.append((setting_name, "Write failed"))
                    _LOGGER.error("Failed to write setting: %s", setting_name)

            except Exception as err:  # pylint: disable=broad-except
                failed.append((setting_name, str(err)))
                _LOGGER.exception("Error applying setting %s: %s", setting_name, err)

        # Return results
        result = {
            "success": len(failed) == 0,
            "preset_name": preset.name,
            "applied": applied,
            "failed": failed,
            "total_settings": len(settings),
        }

        if result["success"]:
            _LOGGER.info("Successfully applied preset: %s", preset.name)
        else:
            _LOGGER.debug(
                "Preset %s partially applied: %d/%d settings failed",
                preset.name,
                len(failed),
                len(settings),
            )

        return result

    async def save_custom_preset(
        self,
        name: str,
        description: str,
        settings: dict[str, Any] | None = None,
        icon: str = "mdi:cog",
    ) -> str:
        """Save current configuration as custom preset.

        Args:
            name: Name for the custom preset
            description: Description of the preset
            settings: Optional settings dict (uses current config if None)
            icon: Material Design Icon identifier

        Returns:
            Preset ID of created preset

        Raises:
            ValueError: If preset name already exists
            HomeAssistantError: If reading current config fails
        """
        # Generate preset ID from name
        preset_id = f"custom_{name.lower().replace(' ', '_')}"

        # Check for duplicate name
        if preset_id in self._presets:
            raise ValueError(f"Preset already exists: {name}")

        # Use provided settings or read from inverter
        if settings is None:
            settings = await self._read_current_settings()

        # Validate settings
        validation_errors = await self._validate_settings(settings)
        if validation_errors:
            raise HomeAssistantError(
                f"Settings validation failed: {', '.join(validation_errors)}"
            )

        # Create custom preset
        preset = ConfigurationPreset(
            id=preset_id,
            name=name,
            description=description,
            icon=icon,
            settings=settings,
            use_cases=[],
            warnings=["Custom preset - verify settings before applying"],
            is_custom=True,
        )

        # Add to presets
        self._presets[preset_id] = preset

        # Save to file
        self._save_custom_presets()

        _LOGGER.info("Created custom preset: %s (ID: %s)", name, preset_id)

        return preset_id

    async def delete_custom_preset(self, preset_id: str) -> None:
        """Delete custom preset.

        Args:
            preset_id: Preset ID to delete

        Raises:
            ValueError: If preset not found or not custom
        """
        preset = self.get_preset(preset_id)
        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")

        if not preset.is_custom:
            raise ValueError("Cannot delete built-in preset")

        del self._presets[preset_id]
        self._save_custom_presets()

        _LOGGER.info("Deleted custom preset: %s", preset.name)

    async def _validate_settings(self, settings: dict[str, Any]) -> list[str]:
        """Validate preset settings.

        Args:
            settings: Settings dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for conflicting settings
        if "output_priority" in settings and "charge_source_priority" in settings:
            output_priority = settings["output_priority"]
            charge_priority = settings["charge_source_priority"]

            # Warn about potentially conflicting configurations
            if output_priority == 1 and charge_priority == 3:  # Mains First + PV Only
                errors.append(
                    "Conflicting priorities: Mains First output with PV Only charging"
                )

        # Validate SOC thresholds
        if "discharge_stop_soc" in settings and "switch_to_ac_soc" in settings:
            if settings["discharge_stop_soc"] >= settings["switch_to_ac_soc"]:
                errors.append("discharge_stop_soc must be less than switch_to_ac_soc")

        if "switch_to_ac_soc" in settings and "switch_to_battery_soc" in settings:
            if settings["switch_to_ac_soc"] >= settings["switch_to_battery_soc"]:
                errors.append(
                    "switch_to_ac_soc must be less than switch_to_battery_soc"
                )

        # Validate timed operations
        if (
            settings.get("timed_charge_enable")
            and "charge_start_time_1" not in settings
        ):
            errors.append("timed_charge_enable requires charge_start_time_1")

        if (
            settings.get("timed_discharge_enable")
            and "discharge_start_time_1" not in settings
        ):
            errors.append("timed_discharge_enable requires discharge_start_time_1")

        return errors

    async def _read_current_settings(self) -> dict[str, Any]:
        """Read current inverter settings.

        Returns:
            Dictionary of current settings

        Raises:
            HomeAssistantError: If reading fails
        """
        # This would read all relevant registers from coordinator.data
        # For now, return a placeholder - actual implementation would
        # extract values from self._coordinator.data

        _LOGGER.debug("Reading current settings not yet fully implemented")

        return {}

    def _get_register_for_setting(self, setting_name: str) -> int | None:
        """Map setting name to register address.

        Args:
            setting_name: Setting name (e.g., "output_priority")

        Returns:
            Register address or None if not found
        """
        # Register mapping for common settings
        REGISTER_MAP = {
            "output_priority": 0xE204,
            "charge_source_priority": 0xE20F,
            "discharge_stop_soc": 0xE00F,
            "switch_to_ac_soc": 0xE01F,
            "switch_to_battery_soc": 0xE020,
            "pv_power_priority": 0xE039,
            "max_ac_charge_current": 0xE205,
            "timed_charge_enable": 0xE02C,
            "charge_start_time_1": 0xE026,
            "charge_end_time_1": 0xE027,
            "timed_discharge_enable": 0xE033,
            "discharge_start_time_1": 0xE02D,
            "discharge_end_time_1": 0xE02E,
            "ac_input_range": 0xE20B,
        }

        return REGISTER_MAP.get(setting_name)

    def _encode_setting_value(self, setting_name: str, value: Any) -> int:
        """Encode setting value for register write.

        Args:
            setting_name: Setting name
            value: Raw value

        Returns:
            Encoded register value (16-bit integer)
        """
        # Handle boolean values
        if isinstance(value, bool):
            return 1 if value else 0

        # Handle numeric values with scaling
        if setting_name == "max_ac_charge_current":
            # Scale: 0.1 (value in A, register in 0.1A units)
            return int(value * 10)

        # Most settings are direct integer values
        return int(value)
