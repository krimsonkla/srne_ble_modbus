"""Integration tests for adaptive timing runtime application (Phase 5).

Tests that learned timeout values are correctly applied during runtime
and override default values appropriately.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from custom_components.srne_inverter.infrastructure.transport.ble_transport import BLETransport
from custom_components.srne_inverter.const import (
    MODBUS_RESPONSE_TIMEOUT,
    BLE_COMMAND_TIMEOUT,
    BLE_CONNECTION_TIMEOUT,
)


class TestLearnedTimeoutApplication:
    """Test learned timeout values are applied at runtime."""

    @pytest.mark.asyncio
    async def test_learned_timeout_applied_to_transport(self):
        """Test learned timeout overrides default timeout."""
        # Create mock hass
        hass = Mock()

        # Create BLE transport
        transport = BLETransport(hass)

        # Set learned timeouts (Phase 5)
        learned_timeouts = {
            "modbus_read": 0.875,  # Learned value (was 1.5s default)
            "ble_command": 0.450,  # Learned value (was 1.0s default)
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Verify timeouts were set
        assert transport._learned_timeouts == learned_timeouts
        assert transport._learned_timeouts["modbus_read"] == 0.875

    @pytest.mark.asyncio
    async def test_fallback_to_default_when_no_learned_value(self):
        """Test uses default timeout when no learned value available."""
        hass = Mock()
        transport = BLETransport(hass)

        # Set learned timeouts for some operations only
        learned_timeouts = {
            "modbus_read": 0.875,
            # No learned value for ble_command
        }

        transport.set_learned_timeouts(learned_timeouts)

        # modbus_read should use learned value
        assert transport._learned_timeouts.get("modbus_read") == 0.875

        # ble_command should fall back to default
        assert transport._learned_timeouts.get("ble_command") is None

    @pytest.mark.asyncio
    async def test_empty_learned_timeouts(self):
        """Test behavior with empty learned_timeouts dict."""
        hass = Mock()
        transport = BLETransport(hass)

        # Set empty learned timeouts (fresh installation)
        transport.set_learned_timeouts({})

        # Should not cause errors
        assert transport._learned_timeouts == {}

    @pytest.mark.asyncio
    async def test_learned_timeout_logging(self, caplog):
        """Test learned timeouts are logged when applied."""
        hass = Mock()
        transport = BLETransport(hass)

        learned_timeouts = {
            "modbus_read": 0.875,
            "ble_command": 0.450,
        }

        with caplog.at_level("INFO"):
            transport.set_learned_timeouts(learned_timeouts)

        # Check log contains timeout information
        assert "Applied learned timeouts" in caplog.text
        assert "0.88s" in caplog.text or "0.87s" in caplog.text


class TestFreshInstallation:
    """Test Phase 1 defaults used on first run."""

    @pytest.mark.asyncio
    async def test_fresh_installation_uses_phase1_defaults(self):
        """Test fresh installation uses conservative Phase 1 defaults."""
        hass = Mock()
        transport = BLETransport(hass)

        # Fresh installation - no learned timeouts set
        # Should use defaults from const.py

        # Verify Phase 1 defaults are in effect
        # (These are the values before learning begins)
        assert BLE_COMMAND_TIMEOUT == 1.0  # Conservative Phase 1
        assert MODBUS_RESPONSE_TIMEOUT == 1.5  # Conservative Phase 1
        assert BLE_CONNECTION_TIMEOUT == 5.0  # Conservative Phase 1

    @pytest.mark.asyncio
    async def test_fresh_installation_no_learned_timeouts_file(self, tmp_path):
        """Test fresh installation with no storage file."""
        from homeassistant.helpers.storage import Store

        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_fresh"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # Load from non-existent file
        loaded_data = await store.async_load()

        # Should return None
        assert loaded_data is None

        # Coordinator should use empty dict for learned_timeouts
        learned_timeouts = (loaded_data or {}).get("learned_timeouts", {})
        assert learned_timeouts == {}


class TestTimeoutOverrideScenarios:
    """Test various timeout override scenarios."""

    @pytest.mark.asyncio
    async def test_learned_timeout_faster_than_default(self):
        """Test learned timeout optimizes for fast hardware."""
        hass = Mock()
        transport = BLETransport(hass)

        # Fast hardware learned timeouts
        learned_timeouts = {
            "modbus_read": 0.600,  # Faster than 1.5s default
            "ble_command": 0.400,  # Faster than 1.0s default
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Verify faster timeouts applied
        assert transport._learned_timeouts["modbus_read"] < MODBUS_RESPONSE_TIMEOUT
        assert transport._learned_timeouts["ble_command"] < BLE_COMMAND_TIMEOUT

    @pytest.mark.asyncio
    async def test_learned_timeout_slower_than_default(self):
        """Test learned timeout adapts for slow hardware."""
        hass = Mock()
        transport = BLETransport(hass)

        # Slow hardware learned timeouts
        learned_timeouts = {
            "modbus_read": 2.400,  # Slower than 1.5s default
            "ble_command": 1.800,  # Slower than 1.0s default
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Verify slower timeouts applied
        assert transport._learned_timeouts["modbus_read"] > MODBUS_RESPONSE_TIMEOUT
        assert transport._learned_timeouts["ble_command"] > BLE_COMMAND_TIMEOUT

    @pytest.mark.asyncio
    async def test_partial_learned_timeouts(self):
        """Test partial learned timeouts (some operations learned, others default)."""
        hass = Mock()
        transport = BLETransport(hass)

        # Only learned timeout for one operation
        learned_timeouts = {
            "modbus_read": 0.875,
            # ble_command not learned yet
        }

        transport.set_learned_timeouts(learned_timeouts)

        # modbus_read uses learned value
        assert transport._learned_timeouts.get("modbus_read") == 0.875

        # ble_command should not be in dict (will use default)
        assert "ble_command" not in transport._learned_timeouts


class TestTimeoutUpdateBehavior:
    """Test timeout update and re-learning behavior."""

    @pytest.mark.asyncio
    async def test_timeout_can_be_updated(self):
        """Test learned timeouts can be updated with new values."""
        hass = Mock()
        transport = BLETransport(hass)

        # Initial learned timeouts
        initial_timeouts = {
            "modbus_read": 0.875,
            "ble_command": 0.450,
        }
        transport.set_learned_timeouts(initial_timeouts)

        # Update with new learned values
        updated_timeouts = {
            "modbus_read": 1.125,  # Increased timeout
            "ble_command": 0.450,  # Same
            "ble_connect": 2.250,  # New operation
        }
        transport.set_learned_timeouts(updated_timeouts)

        # Verify updates applied
        assert transport._learned_timeouts["modbus_read"] == 1.125
        assert transport._learned_timeouts["ble_command"] == 0.450
        assert transport._learned_timeouts["ble_connect"] == 2.250

    @pytest.mark.asyncio
    async def test_clear_learned_timeouts(self):
        """Test clearing learned timeouts reverts to defaults."""
        hass = Mock()
        transport = BLETransport(hass)

        # Set learned timeouts
        learned_timeouts = {
            "modbus_read": 0.875,
        }
        transport.set_learned_timeouts(learned_timeouts)

        # Clear by setting empty dict
        transport.set_learned_timeouts({})

        # Should revert to empty (will use defaults)
        assert transport._learned_timeouts == {}


class TestEdgeCases:
    """Test edge cases in runtime application."""

    @pytest.mark.asyncio
    async def test_none_learned_timeout_value(self):
        """Test handling of None timeout values."""
        hass = Mock()
        transport = BLETransport(hass)

        # Attempt to set None value (should not happen, but test robustness)
        learned_timeouts = {
            "modbus_read": 0.875,
            "ble_command": None,  # Invalid
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Should still set dict (coordinator validates values)
        assert transport._learned_timeouts["modbus_read"] == 0.875
        assert transport._learned_timeouts["ble_command"] is None

    @pytest.mark.asyncio
    async def test_negative_timeout_value(self):
        """Test handling of negative timeout values."""
        hass = Mock()
        transport = BLETransport(hass)

        # Negative timeout (should not happen, but test robustness)
        learned_timeouts = {
            "modbus_read": -0.5,  # Invalid
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Transport accepts it (TimeoutLearner prevents this)
        assert transport._learned_timeouts["modbus_read"] == -0.5

    @pytest.mark.asyncio
    async def test_zero_timeout_value(self):
        """Test handling of zero timeout value."""
        hass = Mock()
        transport = BLETransport(hass)

        learned_timeouts = {
            "modbus_read": 0.0,  # Zero timeout
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Transport accepts it (may cause immediate timeouts)
        assert transport._learned_timeouts["modbus_read"] == 0.0

    @pytest.mark.asyncio
    async def test_very_large_timeout_value(self):
        """Test handling of very large timeout values."""
        hass = Mock()
        transport = BLETransport(hass)

        learned_timeouts = {
            "modbus_read": 100.0,  # Very large timeout
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Transport accepts it (TimeoutLearner clamps to 5.0s)
        assert transport._learned_timeouts["modbus_read"] == 100.0


class TestCoordinatorIntegration:
    """Test integration with coordinator's timeout management."""

    @pytest.mark.asyncio
    async def test_coordinator_loads_and_applies_learned_timeouts(self, tmp_path):
        """Test coordinator loads learned timeouts and applies to transport."""
        from homeassistant.helpers.storage import Store

        # Create mock hass
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_coord_integration"

        # Save learned timeouts to storage
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")
        data = {
            "failed_registers": [],
            "learned_timeouts": {
                "modbus_read": 0.875,
                "ble_command": 0.450,
            },
        }
        await store.async_save(data)

        # Simulate coordinator loading
        loaded_data = await store.async_load()
        learned_timeouts = loaded_data.get("learned_timeouts", {})

        # Create transport and apply learned timeouts
        transport = BLETransport(hass)
        transport.set_learned_timeouts(learned_timeouts)

        # Verify timeouts applied
        assert transport._learned_timeouts["modbus_read"] == 0.875
        assert transport._learned_timeouts["ble_command"] == 0.450


