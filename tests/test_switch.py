"""Unit tests for SRNE Inverter switch platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.srne_inverter.const import DOMAIN
from custom_components.srne_inverter.switch import SRNEPowerSwitch


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = {"battery_soc": 85, "machine_state": 1, "connected": True}
    coordinator.async_write_register = AsyncMock(return_value=True)
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.title = "Test Inverter"
    return entry


@pytest.fixture
def switch_entity(mock_coordinator, mock_config_entry):
    """Create a switch entity."""
    return SRNEPowerSwitch(mock_coordinator, mock_config_entry)


class TestSRNEPowerSwitchCreation:
    """Test switch entity initialization."""

    def test_switch_initialization(self, switch_entity, mock_config_entry):
        """Test switch entity is created with correct properties."""
        assert switch_entity.unique_id == f"{mock_config_entry.entry_id}_ac_power"
        assert switch_entity.name == "AC Power"
        assert switch_entity.device_class == "outlet"
        assert switch_entity.is_on is False  # Standby state
        assert switch_entity._optimistic_state is None

    def test_switch_device_info(self, switch_entity, mock_config_entry):
        """Test switch device info matches inverter device."""
        device_info = switch_entity.device_info
        assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
        assert device_info["name"] == mock_config_entry.title
        assert device_info["manufacturer"] == "SRNE"
        assert device_info["model"] == "HF Series Inverter"

    def test_switch_has_entity_name(self, switch_entity):
        """Test switch has entity name attribute."""
        assert switch_entity.has_entity_name is True


class TestSRNEPowerSwitchState:
    """Test switch state determination."""

    def test_is_on_with_standby_state(self, switch_entity, mock_coordinator):
        """Test switch is OFF when machine state is standby (1)."""
        mock_coordinator.data = {"machine_state": 1, "connected": True}
        assert switch_entity.is_on is False

    def test_is_on_with_manual_shutdown_state(self, switch_entity, mock_coordinator):
        """Test switch is OFF when machine state is manual shutdown (9)."""
        mock_coordinator.data = {"machine_state": 9, "connected": True}
        assert switch_entity.is_on is False

    def test_is_on_with_ac_operation_state(self, switch_entity, mock_coordinator):
        """Test switch is ON when machine state is AC power operation (4)."""
        mock_coordinator.data = {"machine_state": 4, "connected": True}
        assert switch_entity.is_on is True

    def test_is_on_with_inverter_operation_state(self, switch_entity, mock_coordinator):
        """Test switch is ON when machine state is inverter operation (5)."""
        mock_coordinator.data = {"machine_state": 5, "connected": True}
        assert switch_entity.is_on is True

    def test_is_on_with_transitional_state(self, switch_entity, mock_coordinator):
        """Test switch is unknown with transitional states."""
        # Test soft start state (3)
        mock_coordinator.data = {"machine_state": 3, "connected": True}
        assert switch_entity.is_on is None

        # Test inverter to AC state (6)
        mock_coordinator.data = {"machine_state": 6, "connected": True}
        assert switch_entity.is_on is None

    def test_is_on_with_no_data(self, switch_entity, mock_coordinator):
        """Test switch is unknown when coordinator has no data."""
        mock_coordinator.data = None
        assert switch_entity.is_on is None

    def test_is_on_with_no_machine_state(self, switch_entity, mock_coordinator):
        """Test switch is unknown when machine state is missing."""
        mock_coordinator.data = {"battery_soc": 85, "connected": True}
        assert switch_entity.is_on is None

    def test_optimistic_state_priority(self, switch_entity, mock_coordinator):
        """Test optimistic state takes priority over confirmed state."""
        # Set confirmed state to OFF
        mock_coordinator.data = {"machine_state": 1, "connected": True}
        assert switch_entity.is_on is False

        # Set optimistic state to ON
        switch_entity._optimistic_state = True
        assert switch_entity.is_on is True

        # Clear optimistic state
        switch_entity._optimistic_state = None
        assert switch_entity.is_on is False


class TestSRNEPowerSwitchOperations:
    """Test switch on/off operations."""

    @pytest.mark.asyncio
    async def test_turn_on_calls_coordinator(self, switch_entity, mock_coordinator):
        """Test turn_on writes value 1 to register 0xDF00."""
        with patch.object(switch_entity, "async_write_ha_state"):
            await switch_entity.async_turn_on()

        mock_coordinator.async_write_register.assert_called_once_with(0xDF00, 1)

    @pytest.mark.asyncio
    async def test_turn_off_calls_coordinator(self, switch_entity, mock_coordinator):
        """Test turn_off writes value 0 to register 0xDF00."""
        with patch.object(switch_entity, "async_write_ha_state"):
            await switch_entity.async_turn_off()

        mock_coordinator.async_write_register.assert_called_once_with(0xDF00, 0)

    @pytest.mark.asyncio
    async def test_optimistic_state_update_on(self, switch_entity, mock_coordinator):
        """Test switch updates state optimistically when turning on."""
        # Initial state is OFF (standby)
        assert switch_entity.is_on is False

        # Turn on
        with patch.object(switch_entity, "async_write_ha_state"):
            await switch_entity.async_turn_on()

        # State should be optimistically ON
        assert switch_entity.is_on is True
        assert switch_entity._optimistic_state is True

    @pytest.mark.asyncio
    async def test_optimistic_state_update_off(self, switch_entity, mock_coordinator):
        """Test switch updates state optimistically when turning off."""
        # Set initial state to ON
        mock_coordinator.data = {"machine_state": 4, "connected": True}
        assert switch_entity.is_on is True

        # Turn off
        with patch.object(switch_entity, "async_write_ha_state"):
            await switch_entity.async_turn_off()

        # State should be optimistically OFF
        assert switch_entity.is_on is False
        assert switch_entity._optimistic_state is False

    @pytest.mark.asyncio
    async def test_multiple_rapid_toggles(self, switch_entity, mock_coordinator):
        """Test rapid on/off toggles queue commands properly."""
        with patch.object(switch_entity, "async_write_ha_state"):
            # Turn on
            await switch_entity.async_turn_on()
            assert mock_coordinator.async_write_register.call_count == 1

            # Turn off
            await switch_entity.async_turn_off()
            assert mock_coordinator.async_write_register.call_count == 2

            # Turn on again
            await switch_entity.async_turn_on()
            assert mock_coordinator.async_write_register.call_count == 3

        # Verify final optimistic state is ON
        assert switch_entity._optimistic_state is True


class TestSRNEPowerSwitchErrorHandling:
    """Test switch error handling."""

    @pytest.mark.asyncio
    async def test_write_failure_reverts_state(self, switch_entity, mock_coordinator):
        """Test write failure reverts optimistic state."""
        mock_coordinator.async_write_register.return_value = False

        with patch.object(switch_entity, "async_write_ha_state"):
            with pytest.raises(
                HomeAssistantError, match="Failed to send power on command"
            ):
                await switch_entity.async_turn_on()

        # Optimistic state should be reverted
        assert switch_entity._optimistic_state is None

    @pytest.mark.asyncio
    async def test_coordinator_exception_handling(
        self, switch_entity, mock_coordinator
    ):
        """Test coordinator exception is caught gracefully."""
        mock_coordinator.async_write_register.side_effect = Exception("BLE error")

        with patch.object(switch_entity, "async_write_ha_state"):
            with pytest.raises(Exception, match="BLE error"):
                await switch_entity.async_turn_on()

        # Optimistic state should be reverted
        assert switch_entity._optimistic_state is None

    def test_disconnected_state_handling(self, switch_entity, mock_coordinator):
        """Test switch unavailable when coordinator disconnected."""
        mock_coordinator.data = {"battery_soc": 85, "connected": False}
        assert switch_entity.available is False

    def test_no_coordinator_data(self, switch_entity, mock_coordinator):
        """Test switch handles missing coordinator data."""
        mock_coordinator.data = None
        assert switch_entity.available is False
        assert switch_entity.is_on is None

    def test_available_with_last_update_failed(self, switch_entity, mock_coordinator):
        """Test switch unavailable when last update failed."""
        mock_coordinator.last_update_success = False
        assert switch_entity.available is False


class TestSRNEPowerSwitchMetadata:
    """Test switch metadata and attributes."""

    def test_icon(self, switch_entity):
        """Test switch icon."""
        assert switch_entity.icon == "mdi:power-plug"

    def test_extra_state_attributes_with_machine_state(
        self, switch_entity, mock_coordinator
    ):
        """Test switch provides machine state attributes."""
        mock_coordinator.data = {"machine_state": 4, "connected": True}

        attrs = switch_entity.extra_state_attributes
        assert attrs["machine_state"] == 4
        assert attrs["machine_state_name"] == "AC power operation"
        assert attrs["state_source"] == "confirmed"

    def test_extra_state_attributes_optimistic(self, switch_entity, mock_coordinator):
        """Test state_source is optimistic during pending write."""
        switch_entity._optimistic_state = True

        attrs = switch_entity.extra_state_attributes
        assert attrs["state_source"] == "optimistic"

    def test_extra_state_attributes_unknown_state(
        self, switch_entity, mock_coordinator
    ):
        """Test attributes with unknown machine state."""
        mock_coordinator.data = {"machine_state": 99, "connected": True}

        attrs = switch_entity.extra_state_attributes
        assert attrs["machine_state"] == 99
        assert attrs["machine_state_name"] == "Unknown"

    def test_extra_state_attributes_no_data(self, switch_entity, mock_coordinator):
        """Test attributes when coordinator has no data."""
        mock_coordinator.data = None

        attrs = switch_entity.extra_state_attributes
        assert attrs == {}


class TestSRNEPowerSwitchCoordinatorUpdate:
    """Test coordinator update handling."""

    def test_handle_coordinator_update_clears_optimistic(
        self, switch_entity, mock_coordinator
    ):
        """Test optimistic state cleared when confirmed."""
        # Set optimistic state to ON
        switch_entity._optimistic_state = True

        # Coordinator updates with matching state (AC operation = ON)
        mock_coordinator.data = {"machine_state": 4, "connected": True}
        with patch.object(switch_entity, "async_write_ha_state"):
            switch_entity._handle_coordinator_update()

        # Optimistic state should be cleared
        assert switch_entity._optimistic_state is None

    def test_handle_coordinator_update_keeps_optimistic_on_mismatch(
        self, switch_entity, mock_coordinator
    ):
        """Test optimistic state kept when state doesn't match."""
        # Set optimistic state to ON
        switch_entity._optimistic_state = True

        # Coordinator updates with different state (standby = OFF)
        mock_coordinator.data = {"machine_state": 1, "connected": True}
        with patch.object(switch_entity, "async_write_ha_state"):
            switch_entity._handle_coordinator_update()

        # Optimistic state should remain (command might still be processing)
        assert switch_entity._optimistic_state is True

    def test_handle_coordinator_update_with_none_confirmed(
        self, switch_entity, mock_coordinator
    ):
        """Test optimistic state kept when confirmed state is None."""
        # Set optimistic state to ON
        switch_entity._optimistic_state = True

        # Coordinator updates with transitional state (None)
        mock_coordinator.data = {"machine_state": 3, "connected": True}
        with patch.object(switch_entity, "async_write_ha_state"):
            switch_entity._handle_coordinator_update()

        # Optimistic state should remain
        assert switch_entity._optimistic_state is True


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test switch platform setup."""
    mock_coordinator = MagicMock()
    mock_coordinator.data = {"battery_soc": 85, "machine_state": 1, "connected": True}
    mock_coordinator.async_write_register = AsyncMock(return_value=True)

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.title = "Test Inverter"

    mock_hass = MagicMock(spec=HomeAssistant)
    mock_hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    async_add_entities = MagicMock()

    from custom_components.srne_inverter.switch import async_setup_entry

    await async_setup_entry(mock_hass, mock_entry, async_add_entities)

    # Verify one switch entity was added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SRNEPowerSwitch)
