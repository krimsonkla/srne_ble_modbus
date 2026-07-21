"""Tests for the SRNE Inverter integration __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srne_inverter import async_setup_entry, async_unload_entry
from custom_components.srne_inverter.const import DOMAIN


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a MockConfigEntry added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test SRNE Inverter",
        data={"address": "AA:BB:CC:DD:EE:FF"},
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_shutdown = AsyncMock()
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


async def test_async_setup_entry_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_coordinator
):
    """Test successful setup of a config entry."""
    device_config = {"registers": {}, "device": {}}
    mock_coordinator._load_storage = AsyncMock()
    fake_container = MagicMock()
    fake_container.coordinator = mock_coordinator

    with patch(
        "custom_components.srne_inverter.presentation.container.create_container",
        return_value=fake_container,
    ), patch(
        "custom_components.srne_inverter.load_entity_config",
        new=AsyncMock(return_value=device_config),
    ), patch(
        "custom_components.srne_inverter.merge_detected_features",
        return_value=device_config,
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new=AsyncMock(return_value=None),
    ):
        result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    mock_coordinator.async_config_entry_first_refresh.assert_called_once()


async def test_async_setup_entry_connection_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_coordinator
):
    """Test setup failure when connection fails."""
    device_config = {"registers": {}, "device": {}}
    mock_coordinator._load_storage = AsyncMock()
    mock_coordinator.async_config_entry_first_refresh.side_effect = Exception(
        "Connection failed"
    )
    fake_container = MagicMock()
    fake_container.coordinator = mock_coordinator

    with patch(
        "custom_components.srne_inverter.presentation.container.create_container",
        return_value=fake_container,
    ), patch(
        "custom_components.srne_inverter.load_entity_config",
        new=AsyncMock(return_value=device_config),
    ), patch(
        "custom_components.srne_inverter.merge_detected_features",
        return_value=device_config,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_async_unload_entry_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_coordinator
):
    """Test successful unload of a config entry."""
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_called_once()


async def test_async_unload_entry_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_coordinator
):
    """Test unload when platform unload fails."""
    hass.data[DOMAIN] = {mock_config_entry.entry_id: {"coordinator": mock_coordinator}}
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_not_called()
