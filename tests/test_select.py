"""Tests for the SRNE Inverter select platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.srne_inverter.select import (
    PRIORITY_OPTIONS,
    PRIORITY_TO_VALUE,
    VALUE_TO_PRIORITY,
    SRNEEnergyPrioritySelect,
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
    """Create a mock coordinator with Solar First priority."""
    coordinator = MagicMock()
    coordinator.data = {
        "energy_priority": 0,  # Solar First
        "connected": True,
    }
    coordinator.async_write_register = AsyncMock(return_value=True)
    return coordinator


@pytest.fixture
def mock_coordinator_battery_first():
    """Create a mock coordinator with Battery First priority."""
    coordinator = MagicMock()
    coordinator.data = {
        "energy_priority": 2,  # Battery First
        "connected": True,
    }
    coordinator.async_write_register = AsyncMock(return_value=True)
    return coordinator


class TestSelectPlatform:
    """Test the select platform setup."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(
        self, mock_hass, mock_config_entry, mock_coordinator
    ):
        """Test select platform setup."""
        from custom_components.srne_inverter.const import DOMAIN

        mock_hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
        async_add_entities = MagicMock()

        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], SRNEEnergyPrioritySelect)


class TestPriorityMapping:
    """Test priority value mapping."""

    def test_priority_options(self):
        """Test priority options are correct."""
        assert PRIORITY_OPTIONS == ["Solar First", "Utility First", "Battery First"]

    def test_priority_to_value_mapping(self):
        """Test priority name to value mapping."""
        assert PRIORITY_TO_VALUE["Solar First"] == 0
        assert PRIORITY_TO_VALUE["Utility First"] == 1
        assert PRIORITY_TO_VALUE["Battery First"] == 2

    def test_value_to_priority_mapping(self):
        """Test value to priority name mapping."""
        assert VALUE_TO_PRIORITY[0] == "Solar First"
        assert VALUE_TO_PRIORITY[1] == "Utility First"
        assert VALUE_TO_PRIORITY[2] == "Battery First"


