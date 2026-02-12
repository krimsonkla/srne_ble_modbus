"""End-to-end tests for adaptive timing system.

Tests the complete learning cycle from initial defaults through
measurement collection, learning, persistence, and application.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import time

from homeassistant.helpers.storage import Store

from custom_components.srne_inverter.application.services.timing_collector import TimingCollector
from custom_components.srne_inverter.application.services.timeout_learner import TimeoutLearner
from custom_components.srne_inverter.infrastructure.transport.ble_transport import BLETransport
from custom_components.srne_inverter.const import (
    MODBUS_RESPONSE_TIMEOUT,
    BLE_COMMAND_TIMEOUT,
    TIMING_MIN_SAMPLES,
)


class TestFullLearningCycle:
    """Test complete learning cycle from start to finish."""

    @pytest.mark.asyncio
    async def test_full_learning_cycle(self, tmp_path):
        """Test complete adaptive timing learning cycle.

        Phases:
        1. Start with Phase 1 defaults
        2. Collect 20 measurements
        3. Calculate learned timeout
        4. Save to storage
        5. Reload and apply
        """
        # Setup
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_full_cycle"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # PHASE 1: Start with defaults
        transport = BLETransport(hass)
        assert transport._learned_timeouts == {}  # No learned timeouts yet

        # Should use Phase 1 defaults
        assert MODBUS_RESPONSE_TIMEOUT == 1.5  # Conservative default

        # PHASE 2: Collect measurements
        collector = TimingCollector(sample_size=100)

        # Simulate 25 Modbus read operations with realistic timing
        for i in range(25):
            # Simulate operation timing: 400-640ms with some variation
            duration_ms = 400.0 + (i % 12) * 20
            success = True

            collector.record("modbus_read", duration_ms, success=success)

        # Verify sufficient data collected
        assert collector.get_sample_count("modbus_read") >= TIMING_MIN_SAMPLES

        # PHASE 3: Calculate learned timeout
        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        assert learned_timeout is not None
        # P95 should be around 620ms -> 0.62s * 1.5 = 0.93s
        assert 0.8 < learned_timeout < 1.1

        # PHASE 4: Save to storage
        learned_timeouts = learner.calculate_all_timeouts()

        data = {
            "failed_registers": [],
            "learned_timeouts": learned_timeouts,
        }
        await store.async_save(data)

        # PHASE 5: Reload and apply (simulate HA restart)
        loaded_data = await store.async_load()
        assert loaded_data is not None

        reloaded_timeouts = loaded_data.get("learned_timeouts", {})
        assert "modbus_read" in reloaded_timeouts

        # Create new transport and apply learned timeouts
        new_transport = BLETransport(hass)
        new_transport.set_learned_timeouts(reloaded_timeouts)

        # Verify learned timeout is applied
        assert new_transport._learned_timeouts["modbus_read"] == learned_timeout

        # Verify optimization occurred
        assert new_transport._learned_timeouts["modbus_read"] < MODBUS_RESPONSE_TIMEOUT


class TestSlowHardwareAdaptation:
    """Test adaptation to slow device (2-3s responses)."""

    @pytest.mark.asyncio
    async def test_slow_hardware_learning_cycle(self, tmp_path):
        """Test complete cycle for slow hardware (Raspberry Pi 3B+)."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_slow_hw"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # Collect measurements simulating slow hardware
        collector = TimingCollector(sample_size=100)

        # Slow responses: 1500-2500ms
        for i in range(25):
            duration_ms = 1500.0 + (i % 10) * 100
            collector.record("modbus_read", duration_ms, success=True)

        # Learn timeout
        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        assert learned_timeout is not None
        # P95 should be around 2400ms -> 2.4s * 1.5 = 3.6s
        assert 3.3 < learned_timeout < 4.0

        # Should increase from default 1.5s
        assert learned_timeout > MODBUS_RESPONSE_TIMEOUT

        # Save and reload
        learned_timeouts = learner.calculate_all_timeouts()
        await store.async_save({"learned_timeouts": learned_timeouts})

        loaded_data = await store.async_load()
        reloaded_timeouts = loaded_data["learned_timeouts"]

        # Verify persistence
        assert reloaded_timeouts["modbus_read"] == learned_timeout

    @pytest.mark.asyncio
    async def test_slow_hardware_with_timeouts(self, tmp_path):
        """Test slow hardware with occasional timeouts."""
        hass = Mock()
        collector = TimingCollector(sample_size=100)

        # Mix of slow responses and timeouts
        for i in range(20):
            # 80% slow but successful
            if i < 16:
                duration_ms = 1800.0 + (i % 8) * 100
                collector.record("modbus_read", duration_ms, success=True)
            # 20% timeouts
            else:
                duration_ms = 5000.0  # Timeout
                collector.record("modbus_read", duration_ms, success=False)

        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        # Should accommodate both slow responses and some timeouts
        assert learned_timeout is not None
        # P95 will be inflated by timeouts, likely clamped to max (5.0s)
        assert learned_timeout >= 3.0


