"""Simplified integration tests for adaptive timing.

Tests core storage and runtime functionality without complex mocking.
"""

import pytest
import tempfile
import json
from pathlib import Path

from custom_components.srne_inverter.application.services.timing_collector import TimingCollector
from custom_components.srne_inverter.application.services.timeout_learner import TimeoutLearner
from custom_components.srne_inverter.infrastructure.transport.ble_transport import BLETransport
from unittest.mock import Mock


class TestStorageSimple:
    """Simple storage tests using manual JSON operations."""

    def test_save_and_load_learned_timeouts(self):
        """Test saving and loading learned timeouts to/from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "learned_timeouts.json"

            # Save learned timeouts
            learned_timeouts = {
                "modbus_read": 0.875,
                "ble_command": 0.450,
            }

            data = {
                "failed_registers": [256, 257],
                "learned_timeouts": learned_timeouts,
            }

            storage_file.write_text(json.dumps(data))

            # Load back
            loaded_data = json.loads(storage_file.read_text())

            assert "learned_timeouts" in loaded_data
            assert loaded_data["learned_timeouts"] == learned_timeouts
            assert loaded_data["failed_registers"] == [256, 257]

    def test_backward_compatibility(self):
        """Test old storage format without learned_timeouts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "old_format.json"

            # Old format (no learned_timeouts)
            old_data = {
                "failed_registers": [256, 257],
            }

            storage_file.write_text(json.dumps(old_data))

            # Load and handle missing key
            loaded_data = json.loads(storage_file.read_text())
            learned_timeouts = loaded_data.get("learned_timeouts", {})

            assert learned_timeouts == {}
            assert "failed_registers" in loaded_data


class TestRuntimeApplicationSimple:
    """Simple runtime application tests."""

    def test_transport_accepts_learned_timeouts(self):
        """Test BLE transport accepts and stores learned timeouts."""
        hass = Mock()
        transport = BLETransport(hass)

        learned_timeouts = {
            "modbus_read": 0.875,
            "ble_command": 0.450,
        }

        transport.set_learned_timeouts(learned_timeouts)

        assert transport._learned_timeouts == learned_timeouts
        assert transport._learned_timeouts["modbus_read"] == 0.875

    def test_transport_empty_learned_timeouts(self):
        """Test transport handles empty learned timeouts."""
        hass = Mock()
        transport = BLETransport(hass)

        transport.set_learned_timeouts({})

        assert transport._learned_timeouts == {}

    def test_transport_updates_learned_timeouts(self):
        """Test transport can update learned timeouts."""
        hass = Mock()
        transport = BLETransport(hass)

        # Initial timeouts
        initial = {"modbus_read": 0.875}
        transport.set_learned_timeouts(initial)

        # Update with new values
        updated = {"modbus_read": 1.125, "ble_command": 0.450}
        transport.set_learned_timeouts(updated)

        assert transport._learned_timeouts["modbus_read"] == 1.125
        assert transport._learned_timeouts["ble_command"] == 0.450


class TestEndToEndSimple:
    """Simplified end-to-end tests."""

    def test_full_learning_cycle_simple(self):
        """Test simplified full learning cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "e2e_test.json"

            # Phase 2: Collect measurements
            collector = TimingCollector(sample_size=100)

            for i in range(25):
                collector.record("modbus_read", 400.0 + i * 10, success=True)

            # Phase 3: Calculate learned timeout
            learner = TimeoutLearner(collector)
            learned_timeout = learner.calculate_timeout("modbus_read")

            assert learned_timeout is not None

            # Phase 4: Save to storage
            learned_timeouts = learner.calculate_all_timeouts()
            data = {"learned_timeouts": learned_timeouts}
            storage_file.write_text(json.dumps(data))

            # Phase 5: Reload and apply
            loaded_data = json.loads(storage_file.read_text())
            reloaded_timeouts = loaded_data["learned_timeouts"]

            hass = Mock()
            transport = BLETransport(hass)
            transport.set_learned_timeouts(reloaded_timeouts)

            # Verify learned timeout applied
            assert transport._learned_timeouts["modbus_read"] == learned_timeout

    def test_fast_hardware_e2e(self):
        """Test E2E for fast hardware."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "fast_hw.json"

            collector = TimingCollector(sample_size=100)

            # Fast responses: 300-400ms
            for i in range(25):
                collector.record("modbus_read", 300.0 + i * 4, success=True)

            learner = TimeoutLearner(collector)
            learned_timeouts = learner.calculate_all_timeouts()

            # Save
            storage_file.write_text(json.dumps({"learned_timeouts": learned_timeouts}))

            # Load and apply
            loaded_data = json.loads(storage_file.read_text())
            hass = Mock()
            transport = BLETransport(hass)
            transport.set_learned_timeouts(loaded_data["learned_timeouts"])

            # Verify optimization (should be < default 1.5s)
            assert transport._learned_timeouts["modbus_read"] < 1.5

    def test_slow_hardware_e2e(self):
        """Test E2E for slow hardware."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = Path(tmpdir) / "slow_hw.json"

            collector = TimingCollector(sample_size=100)

            # Slow responses: 1500-2500ms
            for i in range(25):
                collector.record("modbus_read", 1500.0 + i * 40, success=True)

            learner = TimeoutLearner(collector)
            learned_timeouts = learner.calculate_all_timeouts()

            # Save
            storage_file.write_text(json.dumps({"learned_timeouts": learned_timeouts}))

            # Load and apply
            loaded_data = json.loads(storage_file.read_text())
            hass = Mock()
            transport = BLETransport(hass)
            transport.set_learned_timeouts(loaded_data["learned_timeouts"])

            # Verify adaptation (should be > default 1.5s)
            assert transport._learned_timeouts["modbus_read"] > 1.5
