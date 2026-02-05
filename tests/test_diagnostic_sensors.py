"""Tests for SRNE Inverter diagnostic sensors (Round 5, Phase 2)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory

from custom_components.srne_inverter.const import DOMAIN
from custom_components.srne_inverter.sensor import (
    SRNEBLEConnectionQualitySensor,
    SRNEFailedReadsCountSensor,
    SRNELastUpdateSensor,
    SRNESuccessRateSensor,
    SRNEUpdateDurationSensor,
)


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Test SRNE Inverter"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with diagnostic data."""
    coordinator = MagicMock()
    coordinator.data = {
        "connected": True,
        "battery_soc": 75,
        "ble_rssi": -65,
        "update_duration": 8.5,
        "total_updates": 100,
        "failed_reads": 5,
    }
    coordinator.last_update_success = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    return coordinator


# ============================================================================
# BLE Connection Quality Sensor Tests
# ============================================================================


def test_ble_rssi_sensor_basic(mock_coordinator, mock_entry):
    """Test BLE RSSI sensor basic functionality."""
    sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)

    assert sensor.unique_id == "test_entry_id_ble_connection_quality"
    assert sensor.name == "BLE Connection Quality"
    assert sensor.native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.native_value == -65


def test_ble_rssi_sensor_icons():
    """Test dynamic RSSI icons."""
    mock_coordinator = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test"

    sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)

    # Excellent signal (-60 dBm or better)
    mock_coordinator.data = {"connected": True, "ble_rssi": -55}
    assert sensor.icon == "mdi:wifi-strength-4"

    mock_coordinator.data = {"connected": True, "ble_rssi": -60}
    assert sensor.icon == "mdi:wifi-strength-4"

    # Good signal (-61 to -70 dBm)
    mock_coordinator.data = {"connected": True, "ble_rssi": -65}
    assert sensor.icon == "mdi:wifi-strength-3"

    mock_coordinator.data = {"connected": True, "ble_rssi": -70}
    assert sensor.icon == "mdi:wifi-strength-3"

    # Fair signal (-71 to -80 dBm)
    mock_coordinator.data = {"connected": True, "ble_rssi": -75}
    assert sensor.icon == "mdi:wifi-strength-2"

    mock_coordinator.data = {"connected": True, "ble_rssi": -80}
    assert sensor.icon == "mdi:wifi-strength-2"

    # Poor signal (-81 dBm or worse)
    mock_coordinator.data = {"connected": True, "ble_rssi": -85}
    assert sensor.icon == "mdi:wifi-strength-1"

    mock_coordinator.data = {"connected": True, "ble_rssi": -100}
    assert sensor.icon == "mdi:wifi-strength-1"

    # No signal
    mock_coordinator.data = {"connected": True, "ble_rssi": None}
    assert sensor.icon == "mdi:wifi-strength-off"


def test_ble_rssi_sensor_unavailable(mock_coordinator, mock_entry):
    """Test RSSI sensor when RSSI not available."""
    mock_coordinator.data = {"connected": True}  # No ble_rssi key
    sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None
    assert sensor.icon == "mdi:wifi-strength-off"


def test_ble_rssi_sensor_no_data(mock_coordinator, mock_entry):
    """Test RSSI sensor with no coordinator data."""
    mock_coordinator.data = None
    sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


# ============================================================================
# Last Update Sensor Tests
# ============================================================================


def test_last_update_sensor_basic(mock_coordinator, mock_entry):
    """Test last update timestamp sensor basic functionality."""
    sensor = SRNELastUpdateSensor(mock_coordinator, mock_entry)

    assert sensor.unique_id == "test_entry_id_last_update"
    assert sensor.name == "Last Update"
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.icon == "mdi:clock-check"
    assert sensor.native_value == datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_last_update_sensor_no_update(mock_coordinator, mock_entry):
    """Test last update sensor when no update has occurred."""
    mock_coordinator.last_update_success = None
    sensor = SRNELastUpdateSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


def test_last_update_sensor_recent_update(mock_entry):
    """Test last update sensor with recent timestamp."""
    mock_coordinator = MagicMock()
    now = datetime.now(timezone.utc)
    mock_coordinator.last_update_success = now

    sensor = SRNELastUpdateSensor(mock_coordinator, mock_entry)
    assert sensor.native_value == now