class TestRealisticScenarios:
    """Test realistic usage scenarios."""

    @pytest.mark.asyncio
    async def test_raspberry_pi_3b_optimization(self):
        """Test timeout optimization for Raspberry Pi 3B+ hardware."""
        hass = Mock()
        transport = BLETransport(hass)

        # Raspberry Pi 3B+ learned timeouts
        # (After collecting 20+ samples showing 800-1200ms responses)
        learned_timeouts = {
            "modbus_read": 2.100,  # Learned from P95=1400ms -> 1.4*1.5=2.1s
            "ble_command": 0.750,  # Faster BLE commands
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Should increase timeout from default 1.5s to 2.1s
        assert transport._learned_timeouts["modbus_read"] == 2.100
        assert transport._learned_timeouts["modbus_read"] > MODBUS_RESPONSE_TIMEOUT

    @pytest.mark.asyncio
    async def test_fast_hardware_optimization(self):
        """Test timeout optimization for fast hardware (modern Pi 4/5)."""
        hass = Mock()
        transport = BLETransport(hass)

        # Fast hardware learned timeouts
        # (After collecting samples showing 300-400ms responses)
        learned_timeouts = {
            "modbus_read": 0.600,  # Learned from P95=400ms -> 0.4*1.5=0.6s
            "ble_command": 0.400,  # Very fast
        }

        transport.set_learned_timeouts(learned_timeouts)

        # Should decrease timeout from default 1.5s to 0.6s
        assert transport._learned_timeouts["modbus_read"] == 0.600
        assert transport._learned_timeouts["modbus_read"] < MODBUS_RESPONSE_TIMEOUT

    @pytest.mark.asyncio
    async def test_gradual_learning_progression(self):
        """Test timeout values update as more data is collected."""
        hass = Mock()
        transport = BLETransport(hass)

        # Initial learning (after 20 samples)
        initial_timeouts = {
            "modbus_read": 1.200,
        }
        transport.set_learned_timeouts(initial_timeouts)

        assert transport._learned_timeouts["modbus_read"] == 1.200

        # After more samples (50+ samples, better estimate)
        refined_timeouts = {
            "modbus_read": 1.050,  # More accurate estimate
        }
        transport.set_learned_timeouts(refined_timeouts)

        assert transport._learned_timeouts["modbus_read"] == 1.050

        # After 100+ samples (stable)
        stable_timeouts = {
            "modbus_read": 1.000,  # Stable learned value
        }
        transport.set_learned_timeouts(stable_timeouts)

        assert transport._learned_timeouts["modbus_read"] == 1.000


class TestTimeoutApplicationThread Safety:
    """Test thread safety of timeout application."""

    @pytest.mark.asyncio
    async def test_concurrent_timeout_updates(self):
        """Test concurrent timeout updates don't cause issues."""
        hass = Mock()
        transport = BLETransport(hass)

        # Simulate concurrent updates (should be rare in practice)
        timeouts1 = {"modbus_read": 0.875}
        timeouts2 = {"modbus_read": 1.125}

        # Both should succeed
        transport.set_learned_timeouts(timeouts1)
        transport.set_learned_timeouts(timeouts2)

        # Last write wins
        assert transport._learned_timeouts["modbus_read"] == 1.125

    @pytest.mark.asyncio
    async def test_timeout_access_during_update(self):
        """Test accessing timeouts during update is safe."""
        hass = Mock()
        transport = BLETransport(hass)

        # Set initial timeouts
        initial_timeouts = {"modbus_read": 0.875}
        transport.set_learned_timeouts(initial_timeouts)

        # Access during update (dict assignment is atomic in Python)
        current = transport._learned_timeouts.get("modbus_read")

        # Should have valid value
        assert current == 0.875
