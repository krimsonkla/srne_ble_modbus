"""Configurable binary sensor entity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry

from .configurable_base import ConfigurableBaseEntity
from ..coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ConfigurableBinarySensor(ConfigurableBaseEntity, BinarySensorEntity):
    """Binary sensor entity configured from YAML."""

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, config)

        # Set binary sensor-specific attributes
        if device_class := config.get("device_class"):
            try:
                self._attr_device_class = BinarySensorDeviceClass(device_class.lower())
            except (ValueError, AttributeError):
                try:
                    self._attr_device_class = BinarySensorDeviceClass(device_class)
                except ValueError:
                    _LOGGER.debug(
                        "Invalid device_class '%s' for binary sensor %s",
                        device_class,
                        self._attr_name,
                    )

        self._source_type = config.get("source_type", "register_bit")
        self._condition = config.get("condition", "any_nonzero")

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        if self._source_type == "register_bit":
            return self._check_register_bits()
        elif self._source_type == "coordinator_data":
            data_key = self._config["data_key"]
            return bool(self._get_coordinator_value(data_key, False))
        else:
            _LOGGER.error(
                "Unknown source_type '%s' for binary sensor %s",
                self._source_type,
                self._attr_name,
            )
            return None

    def _check_register_bits(self) -> bool:
        """Check register bit condition."""
        register_count = self._config.get("register_count", 1)

        # Get values (assuming coordinator stores them as list)
        data_key = self._config["entity_id"]
        values = self._get_coordinator_value(data_key, [])

        if not values:
            return False

        # Ensure values is a list
        if not isinstance(values, list):
            values = [values]

        # Apply condition
        if self._condition == "any_nonzero":
            return any(v != 0 for v in values[:register_count])
        elif self._condition == "all_nonzero":
            return all(v != 0 for v in values[:register_count])
        elif self._condition == "any_zero":
            return any(v == 0 for v in values[:register_count])
        else:
            _LOGGER.error(
                "Unknown condition '%s' for binary sensor %s",
                self._condition,
                self._attr_name,
            )
            return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attributes = {}

        # Add fault bit details if available
        if self._source_type == "register_bit":
            data_key = self._config["entity_id"]
            if values := self._get_coordinator_value(data_key):
                # Ensure values is a list
                if not isinstance(values, list):
                    values = [values]
                attributes["register_values"] = [hex(v) for v in values]

        return attributes
