# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""SRNE HF Series Inverter integration for Home Assistant.

This integration provides BLE-based monitoring and control for SRNE HF Series
hybrid inverters using Modbus RTU over BLE protocol.
"""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .config_loader import load_entity_config, merge_detected_features
from .entity_manager import async_get_entity_manager
from .const import DOMAIN
from .coordinator import SRNEDataUpdateCoordinator

# DI Container handles all wiring

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_FORCE_REFRESH = "force_refresh"
SERVICE_RESET_STATISTICS = "reset_statistics"
SERVICE_RESTART_INVERTER = "restart_inverter"
SERVICE_HIDE_UNSUPPORTED = "hide_unsupported_entities"

# Service schemas
RESTART_INVERTER_SCHEMA = vol.Schema(
    {
        vol.Required("confirm"): cv.boolean,
    }
)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


async def _hide_failed_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: SRNEDataUpdateCoordinator,
) -> int:
    """Disable entities in entity registry whose registers have failed.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        coordinator: Coordinator with failed register information

    Returns:
        Number of entities disabled
    """
    if not coordinator._failed_registers and not coordinator._unavailable_sensors:
        _LOGGER.debug("No failed registers or unavailable sensors to hide")
        return 0

    entity_reg = er.async_get(hass)
    device_config = coordinator._device_config
    disabled_count = 0

    # Get all entities for this integration
    entities = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    for entity in entities:
        # Extract register name from entity unique_id
        # Format: {entry_id}_{entity_id}
        entity_id_part = (
            entity.unique_id.split("_", 1)[1] if "_" in entity.unique_id else None
        )

        if not entity_id_part:
            continue

        # Check if entity is in unavailable sensors list
        if entity_id_part in coordinator._unavailable_sensors:
            if entity.disabled_by != er.RegistryEntryDisabler.INTEGRATION:
                entity_reg.async_update_entity(
                    entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )
                disabled_count += 1
                _LOGGER.info(
                    "Disabled unavailable entity: %s (missing dependencies)",
                    entity.entity_id,
                )
            continue

        # Find the register for this entity
        register_name = None

        # Check all entity types for matching entity_id
        for entity_type in [
            "sensors",
            "numbers",
            "selects",
            "switches",
            "binary_sensors",
        ]:
            entities_list = device_config.get(entity_type, [])
            for ent_config in entities_list if isinstance(entities_list, list) else []:
                if ent_config.get("entity_id") == entity_id_part:
                    register_name = ent_config.get("register")
                    break
            if register_name:
                break

        # Check if register has failed
        if register_name and coordinator.is_register_failed(register_name):
            if entity.disabled_by != er.RegistryEntryDisabler.INTEGRATION:
                entity_reg.async_update_entity(
                    entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
                )
                disabled_count += 1
                _LOGGER.info(
                    "Disabled entity %s: register %s not supported by inverter",
                    entity.entity_id,
                    register_name,
                )

    if disabled_count > 0:
        _LOGGER.info(
            "Disabled %d unsupported entities. They will be hidden from UI.",
            disabled_count,
        )

    return disabled_count


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SRNE Inverter from a config entry."""
    _LOGGER.debug(
        "Setting up SRNE Inverter integration for device %s", entry.data.get("address")
    )

    # Load device configuration from YAML
    try:
        device_config = await load_entity_config(hass, entry, "entities_pilot.yaml")

        # Merge detected features and user overrides from config entry into device config
        detected_features = entry.data.get("detected_features")
        feature_overrides = entry.data.get("feature_overrides")

        if detected_features or feature_overrides:
            if detected_features:
                _LOGGER.info(
                    "Loading detected features from config entry: %d features",
                    len(detected_features),
                )
            if feature_overrides:
                _LOGGER.info(
                    "Loading feature overrides from config entry: %d overrides",
                    len(feature_overrides),
                )
            device_config = merge_detected_features(
                device_config, detected_features, feature_overrides
            )
        else:
            _LOGGER.debug(
                "No detected features or overrides in config entry, using YAML defaults (backward compatibility)"
            )

        _LOGGER.info(
            "Loaded device configuration: %s %s (protocol %s)",
            device_config.get("device", {}).get("manufacturer"),
            device_config.get("device", {}).get("model"),
            device_config.get("device", {}).get("protocol_version"),
        )

        # Update entity manager with device config
        entity_manager = async_get_entity_manager(hass)
        entity_manager.set_device_config(entry.entry_id, device_config)
    except Exception as err:
        _LOGGER.error("Failed to load device configuration: %s", err)
        raise ConfigEntryNotReady(
            f"Failed to load device configuration: {err}"
        ) from err

    # Use DI Container for Complete Wiring
    from .presentation.container import create_container

    container = create_container(hass, entry, device_config)
    coordinator = container.coordinator

    # Load previously failed registers before first refresh
    await coordinator._load_failed_registers()

    # Perform first refresh
    # Exception handling pattern: ConfigEntryNotReady triggers HA's built-in retry
    # This allows Home Assistant to automatically retry connection on startup failures
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to connect to SRNE inverter: %s", err)
        raise ConfigEntryNotReady(f"Failed to connect to inverter: {err}") from err

    # Store coordinator and config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "config": device_config,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide unsupported entities after first refresh
    await _hide_failed_entities(hass, entry, coordinator)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services
    async def handle_force_refresh(call: ServiceCall) -> None:
        """Handle force refresh service call."""
        data = hass.data[DOMAIN][entry.entry_id]
        coordinator = data["coordinator"]
        await coordinator.async_request_refresh()
        _LOGGER.info("Force refresh triggered for SRNE inverter")

    async def handle_reset_statistics(call: ServiceCall) -> None:
        """Handle reset statistics service call."""
        data = hass.data[DOMAIN][entry.entry_id]
        coordinator = data["coordinator"]

        # Reset diagnostic counters (NOT inverter statistics)
        coordinator._failed_reads = 0
        coordinator._total_updates = 0

        _LOGGER.info("Diagnostic statistics reset for SRNE inverter")

        # Trigger update to refresh sensor states
        await coordinator.async_request_refresh()

    async def handle_restart_inverter(call: ServiceCall) -> None:
        """Handle restart inverter service call."""
        if not call.data.get("confirm", False):
            raise ValueError("Restart requires confirmation parameter set to true")

        data = hass.data[DOMAIN][entry.entry_id]
        coordinator = data["coordinator"]

        _LOGGER.debug(
            "Inverter restart requested - writing to CmdMachineReset register"
        )

        # Write to CmdMachineReset register (0xDF01)
        # Value 0x0001 triggers restart
        success = await coordinator.async_write_register(0xDF01, 0x0001)

        if success:
            _LOGGER.info("Inverter restart command sent successfully")
        else:
            raise HomeAssistantError("Failed to send restart command to inverter")

    async def handle_hide_unsupported(call: ServiceCall) -> None:
        """Handle hide unsupported entities service call."""
        data = hass.data[DOMAIN][entry.entry_id]
        coordinator = data["coordinator"]

        # Disable entities with failed registers
        disabled_count = await _hide_failed_entities(hass, entry, coordinator)

        _LOGGER.info(
            "Hide unsupported entities complete: %d entities disabled", disabled_count
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_REFRESH,
        handle_force_refresh,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_STATISTICS,
        handle_reset_statistics,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_INVERTER,
        handle_restart_inverter,
        schema=RESTART_INVERTER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_HIDE_UNSUPPORTED,
        handle_hide_unsupported,
    )

    _LOGGER.info(
        "SRNE Inverter integration setup complete for device %s",
        entry.data.get("address"),
    )
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading SRNE Inverter integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove coordinator and clean up
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: SRNEDataUpdateCoordinator = data["coordinator"]
        await coordinator.async_shutdown()

        # Unregister services
        hass.services.async_remove(DOMAIN, SERVICE_FORCE_REFRESH)
        hass.services.async_remove(DOMAIN, SERVICE_RESET_STATISTICS)
        hass.services.async_remove(DOMAIN, SERVICE_RESTART_INVERTER)

    return unload_ok
