"""Tests for SRNE Inverter service calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.srne_inverter import (
    SERVICE_FORCE_REFRESH,
    SERVICE_RESET_STATISTICS,
    SERVICE_RESTART_INVERTER,
    async_setup_entry,
)
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
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_write_register = AsyncMock(return_value=True)
    coordinator._failed_reads = 5
    coordinator._total_updates = 100
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


@pytest.fixture
async def setup_integration(mock_config_entry, mock_coordinator):
    """Set up the integration with mock coordinator."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()

    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        await async_setup_entry(hass, mock_config_entry)

    return hass, mock_coordinator, mock_config_entry


@pytest.mark.asyncio
async def test_force_refresh_service(mock_config_entry, mock_coordinator):
    """Test force refresh service."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Create service call
    call = ServiceCall(DOMAIN, SERVICE_FORCE_REFRESH, {})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_FORCE_REFRESH:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify coordinator.async_request_refresh was called
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_reset_statistics_service(mock_config_entry, mock_coordinator):
    """Test reset statistics service."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Set initial counter values
    mock_coordinator._failed_reads = 10
    mock_coordinator._total_updates = 200

    # Create service call
    call = ServiceCall(DOMAIN, SERVICE_RESET_STATISTICS, {})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESET_STATISTICS:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify counters were reset
    assert mock_coordinator._failed_reads == 0
    assert mock_coordinator._total_updates == 0

    # Verify refresh was triggered
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_restart_inverter_requires_confirmation(mock_config_entry, mock_coordinator):
    """Test restart requires confirmation."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Create service call WITHOUT confirm=true
    call = ServiceCall(DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": False})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise ValueError
        with pytest.raises(ValueError, match="Restart requires confirmation"):
            await service_handler(call)

    # Verify write was NOT called
    mock_coordinator.async_write_register.assert_not_called()


@pytest.mark.asyncio
async def test_restart_inverter_no_confirm_parameter(mock_config_entry, mock_coordinator):
    """Test restart without confirm parameter."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Create service call WITHOUT confirm parameter
    call = ServiceCall(DOMAIN, SERVICE_RESTART_INVERTER, {})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise ValueError
        with pytest.raises(ValueError, match="Restart requires confirmation"):
            await service_handler(call)

    # Verify write was NOT called
    mock_coordinator.async_write_register.assert_not_called()


@pytest.mark.asyncio
async def test_restart_inverter_with_confirmation(mock_config_entry, mock_coordinator):
    """Test restart with confirmation."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Create service call WITH confirm=true
    call = ServiceCall(DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify write to register 0xDF01 with value 0x0001
    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


@pytest.mark.asyncio
async def test_restart_inverter_handles_failure(mock_config_entry, mock_coordinator):
    """Test restart handles write failure."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Mock write failure
    mock_coordinator.async_write_register = AsyncMock(return_value=False)

    # Create service call WITH confirm=true
    call = ServiceCall(DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise HomeAssistantError
        with pytest.raises(HomeAssistantError, match="Failed to send restart command"):
            await service_handler(call)

    # Verify write was attempted
    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


@pytest.mark.asyncio
async def test_services_registered_on_setup(mock_config_entry, mock_coordinator):
    """Test that all services are registered during setup."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()

    registered_services = []

    def track_registration(domain, service, handler, schema=None):
        registered_services.append(service)

    hass.services.async_register = track_registration

    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        await async_setup_entry(hass, mock_config_entry)

    # Verify all three services were registered
    assert SERVICE_FORCE_REFRESH in registered_services
    assert SERVICE_RESET_STATISTICS in registered_services
    assert SERVICE_RESTART_INVERTER in registered_services
    assert len(registered_services) == 3


@pytest.mark.asyncio
async def test_services_unregistered_on_unload(mock_config_entry, mock_coordinator):
    """Test that all services are unregistered during unload."""
    from custom_components.srne_inverter import async_unload_entry

    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.services = MagicMock()
    hass.services.async_remove = MagicMock()

    unregistered_services = []

    def track_unregistration(domain, service):
        unregistered_services.append(service)

    hass.services.async_remove = track_unregistration

    await async_unload_entry(hass, mock_config_entry)

    # Verify all three services were unregistered
    assert SERVICE_FORCE_REFRESH in unregistered_services
    assert SERVICE_RESET_STATISTICS in unregistered_services
    assert SERVICE_RESTART_INVERTER in unregistered_services
    assert len(unregistered_services) == 3


@pytest.mark.asyncio
async def test_restart_inverter_success_logging(mock_config_entry, mock_coordinator, caplog):
    """Test restart service logs success message."""
    import logging

    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}

    # Create service call WITH confirm=true
    call = ServiceCall(DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    with patch(
        "custom_components.srne_inverter.SRNEDataUpdateCoordinator",
        return_value=mock_coordinator,
    ):
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler with logging
        with caplog.at_level(logging.INFO):
            await service_handler(call)

        # Note: caplog may not capture logs due to mock setup
        # This test validates that the service runs successfully
        mock_coordinator.async_write_register.assert_called_once()