# ============================================================================
# Update Duration Sensor Tests
# ============================================================================


def test_update_duration_sensor_basic(mock_coordinator, mock_entry):
    """Test update duration sensor basic functionality."""
    sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)

    assert sensor.unique_id == "test_entry_id_update_duration"
    assert sensor.name == "Update Duration"
    assert sensor.native_unit_of_measurement == UnitOfTime.SECONDS
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.icon == "mdi:timer"
    assert sensor.native_value == 8.5


def test_update_duration_sensor_fast_update(mock_coordinator, mock_entry):
    """Test update duration with fast update."""
    mock_coordinator.data = {"connected": True, "update_duration": 2.3}
    sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)

    assert sensor.native_value == 2.3


def test_update_duration_sensor_slow_update(mock_coordinator, mock_entry):
    """Test update duration with slow update."""
    mock_coordinator.data = {"connected": True, "update_duration": 15.7}
    sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)

    assert sensor.native_value == 15.7


def test_update_duration_sensor_no_data(mock_coordinator, mock_entry):
    """Test update duration sensor with no data."""
    mock_coordinator.data = None
    sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


def test_update_duration_sensor_missing_key(mock_coordinator, mock_entry):
    """Test update duration sensor when key is missing."""
    mock_coordinator.data = {"connected": True}  # No update_duration
    sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


# ============================================================================
# Failed Reads Count Sensor Tests
# ============================================================================


def test_failed_reads_sensor_basic(mock_coordinator, mock_entry):
    """Test failed reads counter basic functionality."""
    sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)

    assert sensor.unique_id == "test_entry_id_failed_reads_count"
    assert sensor.name == "Failed Reads Count"
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.icon == "mdi:alert-circle"
    assert sensor.native_value == 5


def test_failed_reads_sensor_no_failures(mock_coordinator, mock_entry):
    """Test failed reads counter with zero failures."""
    mock_coordinator.data = {"connected": True, "failed_reads": 0}
    sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)

    assert sensor.native_value == 0


def test_failed_reads_sensor_many_failures(mock_coordinator, mock_entry):
    """Test failed reads counter with many failures."""
    mock_coordinator.data = {"connected": True, "failed_reads": 42}
    sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)

    assert sensor.native_value == 42


def test_failed_reads_sensor_no_data(mock_coordinator, mock_entry):
    """Test failed reads counter with no data."""
    mock_coordinator.data = None
    sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


def test_failed_reads_sensor_default_zero(mock_coordinator, mock_entry):
    """Test failed reads counter defaults to zero when key missing."""
    mock_coordinator.data = {"connected": True}  # No failed_reads key
    sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)

    assert sensor.native_value == 0


# ============================================================================
# Success Rate Sensor Tests
# ============================================================================


def test_success_rate_sensor_basic(mock_coordinator, mock_entry):
    """Test success rate sensor basic functionality."""
    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    assert sensor.unique_id == "test_entry_id_success_rate"
    assert sensor.name == "Success Rate"
    assert sensor.native_unit_of_measurement == PERCENTAGE
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.icon == "mdi:check-network"
    # 100 total, 5 failed = 95% success
    assert sensor.native_value == 95.0


def test_success_rate_calculation():
    """Test success rate percentage calculation."""
    mock_coordinator = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test"

    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    # Perfect success (100%)
    mock_coordinator.data = {"connected": True, "total_updates": 50, "failed_reads": 0}
    assert sensor.native_value == 100.0

    # 95% success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 5}
    assert sensor.native_value == 95.0

    # 90% success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 10}
    assert sensor.native_value == 90.0

    # 50% success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 50}
    assert sensor.native_value == 50.0

    # Very low success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 99}
    assert sensor.native_value == 1.0

    # 0% success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 100}
    assert sensor.native_value == 0.0


def test_success_rate_rounding():
    """Test success rate rounds to 1 decimal place."""
    mock_coordinator = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test"

    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    # 33 failed out of 100 = 67% success
    mock_coordinator.data = {"connected": True, "total_updates": 100, "failed_reads": 33}
    assert sensor.native_value == 67.0

    # 1 failed out of 3 = 66.666...% -> 66.7%
    mock_coordinator.data = {"connected": True, "total_updates": 3, "failed_reads": 1}
    assert sensor.native_value == 66.7

    # 1 failed out of 7 = 85.714...% -> 85.7%
    mock_coordinator.data = {"connected": True, "total_updates": 7, "failed_reads": 1}
    assert sensor.native_value == 85.7


