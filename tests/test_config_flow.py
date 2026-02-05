"""Tests for the SRNE Inverter config flow."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResultType

from custom_components.srne_inverter.config_flow import SRNEConfigFlow
from custom_components.srne_inverter.const import DOMAIN


@pytest.fixture
def mock_bluetooth_service_info():
    """Create mock bluetooth service info."""
    info = MagicMock()
    info.address = "AA:BB:CC:DD:EE:FF"
    info.name = "E6-TestDevice"
    return info


@pytest.fixture
def mock_discovered_devices():
    """Create mock discovered devices."""
    device1 = MagicMock()
    device1.address = "AA:BB:CC:DD:EE:FF"
    device1.name = "E6-Inverter1"

    device2 = MagicMock()
    device2.address = "11:22:33:44:55:66"
    device2.name = "E6-Inverter2"

    return [device1, device2]


class TestSRNEConfigFlow:
    """Test the SRNE config flow."""

    @pytest.mark.asyncio
    async def test_user_flow_success(self, mock_discovered_devices):
        """Test successful user configuration flow."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.hass.config_entries = MagicMock()
        flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
            return_value=None
        )
        flow.context = {}  # Initialize context as dict

        # Mock device scanning
        with patch.object(
            flow,
            "_async_scan_devices",
            return_value={
                "AA:BB:CC:DD:EE:FF": "E6-Inverter1 (AA:BB:CC:DD:EE:FF)",
                "11:22:33:44:55:66": "E6-Inverter2 (11:22:33:44:55:66)",
            },
        ):
            # Show form with discovered devices
            result = await flow.async_step_user()

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"] == {}

        # Submit user selection
        with patch(
            "custom_components.srne_inverter.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_discovered_devices[0],
        ):
            result = await flow.async_step_user(
                user_input={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"}
            )

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "SRNE Inverter"
            assert result["data"][CONF_ADDRESS] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_user_flow_no_devices(self):
        """Test user flow when no devices found."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}  # Initialize context as dict

        with patch.object(flow, "_async_scan_devices", return_value={}):
            result = await flow.async_step_user()

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "no_devices_found"

    @pytest.mark.asyncio
    async def test_user_flow_device_not_found(self, mock_discovered_devices):
        """Test user flow when selected device is not found."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.hass.config_entries = MagicMock()
        flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
            return_value=None
        )
        flow.context = {}  # Initialize context as dict

        with patch.object(
            flow,
            "_async_scan_devices",
            return_value={"AA:BB:CC:DD:EE:FF": "E6-Inverter1 (AA:BB:CC:DD:EE:FF)"},
        ):
            # Initial form display
            await flow.async_step_user()

        # Device not found during validation
        with patch(
            "custom_components.srne_inverter.config_flow.bluetooth.async_ble_device_from_address",
            return_value=None,
        ):
            result = await flow.async_step_user(
                user_input={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"}
            )

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "no_devices_found"

    @pytest.mark.asyncio
    async def test_user_flow_already_configured(self, mock_discovered_devices):
        """Test user flow when device is already configured."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}  # Initialize context as dict

        # Set unique ID to simulate already configured device
        await flow.async_set_unique_id("AA:BB:CC:DD:EE:FF")

        with patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=data_entry_flow.AbortFlow("already_configured"),
        ), patch.object(
            flow,
            "_async_scan_devices",
            return_value={"AA:BB:CC:DD:EE:FF": "E6-Inverter1 (AA:BB:CC:DD:EE:FF)"},
        ):
            await flow.async_step_user()

            with pytest.raises(data_entry_flow.AbortFlow):
                with patch(
                    "custom_components.srne_inverter.config_flow.bluetooth.async_ble_device_from_address",
                    return_value=mock_discovered_devices[0],
                ):
                    await flow.async_step_user(
                        user_input={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"}
                    )

    @pytest.mark.asyncio
    async def test_bluetooth_discovery(self, mock_bluetooth_service_info):
        """Test bluetooth discovery flow."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.hass.config_entries = MagicMock()
        flow.hass.config_entries.async_entry_for_domain_unique_id = MagicMock(
            return_value=None
        )
        flow.context = {}  # Initialize context as dict

        result = await flow.async_step_bluetooth(mock_bluetooth_service_info)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "bluetooth_confirm"
        assert flow.context["title_placeholders"]["name"] == "E6-TestDevice"

    @pytest.mark.asyncio
    async def test_bluetooth_confirm(self, mock_bluetooth_service_info):
        """Test bluetooth confirmation step."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.context = {
            "unique_id": "AA:BB:CC:DD:EE:FF",
            "title_placeholders": {"name": "E6-TestDevice"},
        }
        flow._discovered_devices["AA:BB:CC:DD:EE:FF"] = "E6-TestDevice"

        result = await flow.async_step_bluetooth_confirm(user_input={})

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "E6-TestDevice"
        assert result["data"][CONF_ADDRESS] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_scan_devices(self):
        """Test device scanning."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}  # Initialize context as dict

        mock_device1 = MagicMock()
        mock_device1.address = "AA:BB:CC:DD:EE:FF"
        mock_device1.name = "E60-Inverter1"

        mock_device2 = MagicMock()
        mock_device2.address = "11:22:33:44:55:66"
        mock_device2.name = "OtherDevice"  # Should be filtered out

        with patch(
            "custom_components.srne_inverter.config_flow.bluetooth.async_discovered_service_info",
            return_value=[mock_device1, mock_device2],
        ):
            devices = await flow._async_scan_devices()

            assert len(devices) == 1
            assert "AA:BB:CC:DD:EE:FF" in devices
            assert "11:22:33:44:55:66" not in devices

    @pytest.mark.asyncio
    async def test_scan_devices_error(self):
        """Test device scanning with error."""
        flow = SRNEConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}  # Initialize context as dict

        with patch(
            "custom_components.srne_inverter.config_flow.bluetooth.async_discovered_service_info",
            side_effect=Exception("Bluetooth error"),
        ):
            devices = await flow._async_scan_devices()

            assert devices == {}
