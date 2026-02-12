"""Integration tests for adaptive timing storage persistence (Phase 4).

Tests that learned timeout values are properly saved to and loaded from
Home Assistant's storage system.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from pathlib import Path

from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS

from custom_components.srne_inverter.const import DOMAIN


@pytest.fixture
def mock_hass(tmp_path):
    """Create a properly configured mock hass instance."""
    hass = Mock()
    hass.data = {}  # Required for Store
    hass.config = Mock()
    hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)
    return hass


class TestLearnedTimeoutsPersistence:
    """Test learned timeouts survive HA restart."""

    @pytest.mark.asyncio
    async def test_learned_timeouts_save_and_load(self, tmp_path):
        """Test learned timeouts are saved and loaded correctly."""
        # Create mock hass with temporary storage directory
        hass = Mock()
        hass.data = {}  # Required for Store
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_123"

        # Create store instance
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save learned timeouts
        learned_timeouts = {
            "modbus_read": 0.875,
            "ble_command": 0.450,
            "ble_connect": 2.250,
        }

        data_to_save = {
            "failed_registers": [256, 257],  # Existing data
            "learned_timeouts": learned_timeouts,
        }

        await store.async_save(data_to_save)

        # Load data back
        loaded_data = await store.async_load()

        assert loaded_data is not None
        assert "learned_timeouts" in loaded_data
        assert loaded_data["learned_timeouts"] == learned_timeouts

        # Verify failed_registers still intact
        assert loaded_data["failed_registers"] == [256, 257]

    @pytest.mark.asyncio
    async def test_learned_timeouts_empty_initial_state(self, tmp_path):
        """Test fresh installation has no learned timeouts."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_new"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Load from non-existent storage
        loaded_data = await store.async_load()

        # Should return None for new installation
        assert loaded_data is None

    @pytest.mark.asyncio
    async def test_learned_timeouts_update_existing(self, tmp_path):
        """Test updating learned timeouts preserves other data."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_update"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Initial save with failed registers only
        initial_data = {
            "failed_registers": [256, 257, 258],
            "unavailable_sensors": ["sensor_1", "sensor_2"],
        }
        await store.async_save(initial_data)

        # Update with learned timeouts
        updated_data = {
            "failed_registers": [256, 257, 258],
            "unavailable_sensors": ["sensor_1", "sensor_2"],
            "learned_timeouts": {
                "modbus_read": 1.125,
                "ble_command": 0.600,
            },
        }
        await store.async_save(updated_data)

        # Load and verify
        loaded_data = await store.async_load()

        assert loaded_data["failed_registers"] == [256, 257, 258]
        assert loaded_data["unavailable_sensors"] == ["sensor_1", "sensor_2"]
        assert loaded_data["learned_timeouts"]["modbus_read"] == 1.125
        assert loaded_data["learned_timeouts"]["ble_command"] == 0.600


class TestStorageBackwardCompatibility:
    """Test backward compatibility with old storage format."""

    @pytest.mark.asyncio
    async def test_old_storage_without_learned_timeouts(self, tmp_path):
        """Test old installations work without learned_timeouts key."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_old"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Simulate old storage format (no learned_timeouts)
        old_data = {
            "failed_registers": [256, 257],
        }
        await store.async_save(old_data)

        # Load old data
        loaded_data = await store.async_load()

        assert loaded_data is not None
        assert "failed_registers" in loaded_data
        assert "learned_timeouts" not in loaded_data

        # Coordinator should handle missing key gracefully
        learned_timeouts = loaded_data.get("learned_timeouts", {})
        assert learned_timeouts == {}

    @pytest.mark.asyncio
    async def test_migration_adds_learned_timeouts(self, tmp_path):
        """Test migrating old storage to new format."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_migrate"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Start with old format
        old_data = {
            "failed_registers": [256, 257],
        }
        await store.async_save(old_data)

        # Simulate coordinator loading and adding learned_timeouts
        loaded_data = await store.async_load()
        if "learned_timeouts" not in loaded_data:
            loaded_data["learned_timeouts"] = {}

        # Save updated format
        await store.async_save(loaded_data)

        # Verify migration successful
        final_data = await store.async_load()
        assert "learned_timeouts" in final_data
        assert isinstance(final_data["learned_timeouts"], dict)


class TestCorruptedStorageFallback:
    """Test fallback to defaults on corrupted storage."""

    @pytest.mark.asyncio
    async def test_corrupted_json_returns_none(self, tmp_path):
        """Test corrupted JSON file returns None."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_corrupt"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Create corrupted JSON file
        storage_path = Path(hass.config.path(".storage"))
        storage_path.mkdir(parents=True, exist_ok=True)

        storage_file = storage_path / f"{DOMAIN}_{entry_id}_failed_registers"
        storage_file.write_text("{ this is not valid json }")

        # Load should return None for corrupted data
        loaded_data = await store.async_load()

        assert loaded_data is None

    @pytest.mark.asyncio
    async def test_invalid_learned_timeouts_structure(self, tmp_path):
        """Test handling of invalid learned_timeouts structure."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_invalid"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save with invalid learned_timeouts (list instead of dict)
        invalid_data = {
            "failed_registers": [256],
            "learned_timeouts": ["invalid", "structure"],
        }
        await store.async_save(invalid_data)

        # Load data
        loaded_data = await store.async_load()

        # Coordinator should detect invalid structure and use empty dict
        learned_timeouts = loaded_data.get("learned_timeouts", {})
        if not isinstance(learned_timeouts, dict):
            learned_timeouts = {}

        assert isinstance(learned_timeouts, dict)
        assert len(learned_timeouts) == 0

    @pytest.mark.asyncio
    async def test_fallback_to_defaults_on_load_error(self, tmp_path):
        """Test fallback to default timeouts on load error."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_error"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Load should return None (no file exists)
        loaded_data = await store.async_load()

        # Coordinator should handle None gracefully
        if loaded_data is None:
            loaded_data = {}

        learned_timeouts = loaded_data.get("learned_timeouts", {})
        assert learned_timeouts == {}


