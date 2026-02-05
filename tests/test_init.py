"""Tests for the SRNE Inverter integration __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.srne_inverter import async_setup_entry, async_unload_entry
from custom_components.srne_inverter.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    entry.title = "Test SRNE Inverter"
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_shutdown = AsyncMock()
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_config_entry, mock_coordinator):
    """Test successful setup of a config entry."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_connection_failure(
    mock_config_entry, mock_coordinator
):
    """Test setup failure when connection fails."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}

    # Simulate connection failure
    mock_coordinator.async_config_entry_first_refresh.side_effect = Exception(
        "Connection failed"
    )

    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry_success(mock_config_entry, mock_coordinator):
    """Test successful unload of a config entry."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_called_once()
    hass.config_entries.async_unload_platforms.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(mock_config_entry, mock_coordinator):
    """Test unload when platform unload fails."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    # Coordinator should remain in hass.data if unload fails
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_not_called()
