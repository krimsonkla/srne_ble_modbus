"""Config flow for SRNE HF Series Inverter integration."""

from __future__ import annotations

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

from .config import ConfigFlowSchemaBuilder
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Enable YAML-driven schema generation from entities_pilot.yaml
USE_DYNAMIC_SCHEMAS = True


class SRNEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SRNE Inverter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}

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

            # Validate connection
            try:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, address, connectable=True
                )

                if device is None:
                    errors["base"] = "device_not_found"
                else:
                    # Create entry with device name
                    device_name = self._discovered_devices.get(address, "SRNE Inverter")
                    return self.async_create_entry(
                        title=device_name,
                        data={CONF_ADDRESS: address},
                    )
            except Exception as err:
                _LOGGER.exception("Unexpected error during device validation: %s", err)
                errors["base"] = "unknown"

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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow handler."""
        return SRNEOptionsFlowHandler(config_entry)


# Configuration presets for common use cases
CONFIGURATION_PRESETS = {
    "off_grid_solar": {
        "name": "Off-Grid Solar",
        "description": "Optimized for standalone solar + battery systems",
        "icon": "mdi:solar-power",
        "settings": {
            "output_priority": 2,  # SBU
            "charge_source_priority": 3,  # PV Only
            "discharge_stop_soc": 20,
            "switch_to_ac_soc": 10,
            "switch_to_battery_soc": 100,
            "max_ac_charge_current": 0,  # Disable AC charging
        },
    },
    "grid_tied": {
        "name": "Grid-Tied Solar",
        "description": "Grid backup with solar priority",
        "icon": "mdi:transmission-tower",
        "settings": {
            "output_priority": 0,  # Solar First
            "charge_source_priority": 0,  # PV Priority (AC backup)
            "discharge_stop_soc": 10,
            "switch_to_ac_soc": 20,
            "switch_to_battery_soc": 80,
        },
    },
    "ups_mode": {
        "name": "UPS Mode",
        "description": "Grid power with battery backup",
        "icon": "mdi:battery-charging",
        "settings": {
            "output_priority": 1,  # Mains First
            "charge_source_priority": 1,  # AC Priority
            "discharge_stop_soc": 20,
        },
    },
    "time_of_use": {
        "name": "Time-of-Use Optimization",
        "description": "Charge during cheap hours, discharge during peak",
        "icon": "mdi:clock-outline",
        "settings": {
            "charge_source_priority": 2,  # Hybrid
        },
    },
}


class SRNEOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for SRNE Inverter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        Args:
            config_entry: The config entry being configured
        """
        self.config_entry = config_entry
        self._current_section: str | None = None
        self._schema_builder: ConfigFlowSchemaBuilder | None = None

        # Initialize dynamic schema builder if feature flag enabled
        # Config will be loaded lazily when first accessed
        if USE_DYNAMIC_SCHEMAS:
            self._schema_builder = ConfigFlowSchemaBuilder()

    def _build_dynamic_schema(self, page_id: str) -> vol.Schema | None:
        """
        Build schema dynamically using YAML configuration.

        Args:
            page_id: Page identifier from config_pages in entities_pilot.yaml

        Returns:
            Voluptuous schema if dynamic schemas enabled, None otherwise
        """
        if not USE_DYNAMIC_SCHEMAS or not self._schema_builder:
            return None

        # Get current values from coordinator
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if not coordinator or not coordinator.data:
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
        """
        Validate user input using dynamic validation rules.

        Args:
            page_id: Page identifier
            user_input: User input from form
            all_values: All current configuration values

        Returns:
            Tuple of (is_valid, error_dict)
        """
        if not USE_DYNAMIC_SCHEMAS or not self._schema_builder:
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
        """
        Parse user input values to raw register values.

        Args:
            user_input: User input from form (scaled values)

        Returns:
            Dictionary of raw register values (unscaled)
        """
        if not USE_DYNAMIC_SCHEMAS or not self._schema_builder:
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

        # Get coordinator
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
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
        """
        Handle form submission with dynamic validation and parsing.

        Args:
            page_id: Page identifier
            user_input: User input from form

        Returns:
            Tuple of (success, errors)
        """
        if not USE_DYNAMIC_SCHEMAS or not self._schema_builder:
            return (False, {})

        # Get current values
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
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
                "presets": "Configuration Presets",
            },
        )

    async def async_step_battery_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure battery configuration (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Try dynamic validation and submission first
                if USE_DYNAMIC_SCHEMAS and self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "battery_config", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
                else:
                    # Fall back to legacy validation
                    validated = await self._validate_essential_settings(user_input)
                    if validated:
                        # Get coordinator for device config and write access
                        coordinator = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
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
                _LOGGER.error("Validation error in essential settings: %s", err)

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("battery_config")

        if dynamic_schema is not None:
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

        # Fall back to legacy hardcoded schema
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        # Check if coordinator has data
        if not coordinator or not coordinator.data:
            return self.async_show_form(
                step_id="battery_config",
                data_schema=vol.Schema({}),
                errors={"base": "no_inverter_data"},
                description_placeholders={
                    "description": "⚠️ Cannot read settings from inverter. Check connection and try again."
                },
            )

        # Build dynamic schema - only include fields with available data
        schema_dict = {}

        if "battery_capacity" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "battery_capacity",
                    default=coordinator.data["battery_capacity"],
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=400,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="Ah",
                )
            )

        if "battery_voltage" in coordinator.data:
            schema_dict[
                vol.Optional(
                    "battery_voltage",
                    default=coordinator.data["battery_voltage"],
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["12", "24", "36", "48"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(schema_dict)

        available_count = len(schema_dict)

        return self.async_show_form(
            step_id="battery_config",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "description": (
                    f"Configure battery settings (showing {available_count} available settings from inverter).\n\n"
                    "✓ Values shown are current inverter readings\n"
                    "⚠️ Only settings your inverter supports are shown\n"
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
                if USE_DYNAMIC_SCHEMAS and self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "battery_management", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
                else:
                    # Fall back to legacy validation
                    validated = await self._validate_battery_settings(user_input)
                    if validated:
                        # Get coordinator for device config and write access
                        coordinator = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
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
                _LOGGER.error(
                    "Validation error in battery_management settings: %s", err
                )

        # Try to build schema dynamically first
        dynamic_schema = self._build_dynamic_schema("battery_management")

        if dynamic_schema is not None:
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

        # Fall back to legacy hardcoded schema
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        # Check if coordinator has data
        if not coordinator or not coordinator.data:
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

    async def async_step_inverter_output(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure inverter output (inverter settings only)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Try dynamic validation and submission first
                if USE_DYNAMIC_SCHEMAS and self._schema_builder:
                    success, error_dict = await self._handle_form_submission_dynamic(
                        "inverter_output", user_input
                    )
                    if success:
                        return await self.async_step_init()
                    errors.update(error_dict)
                else:
                    # Fall back to legacy validation
                    validated = await self._validate_inverter_output_settings(
                        user_input
                    )
                    if validated:
                        # Get coordinator for device config and write access
                        coordinator = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
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

        # Fall back to legacy hardcoded schema
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        # Check if coordinator has data
        if not coordinator or not coordinator.data:
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
                            "inverter_password", 0
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
                ): cv.boolean,
                vol.Optional(
                    "enable_diagnostic_sensors",
                    default=current_options.get("enable_diagnostic_sensors", True),
                ): cv.boolean,
                vol.Optional(
                    "enable_calculated_sensors",
                    default=current_options.get("enable_calculated_sensors", True),
                ): cv.boolean,
                vol.Optional(
                    "clear_failed_registers",
                    default=False,
                ): cv.boolean,
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
                    if USE_DYNAMIC_SCHEMAS and self._schema_builder:
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
                        # Fall back to legacy approach
                        # Get coordinator for device config and write access
                        coordinator = self.hass.data.get(DOMAIN, {}).get(
                            self.config_entry.entry_id
                        )
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

        # Fall back to legacy hardcoded schema
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

        # Check if coordinator has data
        if not coordinator or not coordinator.data:
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
                    "enable_configurable_numbers",
                    default=current_options.get("enable_configurable_numbers", True),
                ): cv.boolean,
                vol.Optional(
                    "enable_configurable_selects",
                    default=current_options.get("enable_configurable_selects", True),
                ): cv.boolean,
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
                    "• Configurable Numbers: Write to inverter registers via Number entities\n"
                    "• Configurable Selects: Change inverter modes via Select entities\n"
                    "• Diagnostic Sensors: Temperature, fault codes, etc.\n"
                    "• Calculated Sensors: Efficiency, ratios, derived metrics\n"
                    "• Energy Dashboard: Integration with Home Assistant Energy\n\n"
                    "ℹ️ Submit to save and return to menu, or close dialog to cancel"
                ),
            },
        )

    async def _validate_essential_settings(self, settings: dict[str, Any]) -> bool:
        """Validate battery config settings."""
        # Validate battery voltage is in allowed values
        battery_voltage = settings.get("battery_voltage")
        if battery_voltage and battery_voltage not in [12, 24, 36, 48]:
            raise ValueError(
                f"Battery voltage must be 12V, 24V, 36V, or 48V. Got: {battery_voltage}V"
            )

        # Validate battery capacity
        battery_capacity = settings.get("battery_capacity")
        if battery_capacity and not (10 <= battery_capacity <= 400):
            raise ValueError(
                f"Battery capacity must be 10-400 Ah. Got: {battery_capacity} Ah"
            )

        return True

    async def _validate_battery_settings(self, settings: dict[str, Any]) -> bool:
        """Validate battery settings."""
        # Validate charge currents
        max_charge = settings.get("max_charge_current", 200)
        max_ac_charge = settings.get("max_ac_charge_current", 200)
        pv_max_charge = settings.get("pv_max_charge_current", 150)

        if max_ac_charge > max_charge:
            raise ValueError(
                f"AC charge current ({max_ac_charge}A) cannot exceed "
                f"max charge current ({max_charge}A)"
            )

        if pv_max_charge > max_charge:
            raise ValueError(
                f"PV charge current ({pv_max_charge}A) cannot exceed "
                f"max charge current ({max_charge}A)"
            )

        # Validate SOC thresholds are in order
        discharge_stop = settings.get("discharge_stop_soc", 0)
        low_soc = settings.get("low_soc_alarm", 0)
        switch_ac = settings.get("switch_to_ac_soc", 0)
        switch_battery = settings.get("switch_to_battery_soc", 100)

        if not (discharge_stop < low_soc <= switch_ac < switch_battery):
            raise ValueError(
                "SOC thresholds must be in order: "
                f"discharge_stop ({discharge_stop}%) < "
                f"low_soc_alarm ({low_soc}%) <= "
                f"switch_to_ac ({switch_ac}%) < "
                f"switch_to_battery ({switch_battery}%)"
            )

        return True

    async def _validate_inverter_output_settings(
        self, settings: dict[str, Any]
    ) -> bool:
        """Validate inverter output settings."""
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
