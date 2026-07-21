"""Tests for SRNE Inverter service calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.srne_inverter import (
    SERVICE_FORCE_REFRESH,
    SERVICE_RESET_STATISTICS,
    SERVICE_RESTART_INVERTER,
    async_setup_entry,
)
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
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_write_register = AsyncMock(return_value=True)
    coordinator._load_storage = AsyncMock()
    coordinator._failed_reads = 5
    coordinator._total_updates = 100
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


@pytest.fixture
async def setup_with_services(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_coordinator
):
    """Run async_setup_entry with mocks so services register on the real
    ServiceRegistry. Tests then call them via hass.services.async_call."""
    device_config = {"registers": {}, "device": {}}
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
        await async_setup_entry(hass, mock_config_entry)

    yield

    # Cleanup: unregister so subsequent tests don't collide
    for svc in (
        SERVICE_FORCE_REFRESH,
        SERVICE_RESET_STATISTICS,
        SERVICE_RESTART_INVERTER,
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)


async def test_force_refresh_service(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Force refresh calls coordinator.async_request_refresh."""
    await hass.services.async_call(DOMAIN, SERVICE_FORCE_REFRESH, {}, blocking=True)

    mock_coordinator.async_request_refresh.assert_called_once()


async def test_reset_statistics_service(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Reset statistics zeros counters and triggers refresh."""
    mock_coordinator._failed_reads = 10
    mock_coordinator._total_updates = 200

    await hass.services.async_call(DOMAIN, SERVICE_RESET_STATISTICS, {}, blocking=True)

    assert mock_coordinator._failed_reads == 0
    assert mock_coordinator._total_updates == 0
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_restart_inverter_requires_confirmation(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Restart with confirm=False must raise and not write."""
    with pytest.raises(ValueError, match="Restart requires confirmation"):
        await hass.services.async_call(
            DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": False}, blocking=True
        )

    mock_coordinator.async_write_register.assert_not_called()


async def test_restart_inverter_no_confirm_parameter(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Restart without confirm parameter is rejected by the service schema."""
    import voluptuous as vol

    with pytest.raises(vol.MultipleInvalid, match="confirm"):
        await hass.services.async_call(
            DOMAIN, SERVICE_RESTART_INVERTER, {}, blocking=True
        )

    mock_coordinator.async_write_register.assert_not_called()


async def test_restart_inverter_with_confirmation(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Restart with confirm=True writes 0x0001 to register 0xDF01."""
    await hass.services.async_call(
        DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True}, blocking=True
    )

    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


async def test_restart_inverter_handles_failure(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Restart converts write failure into HomeAssistantError."""
    mock_coordinator.async_write_register = AsyncMock(return_value=False)

    with pytest.raises(HomeAssistantError, match="Failed to send restart command"):
        await hass.services.async_call(
            DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True}, blocking=True
        )

    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


async def test_services_registered_on_setup(hass: HomeAssistant, setup_with_services):
    """All three services should be registered during setup."""
    assert hass.services.has_service(DOMAIN, SERVICE_FORCE_REFRESH)
    assert hass.services.has_service(DOMAIN, SERVICE_RESET_STATISTICS)
    assert hass.services.has_service(DOMAIN, SERVICE_RESTART_INVERTER)


async def test_services_unregistered_on_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, setup_with_services
):
    """Unloading the config entry unregisters all three services."""
    from custom_components.srne_inverter import async_unload_entry

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new=AsyncMock(return_value=True),
    ):
        await async_unload_entry(hass, mock_config_entry)

    assert not hass.services.has_service(DOMAIN, SERVICE_FORCE_REFRESH)
    assert not hass.services.has_service(DOMAIN, SERVICE_RESET_STATISTICS)
    assert not hass.services.has_service(DOMAIN, SERVICE_RESTART_INVERTER)


async def test_restart_inverter_success_logging(
    hass: HomeAssistant, mock_coordinator, setup_with_services
):
    """Restart with confirm=True completes without exception."""
    await hass.services.async_call(
        DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True}, blocking=True
    )

    mock_coordinator.async_write_register.assert_called_once()
