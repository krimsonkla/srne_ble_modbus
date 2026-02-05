"""Pytest configuration and fixtures for SRNE Inverter tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to Python path so we can import custom_components
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import AsyncMock, Mock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from custom_components.srne_inverter.const import DOMAIN


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Return a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="SRNE Inverter",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
        source="user",
        entry_id="test_entry_id",
    )


@pytest.fixture
def round3_coordinator_data():
    """Mock coordinator data with all Round 3 sensors."""
    return {
        # Existing Round 2
        "battery_soc": 75,
        "machine_state": 5,
        # Round 3 - Battery details
        "battery_voltage": 52.4,
        "battery_current": 12.5,  # Charging
        # Round 3 - Power monitoring
        "pv_power": 3500,
        "grid_power": -1200,  # Exporting (negative)
        "load_power": 2300,
        # Round 3 - Temperatures
        "inverter_temperature": 45.2,
        "battery_temperature": 28.5,
        # Round 3 - Priority
        "energy_priority": 0,  # Solar First
        "connected": True,
    }


@pytest.fixture
def round3_coordinator_data_discharging():
    """Mock data with battery discharging."""
    return {
        "battery_soc": 65,
        "battery_voltage": 51.2,
        "battery_current": -8.3,  # Discharging (negative)
        "pv_power": 500,  # Low solar
        "grid_power": 1800,  # Importing (positive)
        "load_power": 2300,
        "inverter_temperature": 38.5,
        "battery_temperature": 26.1,
        "machine_state": 5,
        "energy_priority": 2,  # Battery First
        "connected": True,
    }


@pytest.fixture
def mock_ble_device():
    """Mock BLE device."""
    device = Mock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "E60000231107692658"
    return device


@pytest.fixture
def mock_bleak_client():
    """Mock BleakClient for BLE communication tests."""
    client = AsyncMock()
    client.is_connected = True
    return client


@pytest.fixture
def mock_coordinator(round3_coordinator_data):
    """Create a mock coordinator with data."""
    from datetime import datetime
    from unittest.mock import PropertyMock

    coordinator = Mock()
    coordinator.data = round3_coordinator_data
    coordinator.last_update_success_time = "2024-02-03T12:00:00"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_write_register = AsyncMock(return_value=True)

    # Use PropertyMock to ensure last_update_success returns actual datetime
    type(coordinator).last_update_success = PropertyMock(
        return_value=datetime.fromisoformat("2024-02-03T12:00:00")
    )

    return coordinator


@pytest.fixture
async def hass():
    """Create a mock HomeAssistant instance."""
    from homeassistant.core import HomeAssistant

    hass_instance = Mock(spec=HomeAssistant)
    hass_instance.data = {}
    return hass_instance


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio test")
