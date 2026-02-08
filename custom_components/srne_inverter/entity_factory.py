"""Entity factory for creating entities from configuration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .configurable_binary_sensor import ConfigurableBinarySensor
from .configurable_number import ConfigurableNumber
from .configurable_select import ConfigurableSelect
from .configurable_sensor import ConfigurableSensor
from .configurable_switch import ConfigurableSwitch
from .coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EntityFactory:
    """Factory for creating entities from configuration."""

    @staticmethod
    def create_sensor(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> ConfigurableSensor:
        """Create a sensor entity from configuration.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict

        Returns:
            ConfigurableSensor instance
        """
        return ConfigurableSensor(coordinator, entry, config)

    @staticmethod
    def create_switch(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_config: dict[str, Any],
    ) -> ConfigurableSwitch:
        """Create a switch entity from configuration.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict
            device_config: Full device configuration with registers
        """
        return ConfigurableSwitch(coordinator, entry, config, device_config)

    @staticmethod
    def create_select(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_config: dict[str, Any],
    ) -> ConfigurableSelect:
        """Create a select entity from configuration.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict
            device_config: Full device configuration with registers
        """
        return ConfigurableSelect(coordinator, entry, config, device_config)

    @staticmethod
    def create_binary_sensor(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> ConfigurableBinarySensor:
        """Create a binary sensor entity from configuration."""
        return ConfigurableBinarySensor(coordinator, entry, config)

    @staticmethod
    def create_number(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        device_config: dict[str, Any],
    ) -> ConfigurableNumber:
        """Create a number entity from configuration.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Entity configuration dict
            device_config: Full device configuration with registers
        """
        return ConfigurableNumber(coordinator, entry, config, device_config)

    @staticmethod
    def create_entities_from_config(
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        entity_type: str,
    ) -> list:
        """Create all entities of a given type from configuration.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            config: Full configuration dict
            entity_type: Type of entities to create (sensors, switches, etc.)

        Returns:
            List of entity instances
        """
        entities = []
        entity_configs = config.get(entity_type, [])

        factory_methods = {
            "sensors": EntityFactory.create_sensor,
            "switches": EntityFactory.create_switch,
            "selects": EntityFactory.create_select,
            "binary_sensors": EntityFactory.create_binary_sensor,
            "numbers": EntityFactory.create_number,
        }

        factory_method = factory_methods.get(entity_type)
        if not factory_method:
            _LOGGER.error("Unknown entity type: %s", entity_type)
            return entities

        for entity_config in entity_configs:
            try:
                # Check if entity should be enabled based on config flow options
                if not EntityFactory._is_entity_enabled(entry, entity_config, entity_type):
                    _LOGGER.debug(
                        "Skipping %s entity %s: disabled in options",
                        entity_type[:-1],
                        entity_config.get("name"),
                    )
                    continue

                # Pass device config to switches, selects, and numbers for register lookup
                if entity_type in ("switches", "selects", "numbers"):
                    entity = factory_method(coordinator, entry, entity_config, config)
                else:
                    entity = factory_method(coordinator, entry, entity_config)

                entities.append(entity)
                _LOGGER.debug(
                    "Created %s entity: %s",
                    entity_type[:-1],  # Remove 's'
                    entity_config["name"],
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to create entity %s: %s",
                    entity_config.get("name", "unknown"),
                    err,
                    exc_info=True,
                )

        return entities

    @staticmethod
    def _is_entity_enabled(
        entry: ConfigEntry, entity_config: dict[str, Any], entity_type: str
    ) -> bool:
        """Check if an entity is enabled in the config entry options.

        Args:
            entry: Config entry
            entity_config: Entity configuration
            entity_type: Type of entity (sensors, numbers, etc.)

        Returns:
            True if entity is enabled, False otherwise
        """
        options = entry.options

        # Configurable Numbers
        if entity_type == "numbers":
            return options.get("enable_configurable_numbers", True)

        # Configurable Selects
        if entity_type == "selects":
            return options.get("enable_configurable_selects", True)

        # Sensors (Diagnostic, Calculated, Energy)
        if entity_type == "sensors":
            # Diagnostic sensors
            if entity_config.get("entity_category") == "diagnostic":
                return options.get("enable_diagnostic_sensors", True)

            # Calculated sensors
            if entity_config.get("source_type") == "calculated":
                return options.get("enable_calculated_sensors", True)

            # Energy Dashboard sensors
            if entity_config.get("device_class") == "energy":
                return options.get("enable_energy_dashboard", True)

        # Default to enabled for other types (switches, binary_sensors, etc.)
        return True
