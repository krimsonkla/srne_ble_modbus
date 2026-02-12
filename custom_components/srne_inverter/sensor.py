# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""Sensor platform for SRNE Inverter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SRNEDataUpdateCoordinator
from .entity_factory import EntityFactory
from .entities.learned_timeout_sensor import create_learned_timeout_sensors

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# SETUP
# ============================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SRNE Inverter sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SRNEDataUpdateCoordinator = data["coordinator"]
    config = data["config"]

    all_entities = []

    # Load configurable entities from config
    try:
        entities = EntityFactory.create_entities_from_config(
            coordinator, entry, config, "sensors"
        )
        all_entities.extend(entities)
        _LOGGER.info("Loaded %d sensor entities from configuration", len(entities))
    except Exception as err:
        _LOGGER.error("Failed to load sensor entities: %s", err, exc_info=True)
        raise

    # Add diagnostic sensors for learned timeouts (Phase 4)
    try:
        diagnostic_sensors = create_learned_timeout_sensors(coordinator, entry)
        all_entities.extend(diagnostic_sensors)
        _LOGGER.info("Added %d learned timeout diagnostic sensors", len(diagnostic_sensors))
    except Exception as err:
        _LOGGER.warning(
            "Failed to create learned timeout diagnostic sensors: %s", err, exc_info=True
        )

    # Add all entities
    async_add_entities(all_entities, True)