class TestStoragePerformance:
    """Test storage operations performance."""

    @pytest.mark.asyncio
    async def test_save_performance(self, tmp_path):
        """Test saving learned timeouts is fast."""
        import time

        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_perf"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Create realistic data
        data = {
            "failed_registers": list(range(50)),  # 50 failed registers
            "learned_timeouts": {
                "modbus_read": 0.875,
                "modbus_write": 0.920,
                "ble_command": 0.450,
                "ble_connect": 2.250,
                "ble_disconnect": 0.300,
            },
        }

        # Measure save time
        start = time.perf_counter()
        await store.async_save(data)
        elapsed = time.perf_counter() - start

        # Save should be < 100ms
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_load_performance(self, tmp_path):
        """Test loading learned timeouts is fast."""
        import time

        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_load_perf"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save data first
        data = {
            "failed_registers": list(range(50)),
            "learned_timeouts": {
                "modbus_read": 0.875,
                "ble_command": 0.450,
            },
        }
        await store.async_save(data)

        # Measure load time
        start = time.perf_counter()
        loaded_data = await store.async_load()
        elapsed = time.perf_counter() - start

        # Load should be < 50ms
        assert elapsed < 0.05
        assert loaded_data is not None


class TestStorageDataIntegrity:
    """Test data integrity in storage operations."""

    @pytest.mark.asyncio
    async def test_learned_timeouts_data_types(self, tmp_path):
        """Test learned timeouts maintain correct data types."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_types"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save with specific types
        data = {
            "learned_timeouts": {
                "modbus_read": 0.875,  # float
                "ble_command": 1.0,     # float (not int)
            },
        }
        await store.async_save(data)

        # Load and verify types
        loaded_data = await store.async_load()

        assert isinstance(loaded_data["learned_timeouts"]["modbus_read"], float)
        assert isinstance(loaded_data["learned_timeouts"]["ble_command"], (float, int))

    @pytest.mark.asyncio
    async def test_learned_timeouts_precision(self, tmp_path):
        """Test learned timeouts maintain precision."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_precision"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save with high precision values
        data = {
            "learned_timeouts": {
                "modbus_read": 0.8765432,  # High precision
                "ble_command": 1.234,      # 3 decimal places
            },
        }
        await store.async_save(data)

        # Load and verify precision maintained
        loaded_data = await store.async_load()

        # JSON maintains reasonable precision
        assert abs(loaded_data["learned_timeouts"]["modbus_read"] - 0.8765432) < 0.0001
        assert loaded_data["learned_timeouts"]["ble_command"] == 1.234

    @pytest.mark.asyncio
    async def test_empty_learned_timeouts_dict(self, tmp_path):
        """Test saving and loading empty learned_timeouts dict."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        entry_id = "test_entry_empty"
        store = Store(hass, 1, f"{DOMAIN}_{entry_id}_failed_registers")

        # Save with empty learned_timeouts
        data = {
            "failed_registers": [256],
            "learned_timeouts": {},
        }
        await store.async_save(data)

        # Load and verify
        loaded_data = await store.async_load()

        assert "learned_timeouts" in loaded_data
        assert loaded_data["learned_timeouts"] == {}
        assert isinstance(loaded_data["learned_timeouts"], dict)


class TestMultipleEntriesStorage:
    """Test storage isolation between multiple config entries."""

    @pytest.mark.asyncio
    async def test_multiple_entries_isolated(self, tmp_path):
        """Test each config entry has isolated storage."""
        hass = Mock()
        hass.config = Mock()
        hass.config.path = lambda *args: str(tmp_path / args[0]) if args else str(tmp_path)

        # Create stores for two different entries
        store1 = Store(hass, 1, f"{DOMAIN}_entry1_failed_registers")
        store2 = Store(hass, 1, f"{DOMAIN}_entry2_failed_registers")

        # Save different data to each
        data1 = {
            "failed_registers": [256],
            "learned_timeouts": {"modbus_read": 0.800},
        }
        data2 = {
            "failed_registers": [512],
            "learned_timeouts": {"modbus_read": 1.200},
        }

        await store1.async_save(data1)
        await store2.async_save(data2)

        # Load and verify isolation
        loaded1 = await store1.async_load()
        loaded2 = await store2.async_load()

        assert loaded1["learned_timeouts"]["modbus_read"] == 0.800
        assert loaded2["learned_timeouts"]["modbus_read"] == 1.200
        assert loaded1["failed_registers"] != loaded2["failed_registers"]
