"""Tests for BatchBuilderService.

Comprehensive test coverage for batch building logic including:
- Basic batch building
- Failed register exclusion
- Feature-based filtering
- Gap handling
- Batch optimization
- Edge cases
"""

import pytest
from custom_components.srne_inverter.application.services.batch_builder_service import (
    BatchBuilderService,
    RegisterDefinition,
)
from custom_components.srne_inverter.domain.entities.register_batch import RegisterBatch
from custom_components.srne_inverter.domain.value_objects import RegisterAddress


class TestBatchBuilderService:
    """Test suite for BatchBuilderService."""

    @pytest.fixture
    def service(self):
        """Create service instance with default parameters."""
        return BatchBuilderService(
            max_batch_size=32,
            max_gap_size=5,
        )

    @pytest.fixture
    def simple_config(self):
        """Simple device configuration with 4 consecutive registers."""
        return {
            "registers": {
                "battery_voltage": {
                    "address": 0x0100,
                    "type": "read",
                    "length": 1,
                },
                "battery_current": {
                    "address": 0x0101,
                    "type": "read",
                    "length": 1,
                },
                "battery_soc": {
                    "address": 0x0102,
                    "type": "read",
                    "length": 1,
                },
                "battery_temp": {
                    "address": 0x0103,
                    "type": "read",
                    "length": 1,
                },
            }
        }

    @pytest.fixture
    def config_with_gaps(self):
        """Configuration with gaps in address space."""
        return {
            "registers": {
                "reg1": {"address": 0x0100, "type": "read", "length": 1},
                "reg2": {"address": 0x0101, "type": "read", "length": 1},
                # Gap of 6 registers (exceeds max_gap_size=5)
                "reg3": {"address": 0x0108, "type": "read", "length": 1},
                "reg4": {"address": 0x0109, "type": "read", "length": 1},
            }
        }

    @pytest.fixture
    def config_with_features(self):
        """Configuration with feature flags."""
        return {
            "device": {
                "features": {
                    "pv_charging": True,  # Enabled
                    "ac_charging": False,  # Disabled
                },
                "feature_ranges": {"ac_charging": [{"start": 0x0200, "end": 0x0210}]},
            },
            "registers": {
                "pv_voltage": {"address": 0x0100, "type": "read", "length": 1},
                "pv_current": {"address": 0x0101, "type": "read", "length": 1},
                "ac_voltage": {"address": 0x0200, "type": "read", "length": 1},
                "ac_current": {"address": 0x0201, "type": "read", "length": 1},
            },
        }

    # ========================================================================
    # Basic Functionality Tests
    # ========================================================================

    def test_build_batches_simple(self, service, simple_config):
        """Test building batches from simple consecutive registers."""
        batches = service.build_batches(simple_config)

        # Should create 1 batch for 4 consecutive registers
        assert len(batches) == 1

        batch = batches[0]
        assert int(batch.start_address) == 0x0100
        assert batch.count == 4
        assert int(batch.end_address) == 0x0103

    def test_build_batches_with_gaps(self, service, config_with_gaps):
        """Test that large gaps split batches."""
        batches = service.build_batches(config_with_gaps)

        # Gap of 6 exceeds max_gap_size=5, should split
        assert len(batches) == 2

        # First batch: 0x0100-0x0101
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 2

        # Second batch: 0x0108-0x0109
        assert int(batches[1].start_address) == 0x0108
        assert batches[1].count == 2

    def test_build_batches_empty_config(self, service):
        """Test with empty configuration."""
        config = {"registers": {}}
        batches = service.build_batches(config)

        assert batches == []

    def test_build_batches_no_registers_key(self, service):
        """Test with config missing registers key."""
        config = {}
        batches = service.build_batches(config)

        assert batches == []

    # ========================================================================
    # Failed Register Exclusion Tests
    # ========================================================================

    def test_build_batches_exclude_failed(self, service, simple_config):
        """Test that failed registers are excluded from batches.

        NOTE: Failed registers create gaps, but small gaps (<=5) are included
        in the batch range. The batch will read the entire range 0x0100-0x0103,
        but the coordinator will only extract data from 0x0100 and 0x0103.
        This is more efficient than splitting into multiple small batches.
        """
        failed_registers = {0x0101, 0x0102}
        batches = service.build_batches(simple_config, failed_registers)

        # Gap of 2 is within max_gap_size=5, so stays in one batch
        assert len(batches) == 1

        # Batch covers entire range including gap
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 4  # 0x0100-0x0103 inclusive

    def test_build_batches_all_failed(self, service, simple_config):
        """Test when all registers are failed."""
        failed_registers = {0x0100, 0x0101, 0x0102, 0x0103}
        batches = service.build_batches(simple_config, failed_registers)

        assert batches == []

    def test_build_batches_failed_at_start(self, service, simple_config):
        """Test when first register is failed."""
        failed_registers = {0x0100}
        batches = service.build_batches(simple_config, failed_registers)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0101
        assert batches[0].count == 3

    def test_build_batches_failed_at_end(self, service, simple_config):
        """Test when last register is failed."""
        failed_registers = {0x0103}
        batches = service.build_batches(simple_config, failed_registers)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 3

    # ========================================================================
    # Feature-Based Filtering Tests
    # ========================================================================

    def test_build_batches_with_disabled_features(self, service, config_with_features):
        """Test that registers in disabled feature ranges are excluded."""
        batches = service.build_batches(config_with_features)

        # Should only include PV registers (0x0100-0x0101)
        # AC registers (0x0200-0x0201) should be excluded
        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 2

    def test_build_batches_all_features_enabled(self, service, config_with_features):
        """Test when all features are enabled."""
        # Enable AC charging
        config_with_features["device"]["features"]["ac_charging"] = True
        batches = service.build_batches(config_with_features)

        # Should have 2 batches: PV and AC
        assert len(batches) == 2

        assert int(batches[0].start_address) == 0x0100
        assert int(batches[1].start_address) == 0x0200

    # ========================================================================
    # Register Type Filtering Tests
    # ========================================================================

    def test_build_batches_write_only_excluded(self, service):
        """Test that write-only registers are excluded."""
        config = {
            "registers": {
                "readable": {"address": 0x0100, "type": "read", "length": 1},
                "writable": {"address": 0x0101, "type": "write", "length": 1},
                "rw": {"address": 0x0102, "type": "read_write", "length": 1},
            }
        }
        batches = service.build_batches(config)

        # Only read and read_write should be included
        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 3  # Includes the gap at 0x0101

    def test_build_batches_invalid_address(self, service):
        """Test handling of registers with missing addresses."""
        config = {
            "registers": {
                "valid": {"address": 0x0100, "type": "read", "length": 1},
                "invalid": {"type": "read", "length": 1},  # No address
                "valid2": {"address": 0x0101, "type": "read", "length": 1},
            }
        }
        batches = service.build_batches(config)

        # Invalid register should be skipped
        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 2

    # ========================================================================
    # Multi-Register Value Tests
    # ========================================================================

    def test_build_batches_multi_register_values(self, service):
        """Test handling of multi-register values (32-bit, 64-bit)."""
        config = {
            "registers": {
                "single": {"address": 0x0100, "type": "read", "length": 1},
                "double": {"address": 0x0101, "type": "read", "length": 2},
                "quad": {"address": 0x0103, "type": "read", "length": 4},
            }
        }
        batches = service.build_batches(config)

        # Should create 1 batch: 0x0100 (1) + 0x0101-0x0102 (2) + 0x0103-0x0106 (4) = 7 registers
        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 7

    # ========================================================================
    # Batch Size Limit Tests
    # ========================================================================

    def test_build_batches_respects_max_size(self):
        """Test that batches respect max_batch_size limit."""
        service = BatchBuilderService(max_batch_size=4, max_gap_size=5)

        # Create 10 consecutive registers
        config = {
            "registers": {
                f"reg_{i}": {"address": 0x0100 + i, "type": "read", "length": 1}
                for i in range(10)
            }
        }
        batches = service.build_batches(config)

        # Should split into multiple batches of max 4 registers
        assert len(batches) >= 3  # 10 / 4 = 2.5, rounds to 3

        for batch in batches:
            assert batch.count <= 4

    def test_build_batches_large_consecutive_block(self, service):
        """Test batching large consecutive block."""
        # Create 100 consecutive registers
        config = {
            "registers": {
                f"reg_{i}": {"address": 0x0100 + i, "type": "read", "length": 1}
                for i in range(100)
            }
        }
        batches = service.build_batches(config)

        # Should split into batches of max_batch_size=32
        assert len(batches) >= 4  # 100 / 32 = 3.125, rounds to 4

        total_registers = sum(b.count for b in batches)
        assert total_registers == 100

    # ========================================================================
    # Batch Merging Tests
    # ========================================================================

    def test_can_merge_batches_consecutive(self, service):
        """Test that consecutive batches can merge."""
        batch1 = RegisterBatch(
            start_address=RegisterAddress(0x0100),
            count=2,
            registers=[],
        )
        batch2 = RegisterBatch(
            start_address=RegisterAddress(0x0102),
            count=2,
            registers=[],
        )

        assert service.can_merge_batches(batch1, batch2)

    def test_can_merge_batches_with_gap(self, service):
        """Test that batches with gap cannot merge."""
        batch1 = RegisterBatch(
            start_address=RegisterAddress(0x0100),
            count=2,
            registers=[],
        )
        batch2 = RegisterBatch(
            start_address=RegisterAddress(0x0103),  # Gap at 0x0102
            count=2,
            registers=[],
        )

        assert not service.can_merge_batches(batch1, batch2)

    def test_can_merge_batches_exceeds_max_size(self, service):
        """Test that batches cannot merge if combined size exceeds max."""
        batch1 = RegisterBatch(
            start_address=RegisterAddress(0x0100),
            count=20,
            registers=[],
        )
        batch2 = RegisterBatch(
            start_address=RegisterAddress(0x0114),
            count=20,
            registers=[],
        )

        # Combined size = 40, exceeds max_batch_size=32
        assert not service.can_merge_batches(batch1, batch2)

    def test_optimize_batches_merges_small_batches(self, service):
        """Test that optimize_batches merges small consecutive batches."""
        batches = [
            RegisterBatch(RegisterAddress(0x0100), 2, []),
            RegisterBatch(RegisterAddress(0x0102), 2, []),
            RegisterBatch(RegisterAddress(0x0104), 2, []),
        ]

        optimized = service.optimize_batches(batches)

        # Should merge into 1 batch
        assert len(optimized) == 1
        assert int(optimized[0].start_address) == 0x0100
        assert optimized[0].count == 6

    def test_optimize_batches_preserves_gaps(self, service):
        """Test that optimize_batches preserves gaps."""
        batches = [
            RegisterBatch(RegisterAddress(0x0100), 2, []),
            RegisterBatch(RegisterAddress(0x0110), 2, []),  # Large gap
        ]

        optimized = service.optimize_batches(batches)

        # Should not merge due to gap
        assert len(optimized) == 2

    def test_optimize_batches_single_batch(self, service):
        """Test optimize_batches with single batch."""
        batches = [RegisterBatch(RegisterAddress(0x0100), 4, [])]

        optimized = service.optimize_batches(batches)

        assert len(optimized) == 1
        assert optimized[0] == batches[0]

    def test_optimize_batches_empty_list(self, service):
        """Test optimize_batches with empty list."""
        optimized = service.optimize_batches([])

        assert optimized == []

    # ========================================================================
    # Hex Address Handling Tests
    # ========================================================================

    def test_build_batches_hex_string_addresses(self, service):
        """Test handling of hex string addresses in config."""
        config = {
            "registers": {
                "reg1": {"address": "0x0100", "type": "read", "length": 1},
                "reg2": {"address": "0x0101", "type": "read", "length": 1},
            }
        }
        batches = service.build_batches(config)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100

    def test_build_batches_decimal_string_addresses(self, service):
        """Test handling of decimal string addresses."""
        config = {
            "registers": {
                "reg1": {"address": "256", "type": "read", "length": 1},  # 0x0100
                "reg2": {"address": "257", "type": "read", "length": 1},  # 0x0101
            }
        }
        batches = service.build_batches(config)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 256

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_build_batches_single_register(self, service):
        """Test with single register."""
        config = {
            "registers": {
                "only": {"address": 0x0100, "type": "read", "length": 1},
            }
        }
        batches = service.build_batches(config)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 1

    def test_build_batches_maximum_address(self, service):
        """Test with maximum register address."""
        config = {
            "registers": {
                "max": {"address": 0xFFFF, "type": "read", "length": 1},
            }
        }
        batches = service.build_batches(config)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0xFFFF

    def test_build_batches_minimum_address(self, service):
        """Test with minimum register address."""
        config = {
            "registers": {
                "min": {"address": 0x0000, "type": "read", "length": 1},
            }
        }
        batches = service.build_batches(config)

        assert len(batches) == 1
        assert int(batches[0].start_address) == 0x0000

    def test_build_batches_exact_max_gap(self, service):
        """Test with gap exactly equal to max_gap_size."""
        config = {
            "registers": {
                "reg1": {"address": 0x0100, "type": "read", "length": 1},
                "reg2": {"address": 0x0106, "type": "read", "length": 1},  # Gap = 5
            }
        }
        batches = service.build_batches(config)

        # Gap of 5 equals max_gap_size, should stay in same batch
        assert len(batches) == 1
        assert batches[0].count == 7  # 0x0100-0x0106 inclusive

    def test_build_batches_gap_exceeds_by_one(self, service):
        """Test with gap exceeding max_gap_size by 1."""
        config = {
            "registers": {
                "reg1": {"address": 0x0100, "type": "read", "length": 1},
                "reg2": {"address": 0x0107, "type": "read", "length": 1},  # Gap = 6
            }
        }
        batches = service.build_batches(config)

        # Gap of 6 exceeds max_gap_size=5, should split
        assert len(batches) == 2

    # ========================================================================
    # Statistics and Logging Tests
    # ========================================================================

    def test_build_batches_logs_statistics(self, service, simple_config, caplog):
        """Test that build_batches logs useful statistics."""
        import logging

        caplog.set_level(logging.INFO)

        service.build_batches(simple_config)

        assert "Generated 1 batches from 4 registers" in caplog.text

    def test_build_batches_logs_failed_exclusions(self, service, simple_config, caplog):
        """Test that failed register exclusions are logged."""
        import logging

        caplog.set_level(logging.INFO)

        failed_registers = {0x0101, 0x0102}
        service.build_batches(simple_config, failed_registers)

        assert "Excluded 2 failed registers" in caplog.text