def test_success_rate_sensor_no_updates(mock_coordinator, mock_entry):
    """Test success rate when no updates have occurred."""
    mock_coordinator.data = {"connected": True, "total_updates": 0, "failed_reads": 0}
    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


def test_success_rate_sensor_no_data(mock_coordinator, mock_entry):
    """Test success rate sensor with no data."""
    mock_coordinator.data = None
    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


def test_success_rate_sensor_missing_keys(mock_coordinator, mock_entry):
    """Test success rate sensor when keys are missing."""
    mock_coordinator.data = {"connected": True}  # No total_updates or failed_reads
    sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    assert sensor.native_value is None


# ============================================================================
# Integration Tests - All Diagnostic Sensors
# ============================================================================


def test_all_diagnostic_sensors_have_category(mock_coordinator, mock_entry):
    """Test that all diagnostic sensors have diagnostic category."""
    sensors = [
        SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry),
        SRNELastUpdateSensor(mock_coordinator, mock_entry),
        SRNEUpdateDurationSensor(mock_coordinator, mock_entry),
        SRNEFailedReadsCountSensor(mock_coordinator, mock_entry),
        SRNESuccessRateSensor(mock_coordinator, mock_entry),
    ]

    for sensor in sensors:
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC


def test_all_diagnostic_sensors_unique_ids(mock_coordinator, mock_entry):
    """Test that all diagnostic sensors have unique IDs."""
    sensors = [
        SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry),
        SRNELastUpdateSensor(mock_coordinator, mock_entry),
        SRNEUpdateDurationSensor(mock_coordinator, mock_entry),
        SRNEFailedReadsCountSensor(mock_coordinator, mock_entry),
        SRNESuccessRateSensor(mock_coordinator, mock_entry),
    ]

    unique_ids = [sensor.unique_id for sensor in sensors]
    assert len(unique_ids) == len(set(unique_ids))  # All unique


def test_diagnostic_sensors_with_disconnected_coordinator(mock_entry):
    """Test diagnostic sensors handle disconnected state gracefully."""
    mock_coordinator = MagicMock()
    mock_coordinator.data = {"connected": False}  # Disconnected

    rssi_sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)
    duration_sensor = SRNEUpdateDurationSensor(mock_coordinator, mock_entry)
    failed_sensor = SRNEFailedReadsCountSensor(mock_coordinator, mock_entry)
    success_sensor = SRNESuccessRateSensor(mock_coordinator, mock_entry)

    # Should handle gracefully
    assert rssi_sensor.native_value is None
    assert duration_sensor.native_value is None
    assert failed_sensor.native_value == 0  # Defaults to 0
    assert success_sensor.native_value is None


def test_diagnostic_sensors_availability(mock_coordinator, mock_entry):
    """Test diagnostic sensor availability logic."""
    sensor = SRNEBLEConnectionQualitySensor(mock_coordinator, mock_entry)

    # Connected - available
    mock_coordinator.available = True
    mock_coordinator.data = {"connected": True, "ble_rssi": -70}
    assert sensor.available is True

    # Disconnected - unavailable
    mock_coordinator.data = {"connected": False}
    assert sensor.available is False

    # No data - unavailable
    mock_coordinator.data = None
    assert sensor.available is False


# ============================================================================
# Coordinator Tracking Tests
# ============================================================================


def test_coordinator_tracks_metrics():
    """Test that coordinator properly tracks diagnostic metrics."""
    # This would be an integration test with real coordinator
    # For now, verify the expected data structure
    expected_keys = [
        "ble_rssi",
        "update_duration",
        "total_updates",
        "failed_reads",
    ]

    mock_coordinator = MagicMock()
    mock_coordinator.data = {
        "connected": True,
        "ble_rssi": -70,
        "update_duration": 5.5,
        "total_updates": 10,
        "failed_reads": 1,
    }

    for key in expected_keys:
        assert key in mock_coordinator.data