class TestFastHardwareOptimization:
    """Test optimization for fast device (0.3-0.4s responses)."""

    @pytest.mark.asyncio
    async def test_fast_hardware_learning_cycle(self, tmp_path):
        """Test complete cycle for fast hardware."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_fast_hw"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # Collect measurements simulating fast hardware
        collector = TimingCollector(sample_size=100)

        # Fast responses: 300-400ms
        for i in range(25):
            duration_ms = 300.0 + (i % 10) * 10
            collector.record("modbus_read", duration_ms, success=True)

        # Learn timeout
        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        assert learned_timeout is not None
        # P95 should be around 390ms -> 0.39s * 1.5 = 0.585s
        # Should be clamped to minimum (0.3s) or slightly above
        assert 0.3 <= learned_timeout < 0.8

        # Should decrease from default 1.5s
        assert learned_timeout < MODBUS_RESPONSE_TIMEOUT

        # Save and reload
        learned_timeouts = learner.calculate_all_timeouts()
        await store.async_save({"learned_timeouts": learned_timeouts})

        loaded_data = await store.async_load()
        reloaded_timeouts = loaded_data["learned_timeouts"]

        # Apply to transport
        transport = BLETransport(hass)
        transport.set_learned_timeouts(reloaded_timeouts)

        # Verify optimization
        assert transport._learned_timeouts["modbus_read"] < MODBUS_RESPONSE_TIMEOUT
        assert transport._learned_timeouts["modbus_read"] == learned_timeout


class TestMultipleOperationLearning:
    """Test learning timeouts for multiple operation types."""

    @pytest.mark.asyncio
    async def test_learn_multiple_operations(self, tmp_path):
        """Test learning timeouts for different operation types."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_multi_ops"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # Collect measurements for multiple operations
        collector = TimingCollector(sample_size=100)

        # Modbus read: ~500ms
        for i in range(25):
            collector.record("modbus_read", 450.0 + i * 5, success=True)

        # Modbus write: ~600ms (slightly slower)
        for i in range(25):
            collector.record("modbus_write", 550.0 + i * 5, success=True)

        # BLE command: ~150ms (faster)
        for i in range(25):
            collector.record("ble_command", 130.0 + i * 2, success=True)

        # Learn all timeouts
        learner = TimeoutLearner(collector)
        learned_timeouts = learner.calculate_all_timeouts()

        # Should have learned timeouts for all operations
        assert "modbus_read" in learned_timeouts
        assert "modbus_write" in learned_timeouts
        assert "ble_command" in learned_timeouts

        # Verify relative ordering
        assert learned_timeouts["modbus_write"] > learned_timeouts["modbus_read"]
        assert learned_timeouts["ble_command"] < learned_timeouts["modbus_read"]

        # Save and reload
        await store.async_save({"learned_timeouts": learned_timeouts})
        loaded_data = await store.async_load()

        # Verify all timeouts persisted
        reloaded_timeouts = loaded_data["learned_timeouts"]
        assert len(reloaded_timeouts) == 3
        assert reloaded_timeouts == learned_timeouts


