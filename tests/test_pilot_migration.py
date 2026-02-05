"""Test pilot migration to configurable entities."""

import os
from unittest.mock import Mock, patch
import pytest

from custom_components.srne_inverter.config_loader import ConfigLoader
from custom_components.srne_inverter.entity_factory import EntityFactory
from custom_components.srne_inverter.configurable_sensor import ConfigurableSensor
from custom_components.srne_inverter.configurable_switch import ConfigurableSwitch
from custom_components.srne_inverter.configurable_select import ConfigurableSelect


@pytest.fixture
def pilot_config_path():
    """Return path to pilot configuration."""
    base_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(
        base_path,
        "custom_components",
        "srne_inverter",
        "config",
        "entities_pilot.yaml"
    )


def test_pilot_config_exists(pilot_config_path):
    """Test that pilot configuration file exists."""
    assert os.path.exists(pilot_config_path), "Pilot config file should exist"


def test_pilot_config_loads(pilot_config_path):
    """Test pilot configuration loads successfully."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    assert config is not None, "Config should load"
    assert 'sensors' in config, "Config should have sensors"
    assert 'switches' in config, "Config should have switches"
    assert 'selects' in config, "Config should have selects"

    # Verify we have the expected pilot entities
    assert len(config['sensors']) == 3, "Should have 3 pilot sensors"
    assert len(config['switches']) == 1, "Should have 1 pilot switch"
    assert len(config['selects']) == 1, "Should have 1 pilot select"


def test_pilot_sensor_configs(pilot_config_path):
    """Test pilot sensor configurations are valid."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    sensors = config['sensors']

    # Check battery_soc sensor
    battery_soc = next(s for s in sensors if s['entity_id'] == 'battery_soc')
    assert battery_soc['name'] == 'Battery SOC'
    assert battery_soc['source_type'] == 'coordinator_data'
    assert battery_soc['data_key'] == 'battery_soc'
    assert battery_soc['device_class'] == 'battery'
    assert battery_soc['unit_of_measurement'] == '%'

    # Check pv_power sensor
    pv_power = next(s for s in sensors if s['entity_id'] == 'pv_power')
    assert pv_power['name'] == 'PV Power'
    assert pv_power['device_class'] == 'power'
    assert pv_power['unit_of_measurement'] == 'W'

    # Check grid_power sensor (has template attributes)
    grid_power = next(s for s in sensors if s['entity_id'] == 'grid_power')
    assert grid_power['name'] == 'Grid Power'
    assert 'attributes' in grid_power
    assert 'direction' in grid_power['attributes']


def test_pilot_switch_config(pilot_config_path):
    """Test pilot switch configuration is valid."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    switches = config['switches']

    # Check ac_power switch
    ac_power = next(s for s in switches if s['entity_id'] == 'ac_power')
    assert ac_power['name'] == 'AC Power'
    assert ac_power['register'] == 0xDF00
    assert ac_power['type'] == 'command'
    assert ac_power['on_value'] == 0x0001
    assert ac_power['off_value'] == 0x0000


def test_pilot_select_config(pilot_config_path):
    """Test pilot select configuration is valid."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    selects = config['selects']

    # Check energy_priority select
    energy_priority = next(s for s in selects if s['entity_id'] == 'energy_priority')
    assert energy_priority['name'] == 'Energy Priority'
    assert energy_priority['register'] == 0xE204
    assert energy_priority['type'] == 'read_write'
    assert 'options' in energy_priority
    assert energy_priority['options'] == {
        0: 'Solar First',
        1: 'Utility First',
        2: 'Battery First'
    }


