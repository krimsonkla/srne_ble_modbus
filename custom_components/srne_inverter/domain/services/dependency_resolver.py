"""Service for resolving entity dependencies."""

import logging
from typing import Set, Dict, List

_LOGGER = logging.getLogger(__name__)


class DependencyResolver:
    """Service for resolving entity dependencies.

    Manages dependency graphs for calculated sensors and tracks
    which entities depend on which data keys.

    Example:
        >>> resolver = DependencyResolver()
        >>> config = {"sensors": [
        ...     {"entity_id": "power", "source_type": "calculated",
        ...      "depends_on": ["voltage", "current"]}
        ... ]}
        >>> resolver.build_from_config(config)
        >>> resolver.get_dependents("voltage")
        ['power']
    """

    def __init__(self):
        """Initialize dependency resolver."""
        self._dependency_map: Dict[str, List[str]] = {}  # data_key -> [entity_ids]
        self._reverse_map: Dict[str, Set[str]] = {}  # entity_id -> {data_keys}

    def build_from_config(self, device_config: Dict) -> None:
        """Build dependency maps from device configuration.

        Args:
            device_config: Device configuration with sensors

        Example:
            >>> resolver = DependencyResolver()
            >>> config = {"sensors": [{"entity_id": "power", "depends_on": ["voltage"]}]}
            >>> resolver.build_from_config(config)
        """
        self._dependency_map.clear()
        self._reverse_map.clear()

        for sensor in device_config.get("sensors", []):
            if sensor.get("source_type") != "calculated":
                continue

            entity_id = sensor.get("entity_id")
            depends_on = sensor.get("depends_on", [])

            if not entity_id or not depends_on:
                continue

            # Build forward map (dependency -> dependents)
            for dep_key in depends_on:
                if dep_key not in self._dependency_map:
                    self._dependency_map[dep_key] = []
                self._dependency_map[dep_key].append(entity_id)

            # Build reverse map (entity -> dependencies)
            if entity_id not in self._reverse_map:
                self._reverse_map[entity_id] = set()
            self._reverse_map[entity_id].update(depends_on)

        _LOGGER.debug(
            "Dependency resolver built: %d entities with dependencies",
            len(self._reverse_map),
        )

    def get_dependents(self, data_key: str) -> List[str]:
        """Get entities that depend on this data key.

        Args:
            data_key: Data key to check

        Returns:
            List of entity IDs that depend on this key

        Example:
            >>> resolver.get_dependents("voltage")
            ['power', 'energy']
        """
        return self._dependency_map.get(data_key, [])

    def get_dependencies(self, entity_id: str) -> Set[str]:
        """Get dependencies for an entity.

        Args:
            entity_id: Entity ID to check

        Returns:
            Set of data keys this entity depends on

        Example:
            >>> resolver.get_dependencies("power")
            {'voltage', 'current'}
        """
        return self._reverse_map.get(entity_id, set())

    def get_unavailable_entities(self, available_data: Set[str]) -> List[str]:
        """Get list of entities with missing dependencies.

        Args:
            available_data: Set of currently available data keys

        Returns:
            List of entity IDs that are unavailable

        Example:
            >>> available = {"voltage"}  # Missing 'current'
            >>> resolver.get_unavailable_entities(available)
            ['power']  # Power needs both voltage AND current
        """
        unavailable = []

        for entity_id, deps in self._reverse_map.items():
            if not deps.issubset(available_data):
                unavailable.append(entity_id)

        return unavailable

    def has_dependencies(self, entity_id: str) -> bool:
        """Check if entity has dependencies.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity has dependencies
        """
        return entity_id in self._reverse_map

    def get_dependency_count(self) -> int:
        """Get count of entities with dependencies.

        Returns:
            Number of entities with dependencies
        """
        return len(self._reverse_map)

    def clear(self):
        """Clear all dependency data."""
        self._dependency_map.clear()
        self._reverse_map.clear()
