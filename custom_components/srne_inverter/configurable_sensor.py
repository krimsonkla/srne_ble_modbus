"""Configurable sensor entity."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from .configurable_base import ConfigurableBaseEntity
from .coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ConfigurableSensor(ConfigurableBaseEntity, SensorEntity):
    """Sensor entity configured from YAML."""

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, config)

        # Set sensor-specific attributes from config
        if device_class := config.get("device_class"):
            try:
                # Try uppercase first (SensorDeviceClass enum expects uppercase)
                self._attr_device_class = SensorDeviceClass(device_class.upper())
            except (ValueError, AttributeError):
                # Fallback to as-is if uppercase doesn't work
                try:
                    self._attr_device_class = SensorDeviceClass(device_class)
                except ValueError:
                    _LOGGER.debug(
                        "Invalid device_class '%s' for sensor %s",
                        device_class,
                        self._attr_name,
                    )

        if state_class := config.get("state_class"):
            try:
                self._attr_state_class = SensorStateClass(state_class.upper())
            except (ValueError, AttributeError):
                try:
                    self._attr_state_class = SensorStateClass(state_class)
                except ValueError:
                    _LOGGER.debug(
                        "Invalid state_class '%s' for sensor %s",
                        state_class,
                        self._attr_name,
                    )

        # Support both 'unit_of_measurement' and 'unit' keys
        self._attr_native_unit_of_measurement = config.get(
            "unit_of_measurement"
        ) or config.get("unit")
        self._attr_suggested_display_precision = config.get(
            "suggested_display_precision"
        )

        # Store source type
        self._source_type = config.get("source_type", "register")

    @property
    def available(self) -> bool:
        """Return if entity is available.

        For calculated sensors, checks if all dependencies are available in coordinator data.
        """
        # Base availability check from parent class
        if not super().available:
            return False

        # For calculated sensors, verify all dependencies are available
        if self._source_type == "calculated":
            depends_on = self._config.get("depends_on", [])
            for dep in depends_on:
                dep_value = self._get_coordinator_value(dep)
                if dep_value is None:
                    _LOGGER.debug(
                        "Calculated sensor %s unavailable: dependency '%s' is None",
                        self._attr_name,
                        dep,
                    )
                    return False

        return True

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""
        if not self.coordinator.data:
            return None

        # Get value based on source type
        if self._source_type == "register":
            return self._get_register_value()
        elif self._source_type == "coordinator_data":
            return self._get_coordinator_data_value()
        elif self._source_type == "calculated":
            return self._get_calculated_value()
        else:
            _LOGGER.error(
                "Unknown source_type '%s' for sensor %s",
                self._source_type,
                self._attr_name,
            )
            return None

    def _get_register_value(self) -> float | int | str | None:
        """Get value from coordinator data (register-based)."""
        data_key = self._config["entity_id"]
        value = self._get_coordinator_value(data_key)

        if value is None:
            return None

        # Apply value mapping if configured (for enum sensors)
        if value_mapping := self._config.get("value_mapping"):
            return value_mapping.get(
                value,
                self._config.get("unknown_value", f"Unknown ({value})"),
            )

        # Apply scaling
        if self._config.get("scaling", 1.0) != 1.0:
            value = self._apply_scaling(value)

        # Apply precision
        if isinstance(value, float):
            value = self._apply_precision(value)

        return value

    def _get_coordinator_data_value(self) -> Any:
        """Get value directly from coordinator data using data_key."""
        data_key = self._config["data_key"]
        value = self._get_coordinator_value(data_key)

        if value is None:
            return None

        # Apply transformations if needed
        if isinstance(value, (int, float)):
            if self._config.get("scaling", 1.0) != 1.0:
                value = self._apply_scaling(value)
            if isinstance(value, float):
                value = self._apply_precision(value)

        return value

    def _get_calculated_value(self) -> float | int | None:
        """Get calculated value using formula."""
        formula = self._config.get("formula")
        if not formula:
            _LOGGER.error(
                "No formula defined for calculated sensor %s", self._attr_name
            )
            return None

        # Build context for formula evaluation
        context = {
            "data": self.coordinator.data,
            "value": None,  # Current value
        }

        # Add dependency values to context
        if depends_on := self._config.get("depends_on"):
            for key in depends_on:
                context[key] = self._get_coordinator_value(key, 0)

        # Evaluate formula
        try:
            # Check if formula is a Jinja2 template
            if "{{" in formula and "}}" in formula:
                result = self._evaluate_template(formula, context)
                # Handle None or "None" string from template
                if result is None:
                    return None
                # Strip whitespace and check for string "None"
                result_str = str(result).strip()
                if result_str == "None" or result_str == "":
                    return None
                # Try to convert to float
                try:
                    return float(result_str)
                except (ValueError, TypeError):
                    # If not a float, return as string (e.g., datetime strings)
                    # Check if it's a timestamp string that should be preserved
                    if 'T' in result_str or '-' in result_str:
                        return result_str
                    _LOGGER.debug(
                        "Could not convert template result to float for %s: %r",
                        self._attr_name,
                        result,
                    )
                    return None
            else:
                # Execute as Python code
                exec_globals = {
                    "data": self.coordinator.data,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                }
                # Add dependencies to globals
                if depends_on := self._config.get("depends_on"):
                    for key in depends_on:
                        exec_globals[key] = self._get_coordinator_value(key, 0)

                exec_locals = {}
                exec(formula, exec_globals, exec_locals)
                return exec_locals.get("result")
        except Exception as err:
            _LOGGER.error(
                "Error evaluating formula for sensor %s: %s",
                self._attr_name,
                err,
            )
            return None

    @property
    def icon(self) -> str | None:
        """Return dynamic icon if template or rules configured."""
        icon_config = self._config.get("icon")

        # Check for dynamic icon with conditional rules
        if isinstance(icon_config, dict) and icon_config.get("dynamic"):
            return self._evaluate_dynamic_icon(icon_config)

        # Check for simple icon template
        if icon_template := self._config.get("icon_template"):
            context = {
                "value": self.native_value,
                "state": self.native_value,
            }
            return self._evaluate_template(icon_template, context)

        # Return static icon
        return self._attr_icon

    def _evaluate_dynamic_icon(self, icon_config: dict) -> str:
        """Evaluate dynamic icon based on conditional rules.

        Args:
            icon_config: Icon configuration with rules

        Returns:
            Icon string based on conditions
        """
        value = self.native_value
        rules = icon_config.get("rules", [])

        # Check each rule in order
        for rule in rules:
            condition = rule.get("condition")

            # Handle None value check
            if condition == "is_none":
                if value is None:
                    return rule.get("icon", "mdi:help")
                continue

            # Skip if value is None for numeric comparisons
            if value is None:
                continue

            # Evaluate condition
            try:
                # Create context for template evaluation
                context = {"value": value}

                # Support both template strings and simple comparisons
                if "{{" in condition and "}}" in condition:
                    # Jinja2 template
                    result = self._evaluate_template(condition, context)
                    if result and str(result).lower() in ("true", "1", "yes"):
                        return rule.get("icon", "mdi:help")
                else:
                    # Simple Python expression
                    if eval(condition, {"value": value, "__builtins__": {}}):
                        return rule.get("icon", "mdi:help")
            except Exception as err:
                _LOGGER.debug(
                    "Error evaluating icon condition '%s' for %s: %s",
                    condition,
                    self._attr_name,
                    err,
                )
                continue

        # Return default icon if no conditions matched
        return icon_config.get("default", "mdi:help")

    @property
    def last_reset(self) -> datetime | None:
        """Return the time when the sensor was last reset.

        Used for TOTAL state class sensors that reset periodically (e.g., daily energy).
        """
        last_reset_config = self._config.get("last_reset")

        if not last_reset_config:
            return None

        if last_reset_config == "midnight_utc":
            # Reset at midnight UTC
            return datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif last_reset_config == "midnight_local":
            # Reset at midnight local time
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif last_reset_config == "midnight_ha":
            # Reset at midnight in Home Assistant's configured timezone
            try:
                from zoneinfo import ZoneInfo

                ha_timezone = self.hass.config.time_zone
                tz = ZoneInfo(ha_timezone)
                return datetime.now(tz).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to get HA timezone for sensor %s: %s, falling back to UTC",
                    self._attr_name,
                    err,
                )
                return datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
        else:
            _LOGGER.debug(
                "Unknown last_reset value '%s' for sensor %s",
                last_reset_config,
                self._attr_name,
            )
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        attributes = {}

        # Process configured attributes
        if attr_config := self._config.get("attributes"):
            for attr_name, attr_template in attr_config.items():
                context = {
                    "value": self.native_value,
                    "value_raw": self._get_coordinator_value(
                        self._config.get("entity_id", "")
                    ),
                    "coordinator": self.coordinator,
                    "data": self.coordinator.data,
                }
                attributes[attr_name] = self._evaluate_template(attr_template, context)

        return attributes
