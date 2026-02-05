"""Binary sensor platform for SRNE Inverter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SRNEDataUpdateCoordinator
from .entity_factory import EntityFactory

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SRNE Inverter binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SRNEDataUpdateCoordinator = data["coordinator"]
    config = data["config"]

    # Load configurable entities from config
    try:
        entities = EntityFactory.create_entities_from_config(
            coordinator, entry, config, "binary_sensors"
        )
        async_add_entities(entities, True)
        _LOGGER.info(
            "Loaded %d binary sensor entities from configuration", len(entities)
        )
    except Exception as err:
        _LOGGER.error("Failed to load binary sensor entities: %s", err, exc_info=True)
        raise