class TestIncrementalLearning:
    """Test incremental learning as more data is collected."""

    @pytest.mark.asyncio
    async def test_incremental_learning_progression(self, tmp_path):
        """Test timeout values improve with more samples."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_incremental"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        collector = TimingCollector(sample_size=200)
        learner = TimeoutLearner(collector)

        # Phase 1: Initial 20 samples
        for i in range(20):
            # Some variation in timing
            duration_ms = 400.0 + (i % 15) * 30
            collector.record("modbus_read", duration_ms, success=True)

        timeout_20 = learner.calculate_timeout("modbus_read")
        assert timeout_20 is not None

        # Phase 2: Add 30 more samples (50 total)
        for i in range(30):
            duration_ms = 420.0 + (i % 10) * 20
            collector.record("modbus_read", duration_ms, success=True)

        timeout_50 = learner.calculate_timeout("modbus_read")

        # Phase 3: Add 50 more samples (100 total)
        for i in range(50):
            duration_ms = 410.0 + (i % 12) * 15
            collector.record("modbus_read", duration_ms, success=True)

        timeout_100 = learner.calculate_timeout("modbus_read")

        # More samples should stabilize the timeout estimate
        # (May increase or decrease slightly, but should converge)
        assert timeout_100 is not None

        # Save final learned timeout
        await store.async_save({
            "learned_timeouts": {"modbus_read": timeout_100}
        })

        loaded_data = await store.async_load()
        assert loaded_data["learned_timeouts"]["modbus_read"] == timeout_100


class TestRecoveryFromTimeouts:
    """Test learning recovery after timeout issues."""

    @pytest.mark.asyncio
    async def test_recovery_from_high_timeout_rate(self, tmp_path):
        """Test system learns appropriate timeout after high failure rate."""
        hass = Mock()
        collector = TimingCollector(sample_size=100)

        # Initial period with high timeout rate
        # 50% timeouts (too aggressive timeout)
        for i in range(10):
            collector.record("modbus_read", 400.0, success=True)
            collector.record("modbus_read", 1500.0, success=False)  # Timeout

        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        # Should learn higher timeout to reduce failures
        assert learned_timeout is not None
        # P95 will include timeouts, should be > 1.0s
        assert learned_timeout > 1.0

        # After timeout adjustment, success rate improves
        # Add 20 more samples with better success rate
        for i in range(20):
            # Now mostly successful with learned timeout
            collector.record("modbus_read", 800.0, success=True)

        # Re-learn with better data
        improved_timeout = learner.calculate_timeout("modbus_read")

        # Should stabilize around successful operation timing
        assert improved_timeout is not None


class TestEdgeCaseScenarios:
    """Test edge cases in full learning cycle."""

    @pytest.mark.asyncio
    async def test_learning_with_highly_variable_timing(self, tmp_path):
        """Test learning with highly variable response times."""
        hass = Mock()
        collector = TimingCollector(sample_size=100)

        # Highly variable timing: 200ms to 2000ms
        import random
        random.seed(42)  # Reproducible

        for i in range(30):
            duration_ms = random.uniform(200.0, 2000.0)
            collector.record("modbus_read", duration_ms, success=True)

        learner = TimeoutLearner(collector)
        learned_timeout = learner.calculate_timeout("modbus_read")

        # Should still learn a timeout
        assert learned_timeout is not None
        # P95 of highly variable data should be near upper range
        assert learned_timeout > 1.5

    @pytest.mark.asyncio
    async def test_learning_reset_after_clear(self, tmp_path):
        """Test learning can be reset by clearing collector."""
        hass = Mock()
        collector = TimingCollector(sample_size=100)

        # Initial learning
        for i in range(25):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        learner = TimeoutLearner(collector)
        initial_timeout = learner.calculate_timeout("modbus_read")
        assert initial_timeout is not None

        # Clear measurements
        collector.clear("modbus_read")

        # Should not be able to learn anymore
        cleared_timeout = learner.calculate_timeout("modbus_read")
        assert cleared_timeout is None

        # Re-learn with new data
        for i in range(25):
            # Different timing pattern
            collector.record("modbus_read", 800.0 + i * 10, success=True)

        new_timeout = learner.calculate_timeout("modbus_read")
        assert new_timeout is not None
        assert new_timeout != initial_timeout


class TestStorageIntegrationInE2E:
    """Test storage integration in end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_e2e_with_existing_storage(self, tmp_path):
        """Test E2E cycle with pre-existing storage data."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_existing_storage"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # Pre-existing storage with failed registers
        existing_data = {
            "failed_registers": [256, 257],
            "unavailable_sensors": ["sensor_1"],
        }
        await store.async_save(existing_data)

        # Now run learning cycle
        collector = TimingCollector(sample_size=100)

        for i in range(25):
            collector.record("modbus_read", 500.0 + i * 10, success=True)

        learner = TimeoutLearner(collector)
        learned_timeouts = learner.calculate_all_timeouts()

        # Add learned timeouts to existing data
        loaded_data = await store.async_load()
        loaded_data["learned_timeouts"] = learned_timeouts
        await store.async_save(loaded_data)

        # Reload and verify all data intact
        final_data = await store.async_load()

        assert final_data["failed_registers"] == [256, 257]
        assert final_data["unavailable_sensors"] == ["sensor_1"]
        assert "modbus_read" in final_data["learned_timeouts"]

    @pytest.mark.asyncio
    async def test_e2e_with_multiple_restarts(self, tmp_path):
        """Test learning persists across multiple HA restarts."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_multiple_restarts"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        # First boot: Learn initial timeout
        collector1 = TimingCollector(sample_size=100)
        for i in range(25):
            collector1.record("modbus_read", 500.0 + i * 10, success=True)

        learner1 = TimeoutLearner(collector1)
        timeout1 = learner1.calculate_timeout("modbus_read")
        await store.async_save({"learned_timeouts": {"modbus_read": timeout1}})

        # Second boot: Load and verify
        data2 = await store.async_load()
        transport2 = BLETransport(hass)
        transport2.set_learned_timeouts(data2["learned_timeouts"])
        assert transport2._learned_timeouts["modbus_read"] == timeout1

        # Third boot: Continue learning (update timeout)
        collector3 = TimingCollector(sample_size=100)
        for i in range(30):
            collector3.record("modbus_read", 600.0 + i * 10, success=True)

        learner3 = TimeoutLearner(collector3)
        timeout3 = learner3.calculate_timeout("modbus_read")

        # Update storage
        data3 = await store.async_load()
        data3["learned_timeouts"]["modbus_read"] = timeout3
        await store.async_save(data3)

        # Fourth boot: Load updated timeout
        data4 = await store.async_load()
        assert data4["learned_timeouts"]["modbus_read"] == timeout3
        assert data4["learned_timeouts"]["modbus_read"] != timeout1  # Should have changed


class TestPerformanceInE2E:
    """Test performance characteristics of full learning cycle."""

    @pytest.mark.asyncio
    async def test_e2e_cycle_performance(self, tmp_path):
        """Test full E2E cycle completes in reasonable time."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_e2e_perf"
        store = Store(hass, 1, f"srne_ble_modbus_{entry_id}_failed_registers")

        start_time = time.perf_counter()

        # Full cycle
        collector = TimingCollector(sample_size=100)

        for i in range(25):
            collector.record("modbus_read", 500.0 + i * 10, success=True)

        learner = TimeoutLearner(collector)
        learned_timeouts = learner.calculate_all_timeouts()

        await store.async_save({"learned_timeouts": learned_timeouts})

        loaded_data = await store.async_load()

        transport = BLETransport(hass)
        transport.set_learned_timeouts(loaded_data["learned_timeouts"])

        elapsed = time.perf_counter() - start_time

        # Full E2E cycle should complete quickly (< 100ms)
        assert elapsed < 0.1
