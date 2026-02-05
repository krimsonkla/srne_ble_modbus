# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""Switch platform for SRNE Inverter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SRNEDataUpdateCoordinator
from .entity_factory import EntityFactory
from .config_loader import load_entity_config

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# SETUP
# ============================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SRNE Inverter switches from a config entry."""
    coordinator: SRNEDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Load configurable entities from YAML
    try:
        config = await load_entity_config(hass, entry, "entities_pilot.yaml")
        entities = EntityFactory.create_entities_from_config(
            coordinator, entry, config, "switches"
        )
        async_add_entities(entities, True)
        _LOGGER.info("Loaded %d switch entities from configuration", len(entities))
    except Exception as err:
        _LOGGER.error("Failed to load switch entities: %s", err, exc_info=True)
        raise
