"""Tests for the SRNE Inverter sensor platform."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant

from custom_components.srne_inverter.sensor import (
    SRNEBatterySOCSensor,
    async_setup_entry,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test SRNE Inverter"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    from datetime import datetime
    from unittest.mock import PropertyMock

    coordinator = MagicMock()
    coordinator.data = {
        "battery_soc": 85,
        "connected": True,
    }
    coordinator.last_update_success_time = datetime.fromisoformat("2024-02-03T12:00:00")

    # Use PropertyMock to ensure last_update_success returns actual datetime
    type(coordinator).last_update_success = PropertyMock(
        return_value=datetime.fromisoformat("2024-02-03T12:00:00")
    )

    return coordinator


class TestSensorPlatform:
    """Test the sensor platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test sensor platform setup."""
        from custom_components.srne_inverter.const import DOMAIN

        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 36  # 1 from Round 1, 7 from Round 3, 15 from Round 4, 9 from Round 5, 4 new split sensors
        assert isinstance(entities[0], SRNEBatterySOCSensor)


class TestSRNEBatterySOCSensor:
    """Test the battery SOC sensor."""

    def test_sensor_initialization(self, mock_coordinator, mock_config_entry):
        """Test sensor initialization."""
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        assert sensor.unique_id == "test_entry_battery_soc"
        assert sensor.name == "Battery SOC"
        assert sensor.native_unit_of_measurement == PERCENTAGE
        assert sensor.device_class == "battery"

    def test_sensor_device_info(self, mock_coordinator, mock_config_entry):
        """Test sensor device info."""
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        device_info = sensor.device_info
        assert device_info is not None
        assert ("srne_inverter", "test_entry") in device_info["identifiers"]
        assert device_info["name"] == "Test SRNE Inverter"
        assert device_info["manufacturer"] == "SRNE"

    def test_native_value(self, mock_coordinator, mock_config_entry):
        """Test sensor native value."""
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        assert sensor.native_value == 85

    def test_native_value_no_data(self, mock_coordinator, mock_config_entry):
        """Test sensor native value when no data."""
        mock_coordinator.data = None
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        assert sensor.native_value is None

    def test_available_when_connected(self, mock_coordinator, mock_config_entry):
        """Test sensor availability when connected."""
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        with patch.object(sensor, "coordinator", mock_coordinator):
            # Mock CoordinatorEntity.available
            with patch(
                "homeassistant.helpers.update_coordinator.CoordinatorEntity.available",
                new_callable=lambda: property(lambda self: True),
            ):
                assert sensor.available is True

    def test_available_when_disconnected(self, mock_coordinator, mock_config_entry):
        """Test sensor availability when disconnected."""
        mock_coordinator.data = {"connected": False}
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        with patch.object(sensor, "coordinator", mock_coordinator):
            with patch(
                "homeassistant.helpers.update_coordinator.CoordinatorEntity.available",
                new_callable=lambda: property(lambda self: True),
            ):
                assert sensor.available is False

    def test_extra_state_attributes(self, mock_coordinator, mock_config_entry):
        """Test sensor extra state attributes."""
        from datetime import datetime

        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        attrs = sensor.extra_state_attributes
        assert "last_update" in attrs
        # Compare as datetime object
        expected = datetime.fromisoformat("2024-02-03T12:00:00")
        assert attrs["last_update"] == expected

    def test_extra_state_attributes_no_data(self, mock_coordinator, mock_config_entry):
        """Test sensor extra state attributes when no data."""
        mock_coordinator.data = None
        sensor = SRNEBatterySOCSensor(mock_coordinator, mock_config_entry)

        attrs = sensor.extra_state_attributes
        assert attrs == {}


@pytest.fixture
def round3_coordinator():
    """Create coordinator with Round 3 data."""
    from datetime import datetime
    from unittest.mock import PropertyMock

    coordinator = MagicMock()
    coordinator.data = {
        "battery_soc": 75,
        "battery_voltage": 52.4,
        "battery_current": 12.5,  # Charging
        "pv_power": 3500,
        "grid_power": -1200,  # Exporting
        "load_power": 2300,
        "inverter_temperature": 45.2,
        "battery_temperature": 28.5,
        "machine_state": 5,
        "energy_priority": 0,
        "connected": True,
    }
    coordinator.last_update_success_time = datetime.fromisoformat("2024-02-03T12:00:00")

    # Use PropertyMock to ensure last_update_success returns actual datetime
    type(coordinator).last_update_success = PropertyMock(
        return_value=datetime.fromisoformat("2024-02-03T12:00:00")
    )

    return coordinator


@pytest.fixture
def round3_coordinator_discharging():
    """Create coordinator with battery discharging."""
    from datetime import datetime
    from unittest.mock import PropertyMock

    coordinator = MagicMock()
    coordinator.data = {
        "battery_soc": 65,
        "battery_voltage": 51.2,
        "battery_current": -8.3,  # Discharging
        "pv_power": 500,
        "grid_power": 1800,  # Importing
        "load_power": 2300,
        "inverter_temperature": 38.5,
        "battery_temperature": 26.1,
        "machine_state": 5,
        "energy_priority": 2,
        "connected": True,
    }

    # Use PropertyMock to ensure last_update_success returns actual datetime
    type(coordinator).last_update_success = PropertyMock(
        return_value=datetime.fromisoformat("2024-02-03T12:00:00")
    )

    return coordinator


class TestRound3PowerSensors:
    """Test Round 3 power monitoring sensors."""

    def test_pv_power_sensor(self, round3_coordinator, mock_config_entry):
        """Test PV Power sensor."""
        from custom_components.srne_inverter.sensor import SRNEPVPowerSensor
        from homeassistant.components.sensor import SensorDeviceClass
        from homeassistant.const import UnitOfPower

        sensor = SRNEPVPowerSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 3500
        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.native_unit_of_measurement == UnitOfPower.WATT
        assert sensor.icon == "mdi:solar-power"
        assert sensor.unique_id == "test_entry_pv_power"

    def test_grid_power_sensor_exporting(self, round3_coordinator, mock_config_entry):
        """Test Grid Power sensor when exporting."""
        from custom_components.srne_inverter.sensor import SRNEGridPowerSensor

        sensor = SRNEGridPowerSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == -1200
        assert sensor.icon == "mdi:transmission-tower"
        attrs = sensor.extra_state_attributes
        assert attrs["direction"] == "exporting"

    def test_grid_power_sensor_importing(
        self, round3_coordinator_discharging, mock_config_entry
    ):
        """Test Grid Power sensor when importing."""
        from custom_components.srne_inverter.sensor import SRNEGridPowerSensor

        sensor = SRNEGridPowerSensor(round3_coordinator_discharging, mock_config_entry)

        assert sensor.native_value == 1800
        attrs = sensor.extra_state_attributes
        assert attrs["direction"] == "importing"

    def test_grid_power_sensor_balanced(self, round3_coordinator, mock_config_entry):
        """Test Grid Power sensor when balanced."""
        from custom_components.srne_inverter.sensor import SRNEGridPowerSensor

        round3_coordinator.data["grid_power"] = 0
        sensor = SRNEGridPowerSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 0
        attrs = sensor.extra_state_attributes
        assert attrs["direction"] == "balanced"

    def test_load_power_sensor(self, round3_coordinator, mock_config_entry):
        """Test Load Power sensor."""
        from custom_components.srne_inverter.sensor import SRNELoadPowerSensor

        sensor = SRNELoadPowerSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 2300
        assert sensor.icon == "mdi:home-lightning-bolt"


class TestRound3BatterySensors:
    """Test Round 3 battery detail sensors."""

    def test_battery_voltage_sensor(self, round3_coordinator, mock_config_entry):
        """Test Battery Voltage sensor."""
        from custom_components.srne_inverter.sensor import SRNEBatteryVoltageSensor
        from homeassistant.components.sensor import SensorDeviceClass
        from homeassistant.const import UnitOfElectricPotential

        sensor = SRNEBatteryVoltageSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 52.4
        assert sensor.device_class == SensorDeviceClass.VOLTAGE
        assert sensor.native_unit_of_measurement == UnitOfElectricPotential.VOLT

    def test_battery_current_sensor_charging(
        self, round3_coordinator, mock_config_entry
    ):
        """Test Battery Current sensor when charging."""
        from custom_components.srne_inverter.sensor import SRNEBatteryCurrentSensor
        from homeassistant.components.sensor import SensorDeviceClass
        from homeassistant.const import UnitOfElectricCurrent

        sensor = SRNEBatteryCurrentSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 12.5
        assert sensor.device_class == SensorDeviceClass.CURRENT
        assert sensor.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE
        attrs = sensor.extra_state_attributes
        assert attrs["state"] == "charging"

    def test_battery_current_sensor_discharging(
        self, round3_coordinator_discharging, mock_config_entry
    ):
        """Test Battery Current sensor when discharging."""
        from custom_components.srne_inverter.sensor import SRNEBatteryCurrentSensor

        sensor = SRNEBatteryCurrentSensor(
            round3_coordinator_discharging, mock_config_entry
        )

        assert sensor.native_value == -8.3
        attrs = sensor.extra_state_attributes
        assert attrs["state"] == "discharging"

    def test_battery_current_sensor_idle(self, round3_coordinator, mock_config_entry):
        """Test Battery Current sensor when idle."""
        from custom_components.srne_inverter.sensor import SRNEBatteryCurrentSensor

        round3_coordinator.data["battery_current"] = 0
        sensor = SRNEBatteryCurrentSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 0
        attrs = sensor.extra_state_attributes
        assert attrs["state"] == "idle"


class TestRound3TemperatureSensors:
    """Test Round 3 temperature monitoring sensors."""

    def test_inverter_temperature_sensor(self, round3_coordinator, mock_config_entry):
        """Test Inverter Temperature sensor."""
        from custom_components.srne_inverter.sensor import SRNEInverterTemperatureSensor
        from homeassistant.components.sensor import SensorDeviceClass
        from homeassistant.const import UnitOfTemperature

        sensor = SRNEInverterTemperatureSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 45.2
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
        assert sensor.icon == "mdi:thermometer"

    def test_battery_temperature_sensor(self, round3_coordinator, mock_config_entry):
        """Test Battery Temperature sensor."""
        from custom_components.srne_inverter.sensor import SRNEBatteryTemperatureSensor
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = SRNEBatteryTemperatureSensor(round3_coordinator, mock_config_entry)

        assert sensor.native_value == 28.5
        assert sensor.device_class == SensorDeviceClass.TEMPERATURE
        assert sensor.icon == "mdi:thermometer-lines"


class TestRound3SensorPlatform:
    """Test Round 3 sensor platform setup."""

    @pytest.mark.asyncio
    async def test_all_sensors_registered(
        self, mock_hass, mock_config_entry, round3_coordinator
    ):
        """Test that all 8 sensors are registered."""
        from custom_components.srne_inverter.const import DOMAIN

        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: round3_coordinator}}
        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]

        # Should have 36 sensors (1 from Round 1, 7 from Round 3, 15 from Round 4, 9 from Round 5, 4 new split sensors)
        assert len(entities) == 36

        # Verify sensor types
        from custom_components.srne_inverter.sensor import (
            SRNEBatterySOCSensor,
            SRNEPVPowerSensor,
            SRNEGridPowerSensor,
            SRNELoadPowerSensor,
            SRNEBatteryVoltageSensor,
            SRNEBatteryCurrentSensor,
            SRNEInverterTemperatureSensor,
            SRNEBatteryTemperatureSensor,
        )

        assert isinstance(entities[0], SRNEBatterySOCSensor)
        assert isinstance(entities[1], SRNEPVPowerSensor)
        assert isinstance(entities[2], SRNEGridPowerSensor)
        assert isinstance(entities[3], SRNELoadPowerSensor)
        assert isinstance(entities[6], SRNEBatteryVoltageSensor)
        assert isinstance(entities[7], SRNEBatteryCurrentSensor)
        assert isinstance(entities[8], SRNEInverterTemperatureSensor)
        assert isinstance(entities[9], SRNEBatteryTemperatureSensor)


@pytest.fixture
def energy_dashboard_coordinator():
    """Create coordinator with energy dashboard test data."""
    from datetime import datetime
    from unittest.mock import PropertyMock

    coordinator = MagicMock()
    coordinator.data = {
        "battery_soc": 80,
        "battery_voltage": 52.0,
        "battery_current": 10.0,  # Charging
        "pv_power": 2000,
        "grid_power": 500,  # Importing
        "load_power": 2500,
        "pv_energy_today": 15.5,
        "load_energy_today": 12.3,
        "pv_energy_total": 1500.0,
        "load_energy_total": 1200.0,
        "battery_charge_ah_today": 50.0,
        "battery_discharge_ah_today": 30.0,
        "connected": True,
    }

    type(coordinator).last_update_success = PropertyMock(
        return_value=datetime.fromisoformat("2024-02-03T12:00:00")
    )

    return coordinator


class TestEnergyDashboardIntegration:
    """Test Energy Dashboard integration features."""

    def test_pv_energy_today_has_last_reset(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test PV Energy Today has last_reset property."""
        from custom_components.srne_inverter.sensor import SRNEPVEnergyTodaySensor
        from homeassistant.components.sensor import SensorStateClass
        from datetime import datetime, timezone

        sensor = SRNEPVEnergyTodaySensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.native_value == 15.5

        # Check last_reset returns midnight UTC
        last_reset = sensor.last_reset
        assert last_reset is not None
        assert last_reset.hour == 0
        assert last_reset.minute == 0
        assert last_reset.second == 0
        assert last_reset.microsecond == 0
        assert last_reset.tzinfo == timezone.utc

    def test_load_energy_today_has_last_reset(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Load Energy Today has last_reset property."""
        from custom_components.srne_inverter.sensor import SRNELoadEnergyTodaySensor
        from homeassistant.components.sensor import SensorStateClass
        from datetime import datetime, timezone

        sensor = SRNELoadEnergyTodaySensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.native_value == 12.3

        # Check last_reset returns midnight UTC
        last_reset = sensor.last_reset
        assert last_reset is not None
        assert last_reset.hour == 0
        assert last_reset.minute == 0

    def test_battery_charge_ah_today_has_last_reset(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Charge AH Today has last_reset property."""
        from custom_components.srne_inverter.sensor import SRNEBatteryChargeAHTodaySensor
        from homeassistant.components.sensor import SensorStateClass

        sensor = SRNEBatteryChargeAHTodaySensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.native_value == 50.0
        assert sensor.last_reset is not None

    def test_battery_discharge_ah_today_has_last_reset(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Discharge AH Today has last_reset property."""
        from custom_components.srne_inverter.sensor import SRNEBatteryDischargeAHTodaySensor
        from homeassistant.components.sensor import SensorStateClass

        sensor = SRNEBatteryDischargeAHTodaySensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.state_class == SensorStateClass.TOTAL_INCREASING
        assert sensor.native_value == 30.0
        assert sensor.last_reset is not None

    def test_grid_import_power_sensor(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Grid Import Power sensor only returns positive values."""
        from custom_components.srne_inverter.sensor import SRNEGridImportPowerSensor
        from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
        from homeassistant.const import UnitOfPower

        sensor = SRNEGridImportPowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.native_unit_of_measurement == UnitOfPower.WATT
        assert sensor.native_value == 500  # Positive grid_power = importing

    def test_grid_import_power_sensor_when_exporting(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Grid Import Power sensor returns 0 when exporting."""
        from custom_components.srne_inverter.sensor import SRNEGridImportPowerSensor

        energy_dashboard_coordinator.data["grid_power"] = -800  # Exporting
        sensor = SRNEGridImportPowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.native_value == 0  # No import when exporting

    def test_grid_export_power_sensor(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Grid Export Power sensor converts negative to positive."""
        from custom_components.srne_inverter.sensor import SRNEGridExportPowerSensor
        from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

        energy_dashboard_coordinator.data["grid_power"] = -800  # Exporting
        sensor = SRNEGridExportPowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.native_value == 800  # Negative converted to positive

    def test_grid_export_power_sensor_when_importing(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Grid Export Power sensor returns 0 when importing."""
        from custom_components.srne_inverter.sensor import SRNEGridExportPowerSensor

        sensor = SRNEGridExportPowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.native_value == 0  # No export when importing

    def test_grid_split_sensors_sum_to_original(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test grid import/export split sensors sum correctly."""
        from custom_components.srne_inverter.sensor import (
            SRNEGridPowerSensor,
            SRNEGridImportPowerSensor,
            SRNEGridExportPowerSensor,
        )

        # Test with importing
        grid_sensor = SRNEGridPowerSensor(energy_dashboard_coordinator, mock_config_entry)
        import_sensor = SRNEGridImportPowerSensor(energy_dashboard_coordinator, mock_config_entry)
        export_sensor = SRNEGridExportPowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert grid_sensor.native_value == 500
        assert import_sensor.native_value == 500
        assert export_sensor.native_value == 0

        # Test with exporting
        energy_dashboard_coordinator.data["grid_power"] = -800
        assert grid_sensor.native_value == -800
        assert import_sensor.native_value == 0
        assert export_sensor.native_value == 800

    def test_battery_charge_power_sensor(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Charge Power sensor only returns positive values."""
        from custom_components.srne_inverter.sensor import SRNEBatteryChargePowerSensor
        from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

        sensor = SRNEBatteryChargePowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        # 52.0V * 10.0A = 520W
        assert sensor.native_value == 520.0

    def test_battery_charge_power_sensor_when_discharging(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Charge Power sensor returns 0 when discharging."""
        from custom_components.srne_inverter.sensor import SRNEBatteryChargePowerSensor

        energy_dashboard_coordinator.data["battery_current"] = -10.0  # Discharging
        sensor = SRNEBatteryChargePowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.native_value == 0  # No charge when discharging

    def test_battery_discharge_power_sensor(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Discharge Power sensor converts negative to positive."""
        from custom_components.srne_inverter.sensor import SRNEBatteryDischargePowerSensor
        from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

        energy_dashboard_coordinator.data["battery_current"] = -10.0  # Discharging
        sensor = SRNEBatteryDischargePowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.device_class == SensorDeviceClass.POWER
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        # 52.0V * -10.0A = -520W, converted to positive
        assert sensor.native_value == 520.0

    def test_battery_discharge_power_sensor_when_charging(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test Battery Discharge Power sensor returns 0 when charging."""
        from custom_components.srne_inverter.sensor import SRNEBatteryDischargePowerSensor

        sensor = SRNEBatteryDischargePowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert sensor.native_value == 0  # No discharge when charging

    def test_battery_split_sensors_sum_to_original(
        self, energy_dashboard_coordinator, mock_config_entry
    ):
        """Test battery charge/discharge split sensors sum correctly."""
        from custom_components.srne_inverter.sensor import (
            SRNEBatteryPowerSensor,
            SRNEBatteryChargePowerSensor,
            SRNEBatteryDischargePowerSensor,
        )

        # Test with charging
        battery_sensor = SRNEBatteryPowerSensor(energy_dashboard_coordinator, mock_config_entry)
        charge_sensor = SRNEBatteryChargePowerSensor(energy_dashboard_coordinator, mock_config_entry)
        discharge_sensor = SRNEBatteryDischargePowerSensor(energy_dashboard_coordinator, mock_config_entry)

        assert battery_sensor.native_value == 520.0
        assert charge_sensor.native_value == 520.0
        assert discharge_sensor.native_value == 0

        # Test with discharging
        energy_dashboard_coordinator.data["battery_current"] = -10.0
        assert battery_sensor.native_value == -520.0
        assert charge_sensor.native_value == 0
        assert discharge_sensor.native_value == 520.0