def test_pilot_entities_created(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test pilot entities are created from config."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    assert len(entities) == 5, "Should create 5 pilot entities (3 sensors + 1 switch + 1 select)"

    # Check entity types
    sensors = [e for e in entities if isinstance(e, ConfigurableSensor)]
    switches = [e for e in entities if isinstance(e, ConfigurableSwitch)]
    selects = [e for e in entities if isinstance(e, ConfigurableSelect)]

    assert len(sensors) == 3, "Should have 3 sensors"
    assert len(switches) == 1, "Should have 1 switch"
    assert len(selects) == 1, "Should have 1 select"


def test_unique_ids_match_manual(mock_coordinator, mock_config_entry):
    """Verify configurable entities have same unique_ids as manual.

    This is critical - unique IDs must match to prevent entity recreation.
    """
    # Test with single sensor config
    config = {
        'sensors': [{
            'entity_id': 'battery_soc',
            'name': 'Battery SOC',
            'source_type': 'coordinator_data',
            'data_key': 'battery_soc',
        }]
    }

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    sensor = entities[0]
    expected_unique_id = f"{mock_config_entry.entry_id}_battery_soc"
    assert sensor.unique_id == expected_unique_id, \
        f"Unique ID should be {expected_unique_id}, got {sensor.unique_id}"


def test_unique_id_format_consistency(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test all pilot entities follow consistent unique_id format."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    entry_id = mock_config_entry.entry_id

    # All unique IDs should start with entry_id
    for entity in entities:
        assert entity.unique_id.startswith(entry_id), \
            f"Entity {entity.name} unique_id should start with entry_id"

        # Format should be: {entry_id}_{entity_id}
        assert entity.unique_id.count('_') >= 1, \
            f"Entity {entity.name} unique_id should contain underscore separator"


def test_entity_names_set_correctly(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test entities have correct names from config."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    # Check specific entity names
    entity_names = {e.name for e in entities}

    expected_names = {
        'Battery SOC',
        'PV Power',
        'Grid Power',
        'AC Power',
        'Energy Priority'
    }

    assert entity_names == expected_names, \
        f"Entity names mismatch. Expected {expected_names}, got {entity_names}"


def test_device_info_shared(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test all entities share the same device info."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    # All entities should have device_info
    for entity in entities:
        assert hasattr(entity, 'device_info'), f"Entity {entity.name} should have device_info"
        assert entity.device_info is not None, f"Entity {entity.name} device_info should not be None"

        # Check required device_info fields
        assert 'identifiers' in entity.device_info
        assert 'name' in entity.device_info
        assert 'manufacturer' in entity.device_info
        assert 'model' in entity.device_info


def test_sensor_properties_configured(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test sensor properties are properly configured."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    sensors = [e for e in entities if isinstance(e, ConfigurableSensor)]

    # Check battery_soc sensor properties
    battery_soc = next(s for s in sensors if s.name == 'Battery SOC')
    assert battery_soc.device_class == 'battery'
    assert battery_soc.native_unit_of_measurement == '%'
    assert battery_soc.state_class == 'measurement'

    # Check pv_power sensor properties
    pv_power = next(s for s in sensors if s.name == 'PV Power')
    assert pv_power.device_class == 'power'
    assert pv_power.native_unit_of_measurement == 'W'


def test_switch_properties_configured(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test switch properties are properly configured."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    switches = [e for e in entities if isinstance(e, ConfigurableSwitch)]

    # Check ac_power switch
    ac_power = switches[0]
    assert ac_power.name == 'AC Power'
    assert hasattr(ac_power, 'is_on')


def test_select_properties_configured(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test select properties are properly configured."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    selects = [e for e in entities if isinstance(e, ConfigurableSelect)]

    # Check energy_priority select
    energy_priority = selects[0]
    assert energy_priority.name == 'Energy Priority'
    assert hasattr(energy_priority, 'current_option')
    assert hasattr(energy_priority, 'options')


def test_no_duplicate_unique_ids(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test no duplicate unique IDs in pilot entities."""
    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    unique_ids = [e.unique_id for e in entities]

    # Check for duplicates
    assert len(unique_ids) == len(set(unique_ids)), \
        f"Found duplicate unique IDs: {[uid for uid in unique_ids if unique_ids.count(uid) > 1]}"


def test_pilot_entity_availability(mock_coordinator, mock_config_entry, pilot_config_path):
    """Test entities inherit availability from coordinator."""
    # Setup coordinator with connected state
    mock_coordinator.data = {'connected': True, 'battery_soc': 50}

    loader = ConfigLoader(pilot_config_path)
    config = loader.load()

    factory = EntityFactory(mock_coordinator, mock_config_entry)
    entities = factory.create_entities_from_config(config)

    # All entities should be available when coordinator is available
    for entity in entities:
        assert entity.available is True, f"Entity {entity.name} should be available"

    # Test unavailable when disconnected
    mock_coordinator.data = {'connected': False}

    for entity in entities:
        assert entity.available is False, f"Entity {entity.name} should be unavailable when disconnected"
