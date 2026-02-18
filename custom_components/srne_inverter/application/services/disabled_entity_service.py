"""Service for detecting and tracking user-disabled entities."""

import logging
from typing import Any, Callable, Dict, Set

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as er

from ...domain.interfaces.i_disabled_entity_service import IDisabledEntityService

_LOGGER = logging.getLogger(__name__)


class DisabledEntityService(IDisabledEntityService):
    """Service for detecting user-disabled entities and mapping to registers.

    This service encapsulates all entity registry interaction and provides
    a clean interface for the coordinator to query disabled entity state
    without violating SRP.

    Responsibilities:
    - Query entity registry for disabled entities
    - Map entity IDs to register addresses
    - Subscribe to entity registry events
    - Notify subscribers of changes

    Example:
        >>> service = DisabledEntityService(hass, config_entry, register_definitions)
        >>> disabled = service.get_disabled_addresses()
        >>> unsubscribe = service.subscribe_to_updates(lambda: print("Changed"))
        >>> service.shutdown()
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_config: Dict[str, Any],
    ) -> None:
        """Initialize disabled entity service.

        Args:
            hass: Home Assistant instance
            config_entry: Config entry for this integration
            device_config: Full device configuration (entities + registers)
        """
        self._hass = hass
        self._config_entry = config_entry
        self._device_config = device_config
        self._register_definitions = device_config.get("registers", {})

        # Build entity_id → register name mapping from entity configurations
        self._entity_to_register_map = self._build_entity_register_map()

        # Event subscription
        self._event_unsub = None
        self._change_callbacks: list[Callable[[], None]] = []

        # Diagnostic logging
        _LOGGER.info(
            "DisabledEntityService initialized with %d entities and %d register definitions",
            len(self._entity_to_register_map),
            len(self._register_definitions) if self._register_definitions else 0
        )

        # Show sample register definitions to verify they're loaded
        if self._register_definitions:
            sample_register_names = list(self._register_definitions.keys())[:10]
            _LOGGER.info("📚 Sample register names in definitions: %s", sample_register_names)
        if self._entity_to_register_map:
            # Show sample entity_ids to help debug mapping issues
            sample_entity_ids = list(self._entity_to_register_map.keys())[:10]
            _LOGGER.info("Sample entity_ids in map: %s", sample_entity_ids)

            # Show sample register names (entities WITH registers)
            sample_with_registers = {k: v for k, v in list(self._entity_to_register_map.items())[:10] if v is not None}
            if sample_with_registers:
                _LOGGER.info("📋 Sample entity→register mappings: %s", sample_with_registers)

    def get_disabled_addresses(self) -> Set[int]:
        """Get set of register addresses for currently disabled entities.

        Queries the entity registry, filters for disabled entities belonging
        to this config entry, and maps them to register addresses.

        Returns:
            Set of register addresses to exclude from polling

        Example:
            >>> addresses = service.get_disabled_addresses()
            >>> # Returns {0x0100, 0x0200} for disabled entities
        """
        try:
            # Get entity registry
            entity_registry = er.async_get(self._hass)

            # Get all entities for this config entry
            entities = er.async_entries_for_config_entry(
                entity_registry, self._config_entry.entry_id
            )

            _LOGGER.debug(
                "Checking %d total entities for config entry %s",
                len(entities),
                self._config_entry.entry_id
            )

            # Find disabled entities
            disabled_entity_ids = {
                entity.entity_id
                for entity in entities
                if entity.disabled_by is not None
            }

            if not disabled_entity_ids:
                _LOGGER.debug(
                    "No disabled entities found for this config entry. "
                    "If you disabled entities, they may not be detected yet."
                )
                return set()

            _LOGGER.info(
                "Found %d disabled entities: %s",
                len(disabled_entity_ids),
                list(disabled_entity_ids)[:5]  # Show first 5
            )

            # Map entity IDs back to register addresses
            disabled_addresses = set()
            failed_mappings = []

            for entity_id in disabled_entity_ids:
                address = self._map_entity_to_address(entity_id)
                if address is not None:
                    disabled_addresses.add(address)
                else:
                    failed_mappings.append(entity_id)

            if disabled_addresses:
                _LOGGER.info(
                    "✅ Successfully mapped %d/%d disabled entities to register addresses: %s",
                    len(disabled_addresses),
                    len(disabled_entity_ids),
                    [f"0x{addr:04X}" for addr in sorted(disabled_addresses)[:10]]
                )

                if failed_mappings:
                    _LOGGER.info(
                        "ℹ️  %d disabled entities have no registers (calculated/coordinator_data entities): %s",
                        len(failed_mappings),
                        [e.split(".")[-1] for e in failed_mappings[:5]]  # Show entity names only
                    )
            else:
                _LOGGER.info(
                    "ℹ️  Found %d disabled entities but none have register addresses (all are calculated/coordinator_data entities)",
                    len(disabled_entity_ids)
                )

            return disabled_addresses

        except Exception as err:
            _LOGGER.error("Error getting disabled entities: %s", err, exc_info=True)
            return set()

    def subscribe_to_updates(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to entity enable/disable events.

        The callback will be invoked whenever an entity is enabled or disabled.
        Returns an unsubscribe function for cleanup.

        Args:
            callback: Function to call when entity state changes

        Returns:
            Unsubscribe function

        Example:
            >>> def on_change():
            ...     print("Rebuild batches")
            >>> unsub = service.subscribe_to_updates(on_change)
            >>> # Later...
            >>> unsub()
        """
        # Add callback to list
        self._change_callbacks.append(callback)

        # Set up event listener if first subscription
        if self._event_unsub is None:
            self._event_unsub = self._hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._handle_registry_event
            )
            _LOGGER.debug("Subscribed to entity registry events")

        # Return unsubscribe function
        def unsubscribe():
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)

        return unsubscribe

    def shutdown(self) -> None:
        """Clean up resources and unsubscribe from events.

        Example:
            >>> service.shutdown()
        """
        if self._event_unsub:
            self._event_unsub()
            self._event_unsub = None
            _LOGGER.debug("Unsubscribed from entity registry events")

        self._change_callbacks.clear()

    def _build_entity_register_map(self) -> Dict[str, str]:
        """Build mapping from entity_id to register name.

        Scans entity configurations (sensors, numbers, switches, selects, binary_sensors)
        to build a lookup table mapping entity_id → register name.

        Returns:
            Dictionary mapping entity_id to register name

        Example:
            >>> {
            ...     "battery_voltage": "battery_voltage",
            ...     "derate_power": "derate_power",
            ...     "battery_cycle_count": None  # Calculated, no register
            ... }
        """
        entity_register_map = {}

        # Scan all entity types for register references
        for entity_type in ["sensors", "numbers", "switches", "selects", "binary_sensors"]:
            entities = self._device_config.get(entity_type, [])
            if not isinstance(entities, list):
                continue

            for entity_config in entities:
                entity_id = entity_config.get("entity_id")
                register_name = entity_config.get("register")  # May be None for calculated entities

                if entity_id:
                    entity_register_map[entity_id] = register_name

        _LOGGER.info(
            "Built entity→register map with %d entities (%d with registers)",
            len(entity_register_map),
            sum(1 for v in entity_register_map.values() if v is not None)
        )

        # Debug: Show sample mappings
        sample_with_registers = {k: v for k, v in list(entity_register_map.items())[:5] if v is not None}
        if sample_with_registers:
            _LOGGER.debug("Sample entity→register mappings: %s", sample_with_registers)

        return entity_register_map

    def _map_entity_to_address(self, entity_id: str) -> int | None:
        """Map entity ID to register address.

        Uses suffix matching instead of prefix parsing:
        1. Check which entity in our map matches the suffix of the registry entity_id
        2. Look up register name from that entity
        3. Look up address from register definition

        Args:
            entity_id: Full entity ID (e.g., "sensor.e60000231107692658_battery_voltage")

        Returns:
            Register address or None if not found

        Example:
            >>> # Entity ID: sensor.e60000231107692658_derate_power
            >>> # Step 1: Find entity ending with "_derate_power" → "derate_power"
            >>> # Step 2: "derate_power" → register name "derate_power"
            >>> # Step 3: register "derate_power" → address 57880
            >>> address = service._map_entity_to_address("sensor.e60000231107692658_derate_power")
            >>> assert address == 57880
        """
        try:
            # Extract everything after the domain
            # Format: "{domain}.{something}" → "{something}"
            parts = entity_id.split(".")
            if len(parts) != 2:
                _LOGGER.debug("Invalid entity_id format (expected domain.entity_id): %s", entity_id)
                return None

            full_entity_name = parts[1]  # e.g., "e60000231107692658_pv2_voltage"

            # Find which entity in our map matches by checking suffix
            # We try: exact match first, then suffix match (_{entity_name})
            entity_name = None

            # Try exact match first
            if full_entity_name in self._entity_to_register_map:
                entity_name = full_entity_name
                _LOGGER.debug("Exact match: '%s'", entity_name)
            else:
                # Try suffix matching: check if registry ID ends with "_{entity_from_map}"
                for map_entity_name in self._entity_to_register_map.keys():
                    if full_entity_name.endswith(f"_{map_entity_name}"):
                        entity_name = map_entity_name
                        _LOGGER.debug("Suffix match: '%s' → '%s'", full_entity_name, entity_name)
                        break

            if entity_name is None:
                _LOGGER.debug(
                    "No match for '%s'. Available entities: %s",
                    full_entity_name,
                    list(self._entity_to_register_map.keys())[:10]
                )
                return None

            # Step 1: Look up register name from entity configuration
            register_name = self._entity_to_register_map.get(entity_name)
            if register_name is None:
                _LOGGER.debug("Entity '%s' has no register (calculated entity)", entity_name)
                return None

            _LOGGER.debug("Mapped entity '%s' → register '%s'", entity_name, register_name)

            # Step 2: Look up address from register definition
            register_def = self._register_definitions.get(register_name)
            if register_def and "address" in register_def:
                address = register_def["address"]
                _LOGGER.debug(
                    "Mapped: entity '%s' → register '%s' → address 0x%04X",
                    entity_name, register_name, address
                )
                return address
            else:
                _LOGGER.debug(
                    "Register '%s' not found in definitions (entity: %s)",
                    register_name, entity_name
                )
                return None

        except Exception as err:
            _LOGGER.warning("Error mapping entity %s to address: %s", entity_id, err, exc_info=True)
            return None

    async def _handle_registry_event(self, event: Event) -> None:
        """Handle entity registry update events.

        Filters for relevant events (disabled_by changes for our entities)
        and notifies all subscribers.

        Args:
            event: Entity registry update event
        """
        try:
            event_data = event.data

            # Only care about update events
            if event_data.get("action") != "update":
                return

            entity_id = event_data.get("entity_id")
            if not entity_id:
                return

            # Check if it's for our config entry
            entity = er.async_get(self._hass).async_get(entity_id)
            if not entity or entity.config_entry_id != self._config_entry.entry_id:
                return

            # Check if disabled_by changed
            changes = event_data.get("changes", {})
            if "disabled_by" not in changes:
                return

            disabled_by = entity.disabled_by

            _LOGGER.info(
                "Entity %s %s",
                entity_id,
                "disabled" if disabled_by else "enabled",
            )

            # Notify all subscribers
            for callback in self._change_callbacks:
                try:
                    callback()
                except Exception as err:
                    _LOGGER.error("Error in disabled entity callback: %s", err)

        except Exception as err:
            _LOGGER.error("Error handling entity registry event: %s", err)
