"""Entity factory for creating entities from configuration.

This module provides the EntityFactory class for creating Home Assistant entities
from YAML configuration. The factory handles:

- Entity creation for sensors, switches, selects, numbers, and binary sensors
- Availability checking based on failed registers and hardware features
- Register dependency resolution for calculated entities
- Hardware feature compatibility validation

Architecture:
    The factory uses static methods for stateless entity creation, with helper
    methods for availability checking and register validation. Address parsing
    is delegated to domain.helpers.address_helpers for consistency.

Example:
    >>> entities = EntityFactory.create_entities_from_config(
    ...     coordinator, entry, config, "sensors"
    ... )
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .entities.configurable_binary_sensor import ConfigurableBinarySensor
from .entities.configurable_number import ConfigurableNumber
from .entities.configurable_select import ConfigurableSelect
from .entities.configurable_sensor import ConfigurableSensor
from .entities.configurable_switch import ConfigurableSwitch
from .coordinator import SRNEDataUpdateCoordinator
from .domain.helpers.address_helpers import parse_address

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
                if not EntityFactory._is_entity_enabled(
                    entry, entity_config, entity_type
                ):
                    _LOGGER.debug(
                        "Skipping %s entity %s: disabled in options",
                        entity_type[:-1],
                        entity_config.get("name"),
                    )
                    continue

                # Check if entity depends on failed register
                if not EntityFactory._is_entity_available(
                    coordinator, config, entity_config, entity_type
                ):
                    entity_name = entity_config.get("name")
                    entity_id = entity_config.get("entity_id")
                    _LOGGER.info(
                        "Skipping %s entity %s: register failed or hardware feature disabled",
                        entity_type[:-1],
                        entity_name or entity_id,
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
    def _is_entity_available(
        coordinator: SRNEDataUpdateCoordinator,
        config: dict[str, Any],
        entity_config: dict[str, Any],
        entity_type: str,
    ) -> bool:
        """Check if an entity's register is available (not failed, not disabled).

        Args:
            coordinator: Data update coordinator with failed register tracking
            config: Full device configuration with registers and features
            entity_config: Entity configuration
            entity_type: Type of entity (sensors, numbers, etc.)

        Returns:
            True if entity's register is available, False otherwise
        """
        # Check calculated sensor dependencies first
        if not EntityFactory._check_calculated_dependencies(
            coordinator, config, entity_config
        ):
            return False

        # Get and validate register name
        register_name = EntityFactory._extract_register_name(
            entity_config, entity_type, config
        )
        if not register_name:
            return True  # No register dependency, entity is available

        # Check if register failed
        if coordinator.is_register_failed(register_name):
            _LOGGER.debug(
                "Entity %s depends on failed register %s",
                entity_config.get("name") or entity_config.get("entity_id"),
                register_name,
            )
            return False

        # Check if register in disabled hardware feature range
        if not EntityFactory._is_register_enabled_by_features(config, register_name):
            _LOGGER.debug(
                "Entity %s register in disabled hardware feature range",
                entity_config.get("name") or entity_config.get("entity_id"),
            )
            return False

        # Check if register in disabled user preference group
        if not EntityFactory._is_register_enabled_by_user_preferences(
            coordinator, config, register_name
        ):
            _LOGGER.debug(
                "Entity %s register in disabled user preference group",
                entity_config.get("name") or entity_config.get("entity_id"),
            )
            return False

        return True

    @staticmethod
    def _check_calculated_dependencies(
        coordinator: SRNEDataUpdateCoordinator,
        config: dict[str, Any],
        entity_config: dict[str, Any],
    ) -> bool:
        """Check if calculated sensor has all required dependencies.

        Args:
            coordinator: Data update coordinator
            config: Full device configuration
            entity_config: Entity configuration

        Returns:
            True if all dependencies available or not a calculated sensor
        """
        if entity_config.get("source_type") != "calculated":
            return True

        depends_on = entity_config.get("depends_on", [])
        for dep_key in depends_on:
            if not EntityFactory._is_data_key_available(coordinator, config, dep_key):
                _LOGGER.debug(
                    "Calculated sensor %s unavailable: dependency '%s' is not available",
                    entity_config.get("name") or entity_config.get("entity_id"),
                    dep_key,
                )
                return False
        return True

    @staticmethod
    def _extract_register_name(
        entity_config: dict[str, Any], entity_type: str, config: dict[str, Any]
    ) -> str | None:
        """Extract register name from entity configuration.

        Args:
            entity_config: Entity configuration
            entity_type: Type of entity (sensors, numbers, etc.)
            config: Full device configuration

        Returns:
            Register name or None if no register dependency
        """
        # For switches, selects, numbers - use 'register' field
        if entity_type in ("switches", "selects", "numbers"):
            return entity_config.get("register")

        # For sensors - map data_key to register
        data_key = entity_config.get("data_key")
        if data_key and data_key in config.get("registers", {}):
            return data_key

        return None

    @staticmethod
    def _is_data_key_available(
        coordinator: SRNEDataUpdateCoordinator,
        config: dict[str, Any],
        data_key: str,
    ) -> bool:
        """Check if a data key (register) is available.

        Args:
            coordinator: Data update coordinator
            config: Full device configuration
            data_key: Data key to check (register name or calculated field)

        Returns:
            True if data key is available, False otherwise
        """
        # Check if this data_key is a register
        if data_key in config.get("registers", {}):
            register_name = data_key

            # Check if register has failed
            if coordinator.is_register_failed(register_name):
                return False

            # Check if register is disabled by hardware feature
            if not EntityFactory._is_register_enabled_by_features(
                config, register_name
            ):
                return False

        # If not a direct register, assume it's a calculated field
        # Check if any sensor with this entity_id exists
        # For now, we can't validate calculated dependencies at creation time
        # (would need to know which calculated sensors exist, creating circular dependency)
        # So we assume calculated dependencies are available

        return True

    @staticmethod
    def _is_register_enabled_by_features(
        config: dict[str, Any],
        register_name: str,
    ) -> bool:
        """Check if a register is enabled by hardware features.

        Args:
            config: Full device configuration
            register_name: Register name to check

        Returns:
            True if register is in an enabled feature range or no feature restriction,
            False if register is in a disabled feature range
        """
        reg_def = config.get("registers", {}).get(register_name)
        if not reg_def:
            return True  # Unknown register, assume enabled

        address = reg_def.get("address")
        if address is None:
            return True

        # Parse address using helper (handles hex strings and integers)
        try:
            address = parse_address(address)
        except ValueError:
            _LOGGER.warning("Invalid address format for register %s", register_name)
            return True

        # Check if address is in any disabled feature range
        device_config = config.get("device", {})
        features = device_config.get("features", {})
        feature_ranges = device_config.get("feature_ranges", {})

        for feature_name, feature_enabled in features.items():
            if not feature_enabled:  # Feature is disabled
                if EntityFactory._address_in_disabled_range(
                    address, feature_name, feature_ranges, register_name
                ):
                    return False

        return True

    @staticmethod
    def _address_in_disabled_range(
        address: int,
        feature_name: str,
        feature_ranges: dict[str, Any],
        register_name: str,
    ) -> bool:
        """Check if address falls within a disabled feature range.

        Args:
            address: Register address to check
            feature_name: Name of the disabled feature
            feature_ranges: Feature range definitions
            register_name: Register name for logging

        Returns:
            True if address is in a disabled range
        """
        ranges = feature_ranges.get(feature_name, [])
        for range_def in ranges:
            start = range_def.get("start")
            end = range_def.get("end")

            # Parse range boundaries using helper
            try:
                start = parse_address(start) if start is not None else None
                end = parse_address(end) if end is not None else None
            except ValueError:
                _LOGGER.warning("Invalid range format for feature %s", feature_name)
                continue

            if start is not None and end is not None and start <= address <= end:
                _LOGGER.debug(
                    "Register %s (0x%04X) in disabled feature range: %s",
                    register_name,
                    address,
                    feature_name,
                )
                return True

        return False

    @staticmethod
    def _is_register_enabled_by_user_preferences(
        coordinator: SRNEDataUpdateCoordinator,
        config: dict[str, Any],
        register_name: str,
    ) -> bool:
        """Check if a register is enabled by user preferences (show/hide groups).

        User preferences are different from hardware features:
        - Hardware features: Auto-detected capabilities (grid_tie, three_phase, etc.)
        - User preferences: Manual choices to show/hide entity groups

        Examples:
        - show_equalization_settings: Show/hide battery equalization settings
        - show_pv2_settings: Show/hide second PV panel entities
        - show_pv_settings: Show/hide all PV-related entities

        Args:
            coordinator: Data update coordinator
            config: Full device configuration
            register_name: Register name to check

        Returns:
            True if register is enabled by user preferences, False if hidden
        """
        reg_def = config.get("registers", {}).get(register_name)
        if not reg_def:
            return True  # Unknown register, assume enabled

        address = reg_def.get("address")
        if address is None:
            return True

        # Parse address using helper
        try:
            address = parse_address(address)
        except ValueError:
            _LOGGER.warning(
                "Invalid address format for register %s in user preference check",
                register_name,
            )
            return True

        # Get user preferences from config entry options
        # Access through coordinator's _config_entry if available
        if not hasattr(coordinator, "_config_entry"):
            return True  # No config entry, assume enabled

        options = coordinator._config_entry.options

        # Get user preference ranges from device config
        device_config = config.get("device", {})
        user_preferences = device_config.get("user_preferences", {})

        # Check each preference group
        for pref_name, pref_config in user_preferences.items():
            # Check if user has disabled this preference group
            option_key = f"show_{pref_name}"
            is_enabled = options.get(
                option_key, pref_config.get("enabled_by_default", True)
            )

            if not is_enabled:  # Preference group is hidden
                # Check if register is in this preference group's ranges
                ranges = pref_config.get("ranges", [])
                for range_def in ranges:
                    start = range_def.get("start")
                    end = range_def.get("end")

                    # Parse range boundaries
                    try:
                        start = parse_address(start) if start is not None else None
                        end = parse_address(end) if end is not None else None
                    except ValueError:
                        _LOGGER.warning(
                            "Invalid range format for user preference %s", pref_name
                        )
                        continue

                    if (
                        start is not None
                        and end is not None
                        and start <= address <= end
                    ):
                        _LOGGER.debug(
                            "Register %s (0x%04X) in disabled user preference group: %s",
                            register_name,
                            address,
                            pref_name,
                        )
                        return False

        return True

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

        Note:
            Numbers and selects are now controlled by hardware feature detection,
            not by manual toggles. They are always "enabled" here and will be
            filtered by _is_entity_available() based on detected features.
        """
        options = entry.options

        # Numbers and Selects: Always enabled, filtered by hardware detection
        if entity_type in ("numbers", "selects"):
            return True

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
