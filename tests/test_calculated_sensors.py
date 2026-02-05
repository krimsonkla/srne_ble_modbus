"""Tests for Round 5 calculated sensors."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfPower

from custom_components.srne_inverter.sensor import (
    SRNEBatteryPowerSensor,
    SRNEGridDependencySensor,
    SRNESelfSufficiencySensor,
    SRNESystemEfficiencySensor,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test SRNE Inverter"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


# ============================================================================
# SELF-SUFFICIENCY SENSOR TESTS
# ============================================================================


class TestSelfSufficiencySensor:
    """Test self-sufficiency ratio sensor."""

    def test_normal_calculation(self, mock_config_entry):
        """Test normal self-sufficiency calculation (50% coverage)."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 1500,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        # 1500 / 3000 * 100 = 50%
        assert sensor.native_value == 50.0
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.icon == "mdi:solar-panel"

    def test_full_self_sufficiency(self, mock_config_entry):
        """Test 100% self-sufficiency."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        assert sensor.native_value == 100.0

    def test_excess_pv_clamped_to_100(self, mock_config_entry):
        """Test excess PV power is clamped to 100%."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 5000,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        # Should clamp to 100% even though ratio is 166%
        assert sensor.native_value == 100.0

    def test_zero_load_with_pv(self, mock_config_entry):
        """Test zero load with PV generation returns 100%."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 2000,
            "load_power": 0,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        # No load but have PV = 100% self-sufficient
        assert sensor.native_value == 100.0

    def test_zero_load_zero_pv(self, mock_config_entry):
        """Test zero load and zero PV returns 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 0,
            "load_power": 0,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        # No load, no PV = 0%
        assert sensor.native_value == 0.0

    def test_no_pv_power(self, mock_config_entry):
        """Test no PV power returns 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 0,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        assert sensor.native_value == 0.0

    def test_no_data(self, mock_config_entry):
        """Test sensor returns None when no data."""
        coordinator = MagicMock()
        coordinator.data = None

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        assert sensor.native_value is None

    def test_missing_values_default_to_zero(self, mock_config_entry):
        """Test missing values default to zero."""
        coordinator = MagicMock()
        coordinator.data = {
            "connected": True,
        }

        sensor = SRNESelfSufficiencySensor(coordinator, mock_config_entry)

        # Both default to 0, so 0/0 = 0%
        assert sensor.native_value == 0.0


# ============================================================================
# GRID DEPENDENCY SENSOR TESTS
# ============================================================================


class TestGridDependencySensor:
    """Test grid dependency ratio sensor."""

    def test_normal_grid_import(self, mock_config_entry):
        """Test normal grid import calculation."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": 1200,  # Importing
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        # 1200 / 3000 * 100 = 40%
        assert sensor.native_value == 40.0
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.icon == "mdi:transmission-tower"

    def test_full_grid_dependency(self, mock_config_entry):
        """Test 100% grid dependency."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": 3000,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        assert sensor.native_value == 100.0

    def test_grid_export_returns_zero(self, mock_config_entry):
        """Test grid export (negative) returns 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": -1500,  # Exporting
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        # Exporting means no dependency
        assert sensor.native_value == 0.0

    def test_zero_grid_power(self, mock_config_entry):
        """Test zero grid power returns 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": 0,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        assert sensor.native_value == 0.0

    def test_zero_load(self, mock_config_entry):
        """Test zero load returns 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": 1000,
            "load_power": 0,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        # No load = no dependency
        assert sensor.native_value == 0.0

    def test_excessive_grid_clamped(self, mock_config_entry):
        """Test excessive grid power is clamped to 100%."""
        coordinator = MagicMock()
        coordinator.data = {
            "grid_power": 5000,
            "load_power": 3000,
            "connected": True,
        }

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        # Should clamp to 100%
        assert sensor.native_value == 100.0

    def test_no_data(self, mock_config_entry):
        """Test sensor returns None when no data."""
        coordinator = MagicMock()
        coordinator.data = None

        sensor = SRNEGridDependencySensor(coordinator, mock_config_entry)

        assert sensor.native_value is None


# ============================================================================
# BATTERY POWER SENSOR TESTS
# ============================================================================


