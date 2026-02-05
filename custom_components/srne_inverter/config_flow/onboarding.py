"""Config flow onboarding for SRNE HF Series Inverter integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .helpers.schema_builder import ConfigFlowSchemaBuilder
from .base import CONFIGURATION_PRESETS, get_options_flow_handler
from ..const import DOMAIN
from ..onboarding import (
    OnboardingContext,
    OnboardingState,
    OnboardingStateMachine,
    FeatureDetector,
)

_LOGGER = logging.getLogger(__name__)


class SRNEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SRNE Inverter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}
        self._selected_address: str | None = None
        self._onboarding_context: OnboardingContext | None = None
        self._state_machine = OnboardingStateMachine()
        self._detection_progress: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - scan for BLE devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            # Set unique ID based on BLE address
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            # Store selected address for onboarding flow
            self._selected_address = address

            # Transition to onboarding flow
            self._state_machine.transition(OnboardingState.DEVICE_SELECTED)
            return await self.async_step_welcome()

        # Scan for SRNE devices (E6* prefix)
        discovered = await self._async_scan_devices()

        if not discovered:
            errors["base"] = "no_devices_found"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(discovered),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(discovered)),
            },
        )

    async def _async_scan_devices(self) -> dict[str, str]:
        """Scan for SRNE BLE devices.

        Returns:
            Dictionary mapping addresses to display names
        """
        _LOGGER.info("Scanning for SRNE BLE devices with E6* prefix")

        # Get current Bluetooth devices from Home Assistant's discovery
        try:
            # Get all discovered service info
            devices = bluetooth.async_discovered_service_info(self.hass)
            _LOGGER.info("Total BLE devices discovered by HA: %d", len(devices))

            srne_devices = {}
            for device in devices:
                _LOGGER.debug(
                    "Checking device: name=%s, address=%s", device.name, device.address
                )

                # SRNE devices have names starting with "E60" (at least 3 chars)
                if device.name and device.name.startswith("E60"):
                    display_name = f"{device.name} ({device.address})"
                    srne_devices[device.address] = display_name
                    self._discovered_devices[device.address] = device.name
                    _LOGGER.info(
                        "Found SRNE device: %s at %s", device.name, device.address
                    )
                elif device.name and device.name.startswith("E6"):
                    # Log devices that match E6 but not E60 for debugging
                    _LOGGER.debug(
                        "Found E6* device but not E60*: %s at %s",
                        device.name,
                        device.address,
                    )

            if not srne_devices:
                _LOGGER.debug(
                    "No SRNE devices found. Ensure: "
                    "1) Inverter is powered on, "
                    "2) BLE is enabled on inverter, "
                    "3) Within Bluetooth range (~10m), "
                    "4) Home Assistant Bluetooth is working"
                )

            return srne_devices

        except Exception as err:
            _LOGGER.exception("Error scanning for devices: %s", err)
            return {}

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery."""
        _LOGGER.debug("Discovered SRNE device via bluetooth: %s", discovery_info.name)

        address = discovery_info.address
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": discovery_info.name or "SRNE Inverter"
        }
        self._discovered_devices[address] = discovery_info.name or "SRNE Inverter"

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm bluetooth discovery."""
        if user_input is not None:
            address = self.context["unique_id"]
            device_name = self._discovered_devices.get(address, "SRNE Inverter")

            return self.async_create_entry(
                title=device_name,
                data={CONF_ADDRESS: address},
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self.context["title_placeholders"]["name"],
            },
        )

    async def async_step_welcome(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Welcome screen after device selection."""
        if user_input is not None:
            self._state_machine.transition(OnboardingState.USER_LEVEL)
            return await self.async_step_user_level()

        # Initialize onboarding context
        address = self._selected_address
        device_name = self._discovered_devices.get(address, "SRNE Inverter")

        self._onboarding_context = OnboardingContext(
            device_address=address,
            device_name=device_name,
        )

        _LOGGER.info("Starting onboarding for device: %s (%s)", device_name, address)

        return self.async_show_form(
            step_id="welcome",
            data_schema=vol.Schema({}),
            description_placeholders={
                "device_name": device_name,
            },
        )

    async def async_step_user_level(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """User level selection screen."""
        if user_input is not None:
            self._onboarding_context.user_level = user_input["user_level"]
            self._onboarding_context.mark_step_complete("user_level")

            _LOGGER.info("User selected level: %s", user_input["user_level"])

            self._state_machine.transition(OnboardingState.HARDWARE_DETECTION)
            return await self.async_step_hardware_detection()

        return self.async_show_form(
            step_id="user_level",
            data_schema=vol.Schema(
                {
                    vol.Required("user_level", default="basic"): vol.In(
                        {
                            "basic": "Basic User - Guided Setup",
                            "advanced": "Advanced User - Full Control",
                            "expert": "Expert Mode - Maximum Control",
                        }
                    ),
                }
            ),
        )

    async def async_step_hardware_detection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Hardware detection screen with progress."""
        # If we have detection results, proceed to review
        if self._onboarding_context.detected_features:
            self._state_machine.transition(OnboardingState.DETECTION_REVIEW)
            return await self.async_step_detection_review()

        # Start detection in background
        _LOGGER.info("Starting hardware feature detection")

        # Show progress indication
        self.hass.async_create_task(self._run_detection())

        return self.async_show_progress(
            step_id="hardware_detection",
            progress_action="detect_hardware",
        )

    async def _run_detection(self) -> None:
        """Run feature detection in background.

        Note: For Sprint 2, using model-based inference as a placeholder.
        Sprint 2 refinement or Sprint 3 will implement actual hardware probing
        once we have coordinator access patterns established.
        """
        try:
            import time

            start_time = time.time()

            # Simulate detection progress with small delays
            detector = FeatureDetector(None)  # No coordinator yet

            # Use model-based inference for now (safe fallback)
            device_name = self._onboarding_context.device_name
            results = detector.infer_features_from_model(device_name)

            # Add small delay to simulate hardware testing
            await asyncio.sleep(0.5)

            duration = time.time() - start_time

            # Store results in context
            self._onboarding_context.detected_features = results
            self._onboarding_context.detection_method = "model_inference"
            self._onboarding_context.detection_timestamp = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            self._onboarding_context.detection_duration_seconds = duration
            self._onboarding_context.mark_step_complete("hardware_detection")

            _LOGGER.info(
                "Feature inference complete in %.1f seconds. Inferred %d/%d features from model: %s",
                duration,
                sum(results.values()),
                len(results),
                device_name,
            )

            # Trigger next step
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(
                    flow_id=self.flow_id,
                    user_input={},
                )
            )

        except Exception as err:
            _LOGGER.error("Feature detection failed: %s", err, exc_info=True)
            # Use all-false as safe default
            self._onboarding_context.detected_features = {
                "grid_tie": False,
                "diesel_mode": False,
                "three_phase": False,
                "split_phase": False,
                "parallel_operation": False,
                "timed_operation": False,
                "advanced_output": False,
                "customized_models": False,
            }
            self._onboarding_context.detection_method = "failed"

            # Still proceed to next step
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(
                    flow_id=self.flow_id,
                    user_input={},
                )
            )

    async def async_step_detection_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review detection results."""
        if user_input is not None:
            # Store any overrides (for advanced/expert users)
            if "overrides" in user_input:
                self._onboarding_context.user_overrides = user_input["overrides"]

            self._onboarding_context.mark_step_complete("detection_review")

            _LOGGER.info(
                "Detection review complete. User level: %s, Features: %s",
                self._onboarding_context.user_level,
                self._onboarding_context.active_features,
            )

            # Route based on user level
            if self._onboarding_context.user_level == "basic":
                # Basic users: preset selection
                self._state_machine.transition(OnboardingState.PRESET_SELECTION)
                return await self.async_step_preset_selection()
            else:
                # Advanced/expert users: manual configuration
                self._state_machine.transition(OnboardingState.MANUAL_CONFIG)
                return await self.async_step_manual_config()

        # Build display based on user level
        if self._onboarding_context.user_level == "basic":
            # Simple display for basic users
            return self.async_show_form(
                step_id="detection_review",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "detected_features": self._format_features_basic(),
                },
            )
        else:
            # Advanced/expert: show with override capability
            return self.async_show_form(
                step_id="detection_review",
                data_schema=self._build_override_schema(),
                description_placeholders={
                    "detected_features": self._format_features_advanced(),
                },
            )

    def _format_features_basic(self) -> str:
        """Format features for basic users."""
        if not self._onboarding_context.detected_features:
            return "⚠️ Detection did not complete. Using safe defaults."

        lines = ["Your inverter has the following capabilities:\n"]
        for feature, detected in self._onboarding_context.detected_features.items():
            status = "✓" if detected else "✗"
            name = feature.replace("_", " ").title()
            lines.append(f"{status} {name}")
        return "\n".join(lines)

    def _format_features_advanced(self) -> str:
        """Format features with technical details for advanced users."""
        if not self._onboarding_context.detected_features:
            return "⚠️ Detection did not complete. You can configure features manually."

        from ..onboarding.detection import FEATURE_TEST_REGISTERS

        lines = ["Auto-detected features (you can override below):\n"]
        for feature, detected in self._onboarding_context.detected_features.items():
            status = "✓" if detected else "✗"
            name = feature.replace("_", " ").title()
            register = FEATURE_TEST_REGISTERS.get(feature, 0)
            lines.append(f"{status} {name} (register 0x{register:04X})")
        return "\n".join(lines)

    def _build_override_schema(self) -> vol.Schema:
        """Build schema with override checkboxes for each feature."""
        if not self._onboarding_context.detected_features:
            return vol.Schema({})

        schema_dict = {}
        for feature, detected in self._onboarding_context.detected_features.items():
            feature.replace("_", " ").title()
            schema_dict[vol.Optional(f"override_{feature}", default=detected)] = (
                cv.boolean
            )
        return vol.Schema(schema_dict)

    async def async_step_preset_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Preset selection for basic users."""
        if user_input is not None:
            preset_key = user_input["preset"]

            # Store selected preset
            self._onboarding_context.selected_preset = preset_key
            self._onboarding_context.mark_step_complete("preset_selection")

            # Apply preset settings
            preset_settings = CONFIGURATION_PRESETS[preset_key]["settings"]
            self._onboarding_context.custom_settings = preset_settings.copy()

            _LOGGER.info("User selected preset: %s", preset_key)

            # Proceed to validation
            self._state_machine.transition(OnboardingState.VALIDATION)
            return await self.async_step_validation()

        # Filter presets based on detected features
        available_presets = self._filter_presets_by_features()

        # Build preset selection form
        preset_options = [
            selector.SelectOptionDict(
                value=key, label=f"{preset['name']} - {preset['description']}"
            )
            for key, preset in available_presets.items()
        ]

        return self.async_show_form(
            step_id="preset_selection",
            data_schema=vol.Schema(
                {
                    vol.Required("preset"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=preset_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            description_placeholders={
                "preset_count": str(len(available_presets)),
            },
        )

    def _filter_presets_by_features(self) -> dict[str, dict]:
        """Filter presets based on detected features."""
        available = {}
        active_features = self._onboarding_context.active_features

        for key, preset in CONFIGURATION_PRESETS.items():
            # Check if preset requirements are met
            required_features = preset.get("required_features", [])

            if all(active_features.get(f, False) for f in required_features):
                available[key] = preset

        # Always include at least one preset (off-grid solar has no requirements)
        if not available:
            available["off_grid_solar"] = CONFIGURATION_PRESETS["off_grid_solar"]

        return available

    async def async_step_manual_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual configuration for advanced/expert users."""
        if user_input is not None:
            # Store settings
            self._onboarding_context.custom_settings.update(user_input)
            self._onboarding_context.mark_step_complete("manual_config")

            _LOGGER.info(
                "User completed manual config. Settings: %s",
                self._onboarding_context.custom_settings,
            )

            # Proceed to validation
            self._state_machine.transition(OnboardingState.VALIDATION)
            return await self.async_step_validation()

        # Build dynamic form based on user level
        schema = self._build_manual_config_schema()

        return self.async_show_form(
            step_id="manual_config",
            data_schema=schema,
            description_placeholders={
                "user_level": self._onboarding_context.user_level,
            },
        )

    def _build_manual_config_schema(self) -> vol.Schema:
        """Build configuration schema based on user level and features."""
        schema_dict = {}
        user_level = self._onboarding_context.user_level

        # Battery settings (always shown)
        schema_dict[vol.Required("battery_capacity", default=100)] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=400)
        )
        schema_dict[vol.Required("battery_voltage", default="48")] = vol.In(
            ["12", "24", "36", "48"]
        )

        # Output priority
        schema_dict[vol.Required("output_priority", default="2")] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "0", "label": "Solar First"},
                        {"value": "1", "label": "Mains First"},
                        {"value": "2", "label": "SBU (Solar-Battery-Utility)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        )

        # Charge source priority
        schema_dict[vol.Required("charge_source_priority", default="0")] = (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "0", "label": "PV Priority (AC Backup)"},
                        {"value": "1", "label": "AC Priority"},
                        {"value": "2", "label": "Hybrid Mode"},
                        {"value": "3", "label": "PV Only"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        )

        # SOC thresholds (advanced/expert)
        if user_level in ["advanced", "expert"]:
            schema_dict[vol.Optional("discharge_stop_soc", default=20)] = vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            )
            schema_dict[vol.Optional("switch_to_ac_soc", default=10)] = vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            )
            schema_dict[vol.Optional("switch_to_battery_soc", default=80)] = vol.All(
                vol.Coerce(int), vol.Range(min=1, max=100)
            )

        # Expert-only settings
        if user_level == "expert":
            schema_dict[vol.Optional("enable_diagnostic_sensors", default=True)] = (
                cv.boolean
            )
            schema_dict[vol.Optional("log_modbus_traffic", default=False)] = cv.boolean

        return vol.Schema(schema_dict)

    async def async_step_validation(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate configuration settings."""
        # Run validation
        validation_results = self._validate_settings()

        if validation_results["has_errors"]:
            # Format error messages for display
            error_messages = "\n\n".join(
                f"• {error}" for error in validation_results["errors"]
            )

            _LOGGER.warning(
                "Validation failed with %d errors: %s",
                len(validation_results["errors"]),
                validation_results["errors"],
            )

            # Store validation errors for display
            errors_dict = {"base": "validation_failed"}

            # Return to previous step with errors displayed
            if self._onboarding_context.user_level == "basic":
                # Basic users: return to preset selection
                available_presets = self._filter_presets_by_features()
                preset_options = [
                    selector.SelectOptionDict(
                        value=key, label=f"{preset['name']} - {preset['description']}"
                    )
                    for key, preset in available_presets.items()
                ]

                return self.async_show_form(
                    step_id="preset_selection",
                    data_schema=vol.Schema(
                        {
                            vol.Required("preset"): selector.SelectSelector(
                                selector.SelectSelectorConfig(
                                    options=preset_options,
                                    mode=selector.SelectSelectorMode.DROPDOWN,
                                )
                            ),
                        }
                    ),
                    errors=errors_dict,
                    description_placeholders={
                        "preset_count": str(len(available_presets)),
                        "error_details": error_messages,
                    },
                )
            else:
                # Advanced/expert users: return to manual config
                schema = self._build_manual_config_schema()

                return self.async_show_form(
                    step_id="manual_config",
                    data_schema=schema,
                    errors=errors_dict,
                    description_placeholders={
                        "user_level": self._onboarding_context.user_level,
                        "error_details": error_messages,
                    },
                )

        # Validation passed - proceed to review
        self._onboarding_context.validation_passed = True
        self._onboarding_context.validation_warnings = validation_results.get(
            "warnings", []
        )
        self._onboarding_context.mark_step_complete("validation")

        _LOGGER.info(
            "Validation passed with %d warnings: %s",
            len(validation_results["warnings"]),
            validation_results["warnings"],
        )

        self._state_machine.transition(OnboardingState.REVIEW)
        return await self.async_step_review()

    def _validate_settings(self) -> dict[str, Any]:
        """Validate configuration settings with enhanced error messages.

        Returns:
            Dict with keys: has_errors, errors, warnings
        """
        errors = []
        warnings = []
        settings = self._onboarding_context.custom_settings

        # Validate SOC order if present
        discharge_stop = settings.get("discharge_stop_soc", 0)
        switch_ac = settings.get("switch_to_ac_soc", 0)
        switch_battery = settings.get("switch_to_battery_soc", 100)

        if discharge_stop and switch_ac and discharge_stop >= switch_ac:
            errors.append(
                f"Discharge stop SOC ({discharge_stop}%) must be less than "
                f"switch to AC SOC ({switch_ac}%). "
                "Recommended: discharge stop at 20%, switch to AC at 30%."
            )

        if switch_ac and switch_battery and switch_ac >= switch_battery:
            errors.append(
                f"Switch to AC SOC ({switch_ac}%) must be less than "
                f"switch to battery SOC ({switch_battery}%). "
                "Recommended: switch to AC at 30%, switch to battery at 80%."
            )

        # Validate battery voltage
        battery_voltage = settings.get("battery_voltage")
        if battery_voltage and battery_voltage not in ["12", "24", "36", "48"]:
            errors.append(
                f"Battery voltage '{battery_voltage}' is invalid. "
                "Must be one of: 12V, 24V, 36V, or 48V."
            )

        # Battery capacity vs charge current validation
        battery_capacity = settings.get("battery_capacity")
        max_charge = settings.get("max_charge_current")

        if battery_capacity and max_charge:
            # Recommend max charge current <= 0.5C (C/2)
            safe_max = battery_capacity * 0.5
            if max_charge > safe_max:
                warnings.append(
                    f"Charge current ({max_charge}A) exceeds recommended 0.5C rate "
                    f"for {battery_capacity}Ah battery. "
                    f"Maximum recommended: {safe_max:.1f}A. "
                    "Higher rates may reduce battery lifespan."
                )

        # Output priority validation with detected features
        output_priority = settings.get("output_priority")
        has_grid = self._onboarding_context.active_features.get("grid_tie", False)

        if output_priority in ["0", "1"] and not has_grid:
            warnings.append(
                "Output priority set to use grid power, but grid-tie feature not detected. "
                "System may not function as expected. "
                "Consider using 'SBU' (Solar-Battery-Utility) priority instead."
            )

        # Charge source validation
        charge_source = settings.get("charge_source_priority")
        if charge_source in ["0", "1", "2"] and not has_grid:
            warnings.append(
                "Charge source priority includes AC charging, but grid connection not detected. "
                "System will only charge from solar. "
                "Consider using 'PV Only' if you have no grid connection."
            )

        # Battery voltage consistency check
        if battery_voltage:
            device_name = self._onboarding_context.device_name
            # Check common voltage indicators in device name
            if "48V" in device_name.upper() and battery_voltage != "48":
                warnings.append(
                    f"Device name suggests 48V system, but {battery_voltage}V configured. "
                    "Please verify this is correct for your setup."
                )
            elif "24V" in device_name.upper() and battery_voltage != "24":
                warnings.append(
                    f"Device name suggests 24V system, but {battery_voltage}V configured. "
                    "Please verify this is correct for your setup."
                )

        # Low discharge SOC warning
        if discharge_stop and discharge_stop < 10:
            warnings.append(
                f"Discharge stop SOC set to {discharge_stop}%, which is below 10%. "
                "This may significantly reduce battery lifespan. "
                "Consider setting to at least 20% for better battery health."
            )

        # High switch to battery SOC warning
        if switch_battery and switch_battery > 90:
            warnings.append(
                f"Switch to battery SOC set to {switch_battery}%, which is above 90%. "
                "This may cause frequent switching between AC and battery. "
                "Consider setting to 80% for more stable operation."
            )

        return {
            "has_errors": len(errors) > 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Review and confirm configuration before writing."""
        if user_input is not None:
            # User confirmed - create entry
            self._onboarding_context.mark_completed()

            _LOGGER.info(
                "Onboarding complete. User level: %s, Duration: %.1f seconds",
                self._onboarding_context.user_level,
                self._onboarding_context.total_duration or 0,
            )

            # Log configuration summary for troubleshooting
            _LOGGER.debug(
                "Final configuration: detected_features=%s, settings=%s",
                self._onboarding_context.detected_features,
                self._onboarding_context.custom_settings,
            )

            # Create entry with complete metadata
            return self.async_create_entry(
                title=self._onboarding_context.device_name,
                data={
                    CONF_ADDRESS: self._onboarding_context.device_address,
                    "user_level": self._onboarding_context.user_level,
                    "detected_features": self._onboarding_context.detected_features,
                    "detection_method": self._onboarding_context.detection_method,
                    "detection_timestamp": self._onboarding_context.detection_timestamp,
                    "onboarding_completed": True,
                    "onboarding_duration": self._onboarding_context.total_duration,
                },
                options=self._onboarding_context.custom_settings,
            )

        # Build review display
        review_text = self._format_settings_review()
        warnings_text = (
            "\n".join(
                f"⚠️ {warning}"
                for warning in self._onboarding_context.validation_warnings
            )
            if self._onboarding_context.validation_warnings
            else "✓ No warnings"
        )

        return self.async_show_form(
            step_id="review",
            data_schema=vol.Schema({}),
            description_placeholders={
                "review_text": review_text,
                "warnings": warnings_text,
            },
        )

    def _format_settings_review(self) -> str:
        """Format settings for review display."""
        lines = ["Configuration Summary:\n"]

        settings = self._onboarding_context.custom_settings

        if self._onboarding_context.selected_preset:
            preset = CONFIGURATION_PRESETS.get(
                self._onboarding_context.selected_preset, {}
            )
            lines.append(f"Preset: {preset.get('name', 'Unknown')}\n")

        for key, value in settings.items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")

        return "\n".join(lines)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow handler."""
        return get_options_flow_handler()
