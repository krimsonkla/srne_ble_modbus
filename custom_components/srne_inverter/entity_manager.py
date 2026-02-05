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
        self._device_configs: dict[str, dict[str, Any]] = {}

    def set_device_config(self, config_entry_id: str, config: dict[str, Any]) -> None:
        """Set the device configuration for a specific config entry.

        Args:
            config_entry_id: Config entry ID
            config: Device configuration dictionary
        """
        self._device_configs[config_entry_id] = config
        _LOGGER.debug("Set device config for entry %s", config_entry_id)

    def _get_config_for_entry(self, config_entry_id: str) -> dict[str, Any] | None:
        """Get the device configuration for a specific config entry."""
        return self._device_configs.get(config_entry_id)

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
        """
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
        """
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
            Dict mapping category to status info
        """
        status: dict[str, dict[str, Any]] = {}
        config = self._get_config_for_entry(config_entry_id)

        if not config:
            return status

        # Identify unique categories in the config
        categories = set()
        for entity_type in [
            "sensors",
            "switches",
            "selects",
            "binary_sensors",
            "numbers",
        ]:
            for entity in config.get(entity_type, []):
                if cat := entity.get("entity_category"):
                    categories.add(cat)

        # Add entity type categories if they contain entities
        for cat in [
            "configurable_numbers",
            "configurable_selects",
            "diagnostic_sensors",
            "calculated_sensors",
            "3phase_sensors",
            "split_phase_sensors",
            "dual_pv_sensors",
        ]:
            if self._get_entity_ids_for_category(config_entry_id, cat):
                categories.add(cat)

        for category in categories:
            entity_ids = self._get_entity_ids_for_category(config_entry_id, category)
            enabled_count = 0
            disabled_count = 0
            entities = []

            for entity_id in entity_ids:
                registry_entry = self._entity_registry.async_get(entity_id)

                if registry_entry:
                    is_enabled = registry_entry.disabled_by is None
                    if is_enabled:
                        enabled_count += 1
                    else:
                        disabled_count += 1

                    entities.append(
                        {
                            "entity_id": entity_id,
                            "name": registry_entry.name or registry_entry.original_name,
                            "enabled": is_enabled,
                            "disabled_by": registry_entry.disabled_by,
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
            if is_enabled:
                entities = await self.enable_entity_category(config_entry_id, category)
                enabled_count += len(entities)
            else:
                entities = await self.disable_entity_category(config_entry_id, category)
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
        config = self._get_config_for_entry(config_entry_id)
        if not config:
            _LOGGER.warning("No device config found for entry %s", config_entry_id)
            return []

        entity_keys = []

        # Traditional Home Assistant entity categories (config, diagnostic)
        # and our custom groupings (3phase_sensors, etc.)
        for entity_type in [
            "sensors",
            "switches",
            "selects",
            "binary_sensors",
            "numbers",
        ]:
            for entity in config.get(entity_type, []):
                entity_id = entity.get("entity_id")
                if not entity_id:
                    continue

                # Check if matches entity_category field
                # e.g., category='diagnostic' matches entity_category='diagnostic'
                if entity.get("entity_category") == category:
                    entity_keys.append(entity_id)
                    continue

                # Support grouping names from configuration
                if (
                    category == "diagnostic_sensors"
                    and entity.get("entity_category") == "diagnostic"
                ):
                    entity_keys.append(entity_id)
                    continue
                if category == "configurable_numbers" and entity_type == "numbers":
                    entity_keys.append(entity_id)
                    continue
                if category == "configurable_selects" and entity_type == "selects":
                    entity_keys.append(entity_id)
                    continue
                if (
                    category == "calculated_sensors"
                    and entity.get("source_type") == "calculated"
                ):
                    entity_keys.append(entity_id)
                    continue

                # Check for feature-based groupings
                if (
                    "_b" in entity_id
                    or "_c" in entity_id
                    or "phase_b" in entity_id
                    or "phase_c" in entity_id
                ):
                    entity_keys.append(entity_id)
                elif category == "split_phase_sensors" and (
                    "bus_voltage" in entity_id
                    and ("positive" in entity_id or "negative" in entity_id)
                ):
                    entity_keys.append(entity_id)
                elif category == "dual_pv_sensors" and "pv2_" in entity_id:
                    entity_keys.append(entity_id)

        # Remove duplicates
        entity_keys = list(set(entity_keys))

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
        platform = self._get_platform_for_entity(config_entry_id, entity_key)

        # Build entity ID using domain and entity key
        # Format: platform.domain_entitykey
        return f"{platform}.{DOMAIN}_{entity_key}"

    def _get_platform_for_entity(
        self,
        config_entry_id: str,
        entity_key: str,
    ) -> Platform:
        """Determine platform for an entity key.

        Args:
            config_entry_id: Config entry ID
            entity_key: Entity key

        Returns:
            Home Assistant Platform
        """
        config = self._get_config_for_entry(config_entry_id)

        if config:
            platform_map = {
                "sensors": Platform.SENSOR,
                "switches": Platform.SWITCH,
                "selects": Platform.SELECT,
                "binary_sensors": Platform.BINARY_SENSOR,
                "numbers": Platform.NUMBER,
            }

            for entity_type, platform in platform_map.items():
                for entity in config.get(entity_type, []):
                    if entity.get("entity_id") == entity_key:
                        return platform

        # Fallback to simple matching if config not available or not found
        if "switch" in entity_key:
            return Platform.SWITCH
        if "select" in entity_key:
            return Platform.SELECT
        if "binary" in entity_key:
            return Platform.BINARY_SENSOR
        if "number" in entity_key or any(
            x in entity_key for x in ["current", "voltage", "power", "limit"]
        ):
            # Try to guess based on common number entity keywords
            # but default to sensor as it's safer
            pass

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


def get_entity_category_for_entity(
    hass: HomeAssistant, config_entry_id: str, entity_id: str
) -> str | None:
    """Determine which category an entity belongs to.

    Args:
        hass: Home Assistant instance
        config_entry_id: Config entry ID
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

    # Search for entity key in configuration
    manager = async_get_entity_manager(hass)
    config = manager._get_config_for_entry(config_entry_id)
    if not config:
        return None

    for entity_type in ["sensors", "switches", "selects", "binary_sensors", "numbers"]:
        for entity in config.get(entity_type, []):
            if entity.get("entity_id") == entity_key:
                # Return explicit category if present
                if category := entity.get("entity_category"):
                    return category

                # Map to grouping names for UI consistency
                if entity_type == "numbers":
                    return "configurable_numbers"
                if entity_type == "selects":
                    return "configurable_selects"
                if entity.get("source_type") == "calculated":
                    return "calculated_sensors"

                # Check for feature-based groupings
                if (
                    "_b" in entity_key
                    or "_c" in entity_key
                    or "phase_b" in entity_key
                    or "phase_c" in entity_key
                ):
                    return "3phase_sensors"
                if "bus_voltage" in entity_key and (
                    "positive" in entity_key or "negative" in entity_key
                ):
                    return "split_phase_sensors"
                if "pv2_" in entity_key:
                    return "dual_pv_sensors"

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
