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
        register_definitions: Dict[str, Any],
    ) -> None:
        """Initialize disabled entity service.

        Args:
            hass: Home Assistant instance
            config_entry: Config entry for this integration
            register_definitions: Register definitions from device config
        """
        self._hass = hass
        self._config_entry = config_entry
        self._register_definitions = register_definitions

        # Event subscription
        self._event_unsub = None
        self._change_callbacks: list[Callable[[], None]] = []

        # Diagnostic logging
        _LOGGER.info(
            "DisabledEntityService initialized with %d register definitions",
            len(register_definitions) if register_definitions else 0
        )
        if register_definitions:
            sample_registers = list(register_definitions.keys())[:5]
            _LOGGER.debug("Sample register names: %s", sample_registers)

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
                _LOGGER.warning(
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
                    _LOGGER.debug(
                        "Mapped disabled entity %s → register 0x%04X",
                        entity_id,
                        address,
                    )
                else:
                    failed_mappings.append(entity_id)

            if failed_mappings:
                _LOGGER.warning(
                    "Could not map %d disabled entities to registers: %s",
                    len(failed_mappings),
                    failed_mappings[:5]  # Show first 5 failures
                )

            if disabled_addresses:
                _LOGGER.info(
                    "Excluding %d registers from polling: %s",
                    len(disabled_addresses),
                    [f"0x{addr:04X}" for addr in sorted(disabled_addresses)[:10]]
                )
            else:
                _LOGGER.warning(
                    "Found %d disabled entities but none mapped to register addresses",
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

    def _map_entity_to_address(self, entity_id: str) -> int | None:
        """Map entity ID to register address.

        Extracts entity name from ID and looks up corresponding register.

        Args:
            entity_id: Full entity ID (e.g., "sensor.srne_inverter_battery_voltage")

        Returns:
            Register address or None if not found

        Example:
            >>> address = service._map_entity_to_address("sensor.srne_inverter_battery_voltage")
            >>> assert address == 0x0100
        """
        try:
            # Extract entity name from entity_id
            # Format: "sensor.srne_inverter_battery_voltage" → "battery_voltage"
            parts = entity_id.split(".")
            if len(parts) != 2:
                _LOGGER.debug("Invalid entity_id format (expected domain.entity_id): %s", entity_id)
                return None

            entity_name = parts[1]
            _LOGGER.debug("Mapping entity_id %s → extracted name: %s", entity_id, entity_name)

            # Remove common prefixes
            original_name = entity_name
            for prefix in ["srne_inverter_", "srne_"]:
                if entity_name.startswith(prefix):
                    entity_name = entity_name[len(prefix) :]
                    _LOGGER.debug("Removed prefix '%s': %s → %s", prefix, original_name, entity_name)
                    break

            # Look up register in definitions
            _LOGGER.debug("Looking up register name '%s' in %d definitions", entity_name, len(self._register_definitions))
            register_def = self._register_definitions.get(entity_name)
            if register_def and "address" in register_def:
                address = register_def["address"]
                _LOGGER.debug("Found register '%s' → address 0x%04X (%d)", entity_name, address, address)
                return address
            else:
                _LOGGER.debug(
                    "Register '%s' not found in definitions (available: %s)",
                    entity_name,
                    list(self._register_definitions.keys())[:10] if self._register_definitions else []
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
