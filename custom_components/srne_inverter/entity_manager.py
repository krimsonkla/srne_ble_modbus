"""Entity Registry Management for SRNE Inverter Integration.

This module provides centralized entity registry operations for enabling/disabling
configurable entities by category or individually. It integrates with Home Assistant's
entity registry and provides persistence for user preferences.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Storage version for entity preferences
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.entity_preferences"

# Entity category mappings based on the YAML configurations
ENTITY_CATEGORIES = {
    "configurable_numbers": [
        "max_ac_charge_current",
        "max_charge_current",
        "float_charge_voltage",
        "bulk_charge_voltage",
        "battery_low_voltage",
        "battery_shutdown_voltage",
        "grid_charge_start_voltage",
        "pv_power_balance",
    ],
    "configurable_selects": [
        "energy_priority",
        "output_priority",
        "charge_source_priority",
        "battery_type",
        "ac_input_range",
    ],
    "diagnostic_sensors": [
        "update_duration",
        "failed_reads_count",
        "last_update",
        "ble_connection_quality",
        "success_rate",
        "system_datetime",
        "grid_on_countdown",
        "total_bus_voltage",
        "transformer_temperature",
        "ambient_temperature",
        "charge_power_total",
        "load_current",
        "battery_cycle_count",
        "battery_charge_rate",
        "battery_discharge_rate",
        "thermal_stress_indicator",
        "system_health_score",
    ],
    "calculated_sensors": [
        "grid_import_power",
        "grid_export_power",
        "battery_power",
        "battery_charge_power",
        "battery_discharge_power",
        "self_sufficiency",
        "grid_dependency",
        "system_efficiency",
        "battery_time_to_full",
        "battery_time_to_empty",
        "energy_flow_balance",
        "pv_utilization_rate",
        "battery_contribution_rate",
        "daily_solar_value",
        "round_trip_efficiency",
        "pv_to_load_direct_ratio",
        "daily_battery_throughput",
    ],
    "3phase_sensors": [
        "grid_voltage_b",
        "grid_voltage_c",
        "grid_current_b",
        "grid_current_c",
        "grid_power_b",
        "grid_power_c",
        "inverter_voltage_b",
        "inverter_voltage_c",
        "inverter_current_b",
        "inverter_current_c",
        "load_current_b",
        "load_current_c",
        "load_power_b",
        "load_power_c",
        "load_power_b_home",
        "load_power_c_home",
    ],
    "split_phase_sensors": [
        "positive_bus_voltage",
        "negative_bus_voltage",
    ],
    "dual_pv_sensors": [
        "pv2_voltage",
        "pv2_current",
        "pv2_power",
    ],
}


class EntityManager:
    """Manage entity registry operations for SRNE Inverter entities."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the entity manager.

        Args:
            hass: Home Assistant instance
        """
        self._hass = hass
        self._entity_registry = er.async_get(hass)
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._preferences: dict[str, dict[str, bool]] = {}

    async def async_load(self) -> None:
        """Load entity preferences from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._preferences = data.get("preferences", {})
                _LOGGER.debug("Loaded entity preferences: %s", self._preferences)
        except Exception as err:
            _LOGGER.error("Failed to load entity preferences: %s", err)
            self._preferences = {}

    async def async_save(self) -> None:
        """Save entity preferences to storage."""
        try:
            await self._store.async_save({"preferences": self._preferences})
            _LOGGER.debug("Saved entity preferences")
        except Exception as err:
            _LOGGER.error("Failed to save entity preferences: %s", err)

    async def enable_entity_category(
        self,
        config_entry_id: str,
        category: str,
    ) -> list[str]:
        """Enable all entities in a category.

        Args:
            config_entry_id: Config entry ID
            category: Entity category name (e.g., 'configurable_numbers')

        Returns:
            List of entity IDs that were enabled

        Raises:
            ValueError: If category is invalid
        """
        if category not in ENTITY_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Valid categories: {', '.join(ENTITY_CATEGORIES.keys())}"
            )

        entity_ids = self._get_entity_ids_for_category(config_entry_id, category)
        enabled = await self.enable_specific_entities(entity_ids)

        # Update preferences
        if config_entry_id not in self._preferences:
            self._preferences[config_entry_id] = {}
        self._preferences[config_entry_id][category] = True
        await self.async_save()

        _LOGGER.info(
            "Enabled category '%s': %d entities enabled",
            category,
            len(enabled),
        )
        return enabled

    async def disable_entity_category(
        self,
        config_entry_id: str,
        category: str,
    ) -> list[str]:
        """Disable all entities in a category.

        Args:
            config_entry_id: Config entry ID
            category: Entity category name

        Returns:
            List of entity IDs that were disabled

        Raises:
            ValueError: If category is invalid
        """
        if category not in ENTITY_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Valid categories: {', '.join(ENTITY_CATEGORIES.keys())}"
            )

        entity_ids = self._get_entity_ids_for_category(config_entry_id, category)
        disabled = await self.disable_specific_entities(entity_ids)

        # Update preferences
        if config_entry_id not in self._preferences:
            self._preferences[config_entry_id] = {}
        self._preferences[config_entry_id][category] = False
        await self.async_save()

        _LOGGER.info(
            "Disabled category '%s': %d entities disabled",
            category,
            len(disabled),
        )
        return disabled

    async def get_entity_status(
        self,
        config_entry_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Get status of all entities by category.

        Args:
            config_entry_id: Config entry ID

        Returns:
            Dict mapping category to status info:
            {
                "category_name": {
                    "enabled_count": 5,
                    "disabled_count": 2,
                    "total_count": 7,
                    "entities": [list of entity details]
                }
            }
        """
        status: dict[str, dict[str, Any]] = {}

        for category, entity_keys in ENTITY_CATEGORIES.items():
            enabled_count = 0
            disabled_count = 0
            entities = []

            for entity_key in entity_keys:
                entity_id = self._build_entity_id(config_entry_id, entity_key)
                entity = self._entity_registry.async_get(entity_id)

                if entity:
                    is_enabled = entity.disabled_by is None
                    if is_enabled:
                        enabled_count += 1
                    else:
                        disabled_count += 1

                    entities.append(
                        {
                            "entity_id": entity_id,
                            "name": entity.name or entity.original_name,
                            "enabled": is_enabled,
                            "disabled_by": entity.disabled_by,
                        }
                    )

            status[category] = {
                "enabled_count": enabled_count,
                "disabled_count": disabled_count,
                "total_count": enabled_count + disabled_count,
                "entities": entities,
            }

        return status

    async def enable_specific_entities(
        self,
        entity_ids: list[str],
    ) -> list[str]:
        """Enable specific entities by entity_id.

        Args:
            entity_ids: List of entity IDs to enable

        Returns:
            List of entity IDs that were successfully enabled
        """
        return await self._bulk_update_entities(entity_ids, disabled_by=None)

    async def disable_specific_entities(
        self,
        entity_ids: list[str],
    ) -> list[str]:
        """Disable specific entities by entity_id.

        Args:
            entity_ids: List of entity IDs to disable

        Returns:
            List of entity IDs that were successfully disabled
        """
        return await self._bulk_update_entities(
            entity_ids, disabled_by=er.RegistryEntryDisabler.USER
        )

    async def apply_preferences(
        self,
        config_entry_id: str,
    ) -> dict[str, int]:
        """Apply saved preferences for a config entry.

        Args:
            config_entry_id: Config entry ID

        Returns:
            Dict with counts: {"enabled": 5, "disabled": 3}
        """
        if config_entry_id not in self._preferences:
            _LOGGER.debug("No saved preferences for config entry %s", config_entry_id)
            return {"enabled": 0, "disabled": 0}

        enabled_count = 0
        disabled_count = 0

        preferences = self._preferences[config_entry_id]

        for category, is_enabled in preferences.items():
            if category not in ENTITY_CATEGORIES:
                _LOGGER.debug("Unknown category in preferences: %s", category)
                continue

            if is_enabled:
                entities = await self.enable_entity_category(config_entry_id, category)
                enabled_count += len(entities)
            else:
                entities = await self.disable_entity_category(
                    config_entry_id, category
                )
                disabled_count += len(entities)

        _LOGGER.info(
            "Applied preferences for %s: %d enabled, %d disabled",
            config_entry_id,
            enabled_count,
            disabled_count,
        )

        return {"enabled": enabled_count, "disabled": disabled_count}

    def _get_entity_ids_for_category(
        self,
        config_entry_id: str,
        category: str,
    ) -> list[str]:
        """Get full entity IDs for a category.

        Args:
            config_entry_id: Config entry ID
            category: Entity category name

        Returns:
            List of full entity IDs
        """
        entity_keys = ENTITY_CATEGORIES.get(category, [])
        return [
            self._build_entity_id(config_entry_id, entity_key)
            for entity_key in entity_keys
        ]

    def _build_entity_id(self, config_entry_id: str, entity_key: str) -> str:
        """Build full entity ID from config entry and entity key.

        Args:
            config_entry_id: Config entry ID
            entity_key: Entity key (e.g., 'battery_soc')

        Returns:
            Full entity ID (e.g., 'sensor.srne_inverter_battery_soc')
        """
        # Determine platform based on category
        platform = self._get_platform_for_entity(entity_key)

        # Get the config entry to extract device name
        config_entry = self._hass.config_entries.async_get_entry(config_entry_id)
        if not config_entry:
            _LOGGER.debug(
                "Config entry %s not found for entity %s",
                config_entry_id,
                entity_key,
            )
            # Fallback to generic name
            return f"{platform}.{DOMAIN}_{entity_key}"

        # Build entity ID using domain and entity key
        # Format: platform.domain_entitykey
        return f"{platform}.{DOMAIN}_{entity_key}"

    def _get_platform_for_entity(self, entity_key: str) -> str:
        """Determine platform for an entity key.

        Args:
            entity_key: Entity key

        Returns:
            Platform string (sensor, number, select, etc.)
        """
        # Check in which category the entity belongs
        for category, entities in ENTITY_CATEGORIES.items():
            if entity_key in entities:
                if "number" in category:
                    return Platform.NUMBER
                elif "select" in category:
                    return Platform.SELECT
                elif "binary" in category:
                    return Platform.BINARY_SENSOR
                else:
                    return Platform.SENSOR

        # Default to sensor
        return Platform.SENSOR

    async def _bulk_update_entities(
        self,
        entity_ids: list[str],
        disabled_by: er.RegistryEntryDisabler | None,
    ) -> list[str]:
        """Bulk update entity disabled status.

        Args:
            entity_ids: List of entity IDs to update
            disabled_by: Set to RegistryEntryDisabler.USER to disable,
                        None to enable

        Returns:
            List of entity IDs that were successfully updated
        """
        updated = []

        for entity_id in entity_ids:
            if not validate_entity_exists(self._hass, entity_id):
                _LOGGER.debug("Entity %s not found in registry", entity_id)
                continue

            try:
                self._entity_registry.async_update_entity(
                    entity_id,
                    disabled_by=disabled_by,
                )
                updated.append(entity_id)
                _LOGGER.debug(
                    "Updated entity %s: disabled_by=%s",
                    entity_id,
                    disabled_by,
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to update entity %s: %s",
                    entity_id,
                    err,
                )

        return updated


# Utility functions


def validate_entity_exists(
    hass: HomeAssistant,
    entity_id: str,
) -> bool:
    """Check if entity exists in registry.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to check

    Returns:
        True if entity exists, False otherwise
    """
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get(entity_id)
    return entity is not None


def get_entity_category_for_entity(entity_id: str) -> str | None:
    """Determine which category an entity belongs to.

    Args:
        entity_id: Full entity ID

    Returns:
        Category name or None if not found
    """
    # Extract entity key from entity_id
    # Format: platform.domain_entitykey
    if "." not in entity_id:
        return None

    entity_key = entity_id.split(".", 1)[1]

    # Remove domain prefix if present
    if entity_key.startswith(f"{DOMAIN}_"):
        entity_key = entity_key[len(DOMAIN) + 1 :]

    # Search for entity key in categories
    for category, entities in ENTITY_CATEGORIES.items():
        if entity_key in entities:
            return category

    return None


@callback
def async_get_entity_manager(hass: HomeAssistant) -> EntityManager:
    """Get or create the entity manager instance.

    Args:
        hass: Home Assistant instance

    Returns:
        EntityManager instance
    """
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if "entity_manager" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entity_manager"] = EntityManager(hass)

    return hass.data[DOMAIN]["entity_manager"]
