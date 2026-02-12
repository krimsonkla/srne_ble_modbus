"""Diagnostic sensors for learned timeout monitoring.

Provides transparency into the adaptive timing system by exposing:
- Current learned timeout values
- Sample counts used for learning
- Learning status and statistics
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from ..coordinator import SRNEDataUpdateCoordinator
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LearnedTimeoutSensor(SensorEntity):
    """Diagnostic sensor for learned timeout values.

    Exposes the current learned timeout value for a specific operation,
    allowing users to monitor the adaptive timing system's behavior.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        operation: str,
        name_suffix: str,
    ) -> None:
        """Initialize learned timeout sensor.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            operation: Operation type ('ble_send' or 'modbus_read')
            name_suffix: Human-readable name suffix
        """
        self._coordinator = coordinator
        self._entry = entry
        self._operation = operation

        # Entity attributes
        device_name = entry.data.get("name", "SRNE Inverter")
        self._attr_name = f"{device_name} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_learned_timeout_{operation}"

        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def native_value(self) -> float | None:
        """Return learned timeout value in seconds.

        Returns the learned value if available, otherwise returns the
        default constant value currently being used.
        """
        # Check if coordinator has learned timeouts
        if not hasattr(self._coordinator, "_learned_timeouts"):
            return self._get_default_timeout()

        # Get learned value
        learned_timeouts = self._coordinator._learned_timeouts
        learned_value = learned_timeouts.get(self._operation)

        # Return learned value if exists, otherwise default
        if learned_value is not None:
            return learned_value

        return self._get_default_timeout()

    def _get_default_timeout(self) -> float:
        """Get the default timeout value for this operation."""
        from ..const import BLE_COMMAND_TIMEOUT, MODBUS_RESPONSE_TIMEOUT

        defaults = {
            "ble_send": BLE_COMMAND_TIMEOUT,
            "modbus_read": MODBUS_RESPONSE_TIMEOUT,
        }
        return defaults.get(self._operation, 1.0)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Add timeout learner statistics if available
        if hasattr(self._coordinator, "_timeout_learner") and self._coordinator._timeout_learner:
            learned = self._coordinator._timeout_learner.calculate_timeout(self._operation)
            if learned:
                attrs["based_on_samples"] = learned.based_on_samples
                attrs["p95_measured_s"] = learned.p95_measured
                attrs["default_timeout_s"] = learned.default_timeout

                # Calculate change percentage
                change_percent = (
                    (learned.timeout - learned.default_timeout) / learned.default_timeout
                ) * 100
                attrs["change_from_default_pct"] = round(change_percent, 1)

        # Add timing collector statistics if available
        if hasattr(self._coordinator, "_timing_collector") and self._coordinator._timing_collector:
            stats = self._coordinator._timing_collector.get_statistics(self._operation)
            if stats:
                attrs["mean_ms"] = stats.mean_ms
                attrs["median_ms"] = stats.median_ms
                attrs["p99_ms"] = stats.p99_ms
                attrs["success_rate"] = stats.success_rate

        return attrs


class LearnedTimeoutSampleCountSensor(SensorEntity):
    """Diagnostic sensor for timing sample count.

    Shows how many timing measurements have been collected for learning.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SRNEDataUpdateCoordinator,
        entry: ConfigEntry,
        operation: str,
        name_suffix: str,
    ) -> None:
        """Initialize sample count sensor.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
            operation: Operation type ('ble_send' or 'modbus_read')
            name_suffix: Human-readable name suffix
        """
        self._coordinator = coordinator
        self._entry = entry
        self._operation = operation

        # Entity attributes
        device_name = entry.data.get("name", "SRNE Inverter")
        self._attr_name = f"{device_name} {name_suffix}"
        self._attr_unique_id = f"{entry.entry_id}_timing_samples_{operation}"

        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
        }

    @property
    def native_value(self) -> int | None:
        """Return number of timing samples collected."""
        if not hasattr(self._coordinator, "_timing_collector"):
            return None

        if not self._coordinator._timing_collector:
            return None

        return self._coordinator._timing_collector.get_sample_count(self._operation)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        # Add learning status
        if hasattr(self._coordinator, "_timing_collector") and self._coordinator._timing_collector:
            sample_count = self._coordinator._timing_collector.get_sample_count(self._operation)
            from ..const import TIMING_MIN_SAMPLES

            if sample_count >= TIMING_MIN_SAMPLES:
                attrs["learning_status"] = "active"
            elif sample_count > 0:
                attrs["learning_status"] = "collecting"
                attrs["samples_needed"] = TIMING_MIN_SAMPLES - sample_count
            else:
                attrs["learning_status"] = "inactive"

        return attrs


def create_learned_timeout_sensors(
    coordinator: SRNEDataUpdateCoordinator,
    entry: ConfigEntry,
) -> list[SensorEntity]:
    """Create all learned timeout diagnostic sensors.

    Args:
        coordinator: Data update coordinator
        entry: Config entry

    Returns:
        List of sensor entities for learned timeouts
    """
    sensors = []

    # Only create sensors if timing infrastructure is present
    if not hasattr(coordinator, "_timing_collector") or not coordinator._timing_collector:
        _LOGGER.debug("Timing collector not available, skipping diagnostic sensors")
        return sensors

    # BLE Send timeout sensors
    sensors.append(
        LearnedTimeoutSensor(
            coordinator,
            entry,
            "ble_send",
            "BLE Send Timeout (Learned)",
        )
    )
    sensors.append(
        LearnedTimeoutSampleCountSensor(
            coordinator,
            entry,
            "ble_send",
            "BLE Send Samples",
        )
    )

    _LOGGER.info("Created %d learned timeout diagnostic sensors", len(sensors))
    return sensors
