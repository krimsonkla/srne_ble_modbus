"""Base class for configuration-driven entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Manufacturer constant
MANUFACTURER = "SRNE"


class ConfigurableBaseEntity(CoordinatorEntity[SRNEDataUpdateCoordinator]):
    """Base class for configuration-driven entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the configurable entity.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict from YAML
        """
        super().__init__(coordinator)

        self._config = config
        self._entry = entry

        # Required fields
        entity_id = config["entity_id"]
        # Generate unique_id from entity_id
        self._attr_unique_id = f"{entry.entry_id}_{entity_id}"
        self._attr_name = config["name"]

        # Optional description field
        if description := config.get("description"):
            self._attr_entity_description = description

        # Log for verification during pilot
        _LOGGER.debug(
            "Created configurable entity: %s with unique_id: %s",
            self._attr_name,
            self._attr_unique_id,
        )

        # Optional fields with defaults
        self._attr_icon = config.get("icon")
        self._attr_entity_registry_enabled_default = config.get(
            "enabled_by_default", True
        )

        # Entity category (config, diagnostic, or None)
        if category := config.get("entity_category"):
            try:
                self._attr_entity_category = EntityCategory(category.lower())
            except ValueError:
                _LOGGER.debug(
                    "Invalid entity_category '%s' for %s, ignoring",
                    category,
                    self._attr_name,
                )

        # Device info (shared with all entities)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": MANUFACTURER,
            "model": "HF Series Inverter",
            "sw_version": "1.0",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available.

        An entity is hidden (unavailable) if:
        1. Parent class says unavailable
        2. Coordinator has no data
        3. Not connected to inverter
        4. Register has failed (not supported by inverter)
        5. Entity is in unavailable sensors list (e.g., calculated sensor with missing deps)
        """
        # Basic availability checks
        if not super().available:
            return False

        if self.coordinator.data is None:
            return False

        if not self.coordinator.data.get("connected", False):
            return False

        # Check if this specific entity should be hidden
        entity_id = self._config.get("entity_id")

        # Check if entity is explicitly unavailable (e.g., calculated sensor with missing deps)
        if entity_id and self.coordinator.is_entity_unavailable(entity_id):
            _LOGGER.debug(
                "Entity %s unavailable: in unavailable sensors list",
                entity_id
            )
            return False

        # Check if entity's register has failed (not supported by inverter)
        register_name = self._config.get("register")
        if register_name and self.coordinator.is_register_failed(register_name):
            _LOGGER.debug(
                "Entity %s unavailable: register %s has failed",
                entity_id,
                register_name
            )
            return False

        return True

    def _get_coordinator_value(self, key: str, default: Any = None) -> Any:
        """Get value from coordinator data.

        Args:
            key: Data key to retrieve
            default: Default value if key not found

        Returns:
            Value from coordinator data or default
        """
        if not self.coordinator.data:
            return default
        return self.coordinator.data.get(key, default)

    def _apply_scaling(self, value: float | int) -> float:
        """Apply scaling factor to value.

        Args:
            value: Raw value

        Returns:
            Scaled value
        """
        scaling = self._config.get("scaling", 1.0)
        return value * scaling

    def _apply_precision(self, value: float) -> float:
        """Round value to configured precision.

        Args:
            value: Value to round

        Returns:
            Rounded value
        """
        precision = self._config.get("precision", 2)
        return round(value, precision)

    def _evaluate_template(self, template: str, context: dict[str, Any]) -> Any:
        """Evaluate a Jinja2 template string.

        Args:
            template: Template string
            context: Variables available in template

        Returns:
            Evaluated template result
        """
        # Import here to avoid circular dependency
        from jinja2 import Template, TemplateSyntaxError

        try:
            tmpl = Template(template)
            return tmpl.render(**context)
        except TemplateSyntaxError as err:
            _LOGGER.error(
                "Template syntax error for %s: %s",
                self._attr_name,
                err,
            )
            return None
        except Exception as err:
            _LOGGER.error(
                "Error evaluating template for %s: %s",
                self._attr_name,
                err,
            )
            return None