class TestSRNEEnergyPrioritySelect:
    """Test the energy priority select entity."""

    def test_select_initialization(self, mock_coordinator, mock_config_entry):
        """Test select entity initialization."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        assert select.unique_id == "test_entry_energy_priority"
        assert select.name == "Energy Priority"
        assert select.icon == "mdi:priority-high"
        assert select.options == PRIORITY_OPTIONS

    def test_device_info(self, mock_coordinator, mock_config_entry):
        """Test select device info."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        device_info = select.device_info
        assert device_info is not None
        assert ("srne_inverter", "test_entry") in device_info["identifiers"]
        assert device_info["name"] == "Test SRNE Inverter"
        assert device_info["manufacturer"] == "SRNE"

    def test_current_option_solar_first(self, mock_coordinator, mock_config_entry):
        """Test current option shows Solar First."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        assert select.current_option == "Solar First"

    def test_current_option_battery_first(
        self, mock_coordinator_battery_first, mock_config_entry
    ):
        """Test current option shows Battery First."""
        select = SRNEEnergyPrioritySelect(
            mock_coordinator_battery_first, mock_config_entry
        )

        assert select.current_option == "Battery First"

    def test_current_option_utility_first(self, mock_coordinator, mock_config_entry):
        """Test current option shows Utility First."""
        mock_coordinator.data["energy_priority"] = 1
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        assert select.current_option == "Utility First"

    def test_current_option_no_data(self, mock_coordinator, mock_config_entry):
        """Test current option when no data."""
        mock_coordinator.data = None
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        assert select.current_option is None

    @pytest.mark.asyncio
    async def test_select_option_success(self, mock_coordinator, mock_config_entry):
        """Test selecting an option successfully."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "async_write_ha_state"):
            await select.async_select_option("Utility First")

        # Verify write called with correct register and value (0xE204 = Output Priority)
        mock_coordinator.async_write_register.assert_called_once_with(0xE204, 1)

        # Verify optimistic state
        assert select._optimistic_option == "Utility First"

    @pytest.mark.asyncio
    async def test_select_option_battery_first(
        self, mock_coordinator, mock_config_entry
    ):
        """Test selecting Battery First option."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "async_write_ha_state"):
            await select.async_select_option("Battery First")

        mock_coordinator.async_write_register.assert_called_once_with(0xE204, 2)
        assert select._optimistic_option == "Battery First"

    @pytest.mark.asyncio
    async def test_select_option_invalid(self, mock_coordinator, mock_config_entry):
        """Test selecting invalid option raises error."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "async_write_ha_state"):
            with pytest.raises(HomeAssistantError, match="Invalid priority option"):
                await select.async_select_option("Invalid Option")

    @pytest.mark.asyncio
    async def test_select_option_write_failure(
        self, mock_coordinator, mock_config_entry
    ):
        """Test select option handles write failure."""
        mock_coordinator.async_write_register = AsyncMock(return_value=False)
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)
        initial_option = select.current_option

        with patch.object(select, "async_write_ha_state"):
            with pytest.raises(
                HomeAssistantError, match="Failed to send priority command"
            ):
                await select.async_select_option("Battery First")

        # Verify state reverted (optimistic flag cleared)
        assert select._optimistic_option is None
        # Original state should be maintained
        assert select.current_option == initial_option

    @pytest.mark.asyncio
    async def test_select_option_write_exception(
        self, mock_coordinator, mock_config_entry
    ):
        """Test select option handles write exception."""
        mock_coordinator.async_write_register = AsyncMock(
            side_effect=Exception("BLE error")
        )
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "async_write_ha_state"):
            with pytest.raises(Exception, match="BLE error"):
                await select.async_select_option("Battery First")

        # Verify state reverted
        assert select._optimistic_option is None

    def test_optimistic_state_during_write(self, mock_coordinator, mock_config_entry):
        """Test optimistic state is preferred during pending write."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        # Set optimistic state
        select._optimistic_option = "Battery First"

        # Should return optimistic state even though coordinator shows Solar First
        assert select.current_option == "Battery First"

    def test_coordinator_update_clears_optimistic(
        self, mock_coordinator, mock_config_entry
    ):
        """Test coordinator update clears optimistic state when confirmed."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        # Set optimistic state
        select._optimistic_option = "Battery First"
        assert select._optimistic_option is not None

        # Simulate coordinator update with confirmation
        mock_coordinator.data["energy_priority"] = 2  # Battery First
        with patch.object(select, "async_write_ha_state"):
            select._handle_coordinator_update()

        # Optimistic state should be cleared
        assert select._optimistic_option is None
        assert select.current_option == "Battery First"

    def test_coordinator_update_keeps_optimistic_if_mismatch(
        self, mock_coordinator, mock_config_entry
    ):
        """Test coordinator update keeps optimistic if value doesn't match."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        # Set optimistic state
        select._optimistic_option = "Battery First"

        # Simulate coordinator update with different value (not confirmed yet)
        mock_coordinator.data["energy_priority"] = 0  # Still Solar First
        with patch.object(select, "async_write_ha_state"):
            select._handle_coordinator_update()

        # Optimistic state should remain
        assert select._optimistic_option == "Battery First"

    def test_available_when_connected(self, mock_coordinator, mock_config_entry):
        """Test select is available when connected."""
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "coordinator", mock_coordinator):
            with patch(
                "homeassistant.helpers.update_coordinator.CoordinatorEntity.available",
                new_callable=lambda: property(lambda self: True),
            ):
                assert select.available is True

    def test_available_when_disconnected(self, mock_coordinator, mock_config_entry):
        """Test select is unavailable when disconnected."""
        mock_coordinator.data = {"connected": False}
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "coordinator", mock_coordinator):
            with patch(
                "homeassistant.helpers.update_coordinator.CoordinatorEntity.available",
                new_callable=lambda: property(lambda self: True),
            ):
                assert select.available is False

    def test_available_when_no_data(self, mock_coordinator, mock_config_entry):
        """Test select is unavailable when no data."""
        mock_coordinator.data = None
        select = SRNEEnergyPrioritySelect(mock_coordinator, mock_config_entry)

        with patch.object(select, "coordinator", mock_coordinator):
            with patch(
                "homeassistant.helpers.update_coordinator.CoordinatorEntity.available",
                new_callable=lambda: property(lambda self: True),
            ):
                assert select.available is False
