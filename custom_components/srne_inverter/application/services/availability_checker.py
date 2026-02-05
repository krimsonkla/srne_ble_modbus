"""Service for checking entity availability."""

from typing import Optional, List


class AvailabilityChecker:
    """Service for checking entity availability based on various conditions.

    This service centralizes availability logic that was previously
    scattered across entity classes.
    """

    def __init__(self, coordinator):
        """Initialize availability checker.

        Args:
            coordinator: Data update coordinator
        """
        self._coordinator = coordinator

    def is_available(
        self,
        entity_id: str,
        register_name: Optional[str] = None,
        source_type: str = "register",
        depends_on: Optional[List[str]] = None,
    ) -> bool:
        """Check if entity should be available.

        Args:
            entity_id: Entity ID to check
            register_name: Associated register name (if any)
            source_type: Entity source type (register, calculated, etc.)
            depends_on: List of dependencies (for calculated)

        Returns:
            True if entity should be available
        """
        # Basic checks
        if not self._coordinator.data:
            return False

        if not self._coordinator.data.get("connected", False):
            return False

        # Check entity-specific unavailability
        if hasattr(self._coordinator, "is_entity_unavailable"):
            if self._coordinator.is_entity_unavailable(entity_id):
                return False

        # Check register-based unavailability
        if register_name:
            if hasattr(self._coordinator, "is_register_failed"):
                if self._coordinator.is_register_failed(register_name):
                    return False

        # Check calculated sensor dependencies
        if source_type == "calculated" and depends_on:
            for dep in depends_on:
                if self._coordinator.data.get(dep) is None:
                    return False

        return True

    def check_dependencies(self, depends_on: List[str]) -> bool:
        """Check if all dependencies are available.

        Args:
            depends_on: List of data keys to check

        Returns:
            True if all dependencies available
        """
        if not depends_on:
            return True

        if not self._coordinator.data:
            return False

        return all(self._coordinator.data.get(dep) is not None for dep in depends_on)