# ========================================================================
# Integration Tests
# ========================================================================


class TestBatchBuilderIntegration:
    """Integration tests with realistic scenarios."""

    @pytest.fixture
    def realistic_config(self):
        """Realistic SRNE inverter configuration."""
        return {
            "device": {
                "features": {
                    "pv_charging": True,
                    "ac_charging": False,
                },
                "feature_ranges": {
                    "ac_charging": [{"start": "0xE200", "end": "0xE210"}]
                },
            },
            "registers": {
                # Battery registers (consecutive)
                "battery_voltage": {"address": "0x0100", "type": "read", "length": 1},
                "battery_current": {"address": "0x0101", "type": "read", "length": 1},
                "battery_soc": {"address": "0x0102", "type": "read", "length": 1},
                "battery_temp": {"address": "0x0103", "type": "read", "length": 1},
                # PV registers (consecutive)
                "pv_voltage": {"address": "0x0107", "type": "read", "length": 1},
                "pv_current": {"address": "0x0108", "type": "read", "length": 1},
                "pv_power": {"address": "0x0109", "type": "read", "length": 2},
                # Output registers (large gap)
                "output_voltage": {"address": "0x0200", "type": "read", "length": 1},
                "output_current": {"address": "0x0201", "type": "read", "length": 1},
                "output_frequency": {"address": "0x0202", "type": "read", "length": 1},
                # AC charging registers (disabled feature)
                "ac_input_voltage": {"address": "0xE200", "type": "read", "length": 1},
                "ac_input_current": {"address": "0xE201", "type": "read", "length": 1},
            },
        }

    def test_realistic_scenario(self, realistic_config):
        """Test with realistic SRNE inverter configuration."""
        service = BatchBuilderService()

        batches = service.build_batches(realistic_config)

        # With MAX_GAP_SIZE=0, no gaps allowed (SRNE device requirement)
        # Gap between battery (0x0103) and PV (0x0107) causes split
        # Should have 3 batches:
        # 1. Battery (0x0100-0x0103, 4 registers)
        # 2. PV (0x0107-0x010A, 4 registers)
        # 3. Output (0x0200-0x0202, 3 registers)
        # AC registers excluded due to disabled feature

        assert len(batches) == 3

        # Verify batch ranges
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 4  # Battery consecutive only
        assert int(batches[1].start_address) == 0x0107
        assert batches[1].count == 4  # PV consecutive only
        assert int(batches[2].start_address) == 0x0200
        assert batches[2].count == 3

    def test_realistic_with_failed_registers(self, realistic_config):
        """Test realistic scenario with some failed registers."""
        service = BatchBuilderService()

        # Simulate failed registers
        failed = {0x0102, 0x0108}  # battery_soc, pv_current

        batches = service.build_batches(realistic_config, failed)

        # With MAX_GAP_SIZE=0, failed registers create splits
        # Remaining registers: 0x0100, 0x0101, 0x0103, 0x0107, 0x0109, 0x010A, 0x0200-0x0202
        # No gaps allowed, so we get 5 batches:
        # 1. Battery (0x0100-0x0101, 2 registers)
        # 2. Battery (0x0103, 1 register)
        # 3. PV (0x0107, 1 register)
        # 4. PV (0x0109-0x010A, 2 registers)
        # 5. Output (0x0200-0x0202, 3 registers)

        assert len(batches) == 5
        assert int(batches[0].start_address) == 0x0100
        assert batches[0].count == 2
        assert int(batches[1].start_address) == 0x0103
        assert batches[1].count == 1
        assert int(batches[2].start_address) == 0x0107
        assert batches[2].count == 1
        assert int(batches[3].start_address) == 0x0109
        assert batches[3].count == 2
        assert int(batches[4].start_address) == 0x0200
        assert batches[4].count == 3
