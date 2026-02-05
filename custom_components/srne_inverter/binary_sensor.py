"""Binary sensor platform for SRNE Inverter integration."""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .config_loader import load_entity_config
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
    coordinator: SRNEDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Load configurable entities
    configurable_entities = []
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "config", "entities_pilot.yaml"
        )

        if os.path.exists(config_path):
            config = await load_entity_config(hass, entry, "entities_pilot.yaml")

            configurable_entities = EntityFactory.create_entities_from_config(
                coordinator, entry, config, "binary_sensors"
            )

            _LOGGER.info(
                "Loaded %d configurable binary sensor entities from pilot config",
                len(configurable_entities),
            )
    except Exception as err:
        _LOGGER.debug(
            "Failed to load configurable binary sensors: %s",
            err,
        )

    async_add_entities(configurable_entities)
    _LOGGER.debug(
        "Added %d binary sensor entities",
        len(configurable_entities),
    )