class TestBatteryPowerSensor:
    """Test battery power sensor."""

    def test_battery_charging(self, mock_config_entry):
        """Test battery charging (positive power)."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 52.0,
            "battery_current": 10.0,  # Positive = charging
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        # 52.0 * 10.0 = 520W
        assert sensor.native_value == 520.0
        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.native_unit_of_measurement == UnitOfPower.WATT
        # Charging icon
        assert sensor.icon == "mdi:battery-charging"

    def test_battery_discharging(self, mock_config_entry):
        """Test battery discharging (negative power)."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 50.0,
            "battery_current": -15.0,  # Negative = discharging
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        # 50.0 * -15.0 = -750W
        assert sensor.native_value == -750.0
        # Discharging icon
        assert sensor.icon == "mdi:battery-arrow-down"

    def test_battery_idle(self, mock_config_entry):
        """Test battery idle state."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 52.0,
            "battery_current": 0.5,  # Near zero
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        # 52.0 * 0.5 = 26W (small value)
        assert sensor.native_value == 26.0
        # Idle icon (between -10 and 10)
        assert sensor.icon == "mdi:battery"

    def test_battery_idle_negative(self, mock_config_entry):
        """Test battery idle with small negative current."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 52.0,
            "battery_current": -0.1,
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        # 52.0 * -0.1 = -5.2W
        assert sensor.native_value == -5.2
        # Idle icon
        assert sensor.icon == "mdi:battery"

    def test_missing_voltage(self, mock_config_entry):
        """Test missing voltage returns None."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_current": 10.0,
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        assert sensor.native_value is None
        assert sensor.icon == "mdi:battery"

    def test_missing_current(self, mock_config_entry):
        """Test missing current returns None."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 52.0,
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        assert sensor.native_value is None
        assert sensor.icon == "mdi:battery"

    def test_no_data(self, mock_config_entry):
        """Test sensor returns None when no data."""
        coordinator = MagicMock()
        coordinator.data = None

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        assert sensor.native_value is None
        assert sensor.icon == "mdi:battery"

    def test_zero_values(self, mock_config_entry):
        """Test zero voltage and current."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 0.0,
            "battery_current": 0.0,
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        assert sensor.native_value == 0.0
        assert sensor.icon == "mdi:battery"

    def test_rounding(self, mock_config_entry):
        """Test power is rounded to 1 decimal place."""
        coordinator = MagicMock()
        coordinator.data = {
            "battery_voltage": 51.234,
            "battery_current": 12.567,
            "connected": True,
        }

        sensor = SRNEBatteryPowerSensor(coordinator, mock_config_entry)

        # 51.234 * 12.567 = 643.857678, rounded to 643.9
        assert sensor.native_value == 643.9


# ============================================================================
# SYSTEM EFFICIENCY SENSOR TESTS
# ============================================================================


class TestSystemEfficiencySensor:
    """Test system efficiency sensor."""

    def test_normal_efficiency(self, mock_config_entry):
        """Test normal system efficiency calculation."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "load_power": 2500,
            "battery_voltage": 50.0,
            "battery_current": 5.0,  # Charging 250W
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency = (2500 + 250) / 3000 * 100 = 91.7%
        assert sensor.native_value == 91.7
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.icon == "mdi:gauge"

    def test_perfect_efficiency(self, mock_config_entry):
        """Test 100% efficiency (all PV goes to load/battery)."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "load_power": 2000,
            "battery_voltage": 50.0,
            "battery_current": 20.0,  # Charging 1000W
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency = (2000 + 1000) / 3000 * 100 = 100%
        assert sensor.native_value == 100.0

    def test_no_battery_charging(self, mock_config_entry):
        """Test efficiency with no battery charging."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "load_power": 2700,
            "battery_voltage": 50.0,
            "battery_current": 0.0,  # No charging
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency = (2700 + 0) / 3000 * 100 = 90%
        assert sensor.native_value == 90.0

    def test_battery_discharging_ignored(self, mock_config_entry):
        """Test battery discharging is ignored in efficiency calculation."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 1000,
            "load_power": 800,
            "battery_voltage": 50.0,
            "battery_current": -10.0,  # Discharging, should be ignored
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency = (800 + 0) / 1000 * 100 = 80%
        # Discharging current is negative, max(current, 0) = 0
        assert sensor.native_value == 80.0

    def test_no_pv_power(self, mock_config_entry):
        """Test no PV power returns None."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 0,
            "load_power": 2000,
            "battery_voltage": 50.0,
            "battery_current": 10.0,
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Can't calculate efficiency without PV
        assert sensor.native_value is None

    def test_efficiency_over_100_clamped(self, mock_config_entry):
        """Test efficiency over 100% is clamped."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 2000,
            "load_power": 1800,
            "battery_voltage": 50.0,
            "battery_current": 10.0,  # Charging 500W
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency = (1800 + 500) / 2000 * 100 = 115%, clamped to 100%
        assert sensor.native_value == 100.0

    def test_efficiency_below_zero_clamped(self, mock_config_entry):
        """Test negative efficiency is clamped to 0%."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 1000,
            "load_power": -100,  # Unusual but possible error state
            "battery_voltage": 50.0,
            "battery_current": 0.0,
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Efficiency would be negative, clamped to 0%
        assert sensor.native_value == 0.0

    def test_missing_values_default_to_zero(self, mock_config_entry):
        """Test missing values default to zero."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "connected": True,
        }

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # Missing values default to 0
        # Efficiency = (0 + 0) / 3000 * 100 = 0%
        assert sensor.native_value == 0.0

    def test_no_data(self, mock_config_entry):
        """Test sensor returns None when no data."""
        coordinator = MagicMock()
        coordinator.data = None

        sensor = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        assert sensor.native_value is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestCalculatedSensorsIntegration:
    """Test calculated sensors together."""

    def test_all_sensors_unique_ids(self, mock_config_entry):
        """Test all calculated sensors have unique IDs."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 3000,
            "grid_power": 500,
            "load_power": 3000,
            "battery_voltage": 50.0,
            "battery_current": 10.0,
            "connected": True,
        }

        sensors = [
            SRNESelfSufficiencySensor(coordinator, mock_config_entry),
            SRNEGridDependencySensor(coordinator, mock_config_entry),
            SRNEBatteryPowerSensor(coordinator, mock_config_entry),
            SRNESystemEfficiencySensor(coordinator, mock_config_entry),
        ]

        unique_ids = [s.unique_id for s in sensors]
        assert len(unique_ids) == len(set(unique_ids))  # All unique

    def test_realistic_scenario_daytime(self, mock_config_entry):
        """Test realistic daytime scenario with high PV."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 4000,
            "grid_power": -500,  # Exporting
            "load_power": 2500,
            "battery_voltage": 52.0,
            "battery_current": 20.0,  # Charging
            "connected": True,
        }

        self_suff = SRNESelfSufficiencySensor(coordinator, mock_config_entry)
        grid_dep = SRNEGridDependencySensor(coordinator, mock_config_entry)
        battery_power = SRNEBatteryPowerSensor(coordinator, mock_config_entry)
        efficiency = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # High self-sufficiency (clamped to 100%)
        assert self_suff.native_value == 100.0
        # No grid dependency (exporting)
        assert grid_dep.native_value == 0.0
        # Battery charging
        assert battery_power.native_value == 1040.0
        assert battery_power.icon == "mdi:battery-charging"
        # High efficiency
        assert efficiency.native_value == 88.5  # (2500 + 1040) / 4000

    def test_realistic_scenario_nighttime(self, mock_config_entry):
        """Test realistic nighttime scenario with no PV."""
        coordinator = MagicMock()
        coordinator.data = {
            "pv_power": 0,
            "grid_power": 1500,  # Importing
            "load_power": 3000,
            "battery_voltage": 48.0,
            "battery_current": -30.0,  # Discharging
            "connected": True,
        }

        self_suff = SRNESelfSufficiencySensor(coordinator, mock_config_entry)
        grid_dep = SRNEGridDependencySensor(coordinator, mock_config_entry)
        battery_power = SRNEBatteryPowerSensor(coordinator, mock_config_entry)
        efficiency = SRNESystemEfficiencySensor(coordinator, mock_config_entry)

        # No self-sufficiency
        assert self_suff.native_value == 0.0
        # 50% grid dependency
        assert grid_dep.native_value == 50.0
        # Battery discharging
        assert battery_power.native_value == -1440.0
        assert battery_power.icon == "mdi:battery-arrow-down"
        # No efficiency (no PV)
        assert efficiency.native_value is None
