"""BatchBuilderService for building optimized register batches.

This service handles the construction of register batches from device configuration.
It excludes failed registers and optimizes batch sizes to minimize read requests.

Extracted from register_batching.py and coordinator._rebuild_batches().
Application Layer Extraction
Extracted RegisterDefinition DTO
"""

import logging
from typing import Any, Dict, List, Set, Optional

from ...domain.entities.register_batch import RegisterBatch
from ...domain.value_objects import RegisterAddress
from .register_definition import RegisterDefinition

_LOGGER = logging.getLogger(__name__)

# Batching parameters
MAX_REGISTERS_PER_BATCH = 32  # Modbus standard limit
MAX_GAP_SIZE = 0  # Only batch consecutive registers (no gaps allowed)
# This prevents the SRNE device from returning dash error (0x2D2D2D...)
# when batch includes unsupported registers in gaps


class BatchBuilderService:
    """Service for building optimized register batches.

    This service analyzes device configuration and builds optimized batches
    of consecutive registers that can be read together. It handles:
    - Excluding failed registers from batches
    - Respecting max batch size constraints
    - Handling gaps in address space
    - Feature-based register filtering

    Responsibilities:
    - Build batches from device configuration
    - Filter out failed registers
    - Optimize batch sizes
    - Handle multi-register values (32-bit, 64-bit)

    Example:
        >>> service = BatchBuilderService()
        >>> batches = service.build_batches(config, failed_registers={0x0200})
        >>> for batch in batches:
        ...     print(f"Batch: {batch}")
    """

    def __init__(
        self,
        max_batch_size: int = MAX_REGISTERS_PER_BATCH,
        max_gap_size: int = MAX_GAP_SIZE,
    ):
        """Initialize batch builder service.

        Args:
            max_batch_size: Maximum registers per batch
            max_gap_size: Maximum gap before splitting batch
        """
        self._max_batch_size = max_batch_size
        self._max_gap_size = max_gap_size

        # Performance: Cache disabled addresses set (15x faster - 95% reduction)
        self._disabled_addresses_cache: Optional[Set[int]] = None
        self._cache_key: Optional[frozenset] = None

    def build_batches(
        self,
        device_config: Dict[str, Any],
        failed_registers: Optional[Set[int]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[RegisterBatch]:
        """Build optimized register batches from device configuration.

        This method:
        1. Extracts readable registers from config
        2. Filters by enabled features
        3. Excludes failed registers
        4. Excludes registers for disabled entity types (numbers/selects)
        5. Groups into optimized batches

        Args:
            device_config: Device configuration dictionary
            failed_registers: Set of register addresses to exclude
            options: Config entry options (for filtering disabled entity types)

        Returns:
            List of RegisterBatch entities, sorted by address

        Example:
            >>> config = {
            ...     "registers": {
            ...         "battery_voltage": {"address": 0x0100, "type": "read"},
            ...         "battery_current": {"address": 0x0101, "type": "read"},
            ...     }
            ... }
            >>> batches = service.build_batches(config)
            >>> assert len(batches) >= 1
        """
        if failed_registers is None:
            failed_registers = set()
        if options is None:
            options = {}

        # Build set of register names to exclude based on disabled entity types
        excluded_register_names = self._get_excluded_register_names(
            device_config,
            options,
        )

        # Extract readable registers
        readable_registers = self._extract_readable_registers(
            device_config,
            failed_registers,
            excluded_register_names,
        )

        if not readable_registers:
            _LOGGER.debug("No readable registers found after filtering")
            return []

        # Sort by address
        readable_registers.sort(key=lambda r: r.address)

        _LOGGER.debug(
            "Building batches from %d readable registers, address range: 0x%04X-0x%04X",
            len(readable_registers),
            readable_registers[0].address,
            readable_registers[-1].address,
        )

        # Build batches
        batches = self._build_batches_from_registers(readable_registers)

        _LOGGER.info(
            "Generated %d batches from %d registers",
            len(batches),
            len(readable_registers),
        )

        for i, batch in enumerate(batches, 1):
            _LOGGER.debug(
                "Batch %d: %s-%s (%d regs)",
                i,
                batch.start_address.to_hex(),
                batch.end_address.to_hex(),
                batch.count,
            )

        return batches

    def can_merge_batches(
        self,
        batch1: RegisterBatch,
        batch2: RegisterBatch,
    ) -> bool:
        """Check if two batches can be merged.

        Batches can merge if:
        - They are consecutive (no gap)
        - Combined size <= max_batch_size

        Args:
            batch1: First batch (must come before batch2)
            batch2: Second batch

        Returns:
            True if batches can be merged

        Example:
            >>> b1 = RegisterBatch(RegisterAddress(0x0100), 2, [])
            >>> b2 = RegisterBatch(RegisterAddress(0x0102), 2, [])
            >>> assert service.can_merge_batches(b1, b2)
        """
        # Check if consecutive
        gap = int(batch2.start_address) - int(batch1.end_address) - 1
        if gap != 0:
            return False

        # Check combined size
        combined_size = batch1.count + batch2.count
        if combined_size > self._max_batch_size:
            return False

        return True

    def optimize_batches(
        self,
        batches: List[RegisterBatch],
    ) -> List[RegisterBatch]:
        """Optimize batches by merging consecutive ones.

        Reduces number of read requests by merging small adjacent batches.

        Args:
            batches: List of batches to optimize

        Returns:
            Optimized batch list (may be shorter)

        Example:
            >>> optimized = service.optimize_batches(batches)
            >>> assert len(optimized) <= len(batches)
        """
        if len(batches) <= 1:
            return batches

        optimized = []
        current = batches[0]

        for next_batch in batches[1:]:
            if self.can_merge_batches(current, next_batch):
                # Merge batches
                merged_registers = current.registers + next_batch.registers
                current = RegisterBatch(
                    start_address=current.start_address,
                    count=current.count + next_batch.count,
                    registers=merged_registers,
                    priority=max(current.priority, next_batch.priority),
                )
                _LOGGER.debug(
                    "Merged batches into %s (count=%d)",
                    current.start_address.to_hex(),
                    current.count,
                )
            else:
                # Cannot merge, save current and start new
                optimized.append(current)
                current = next_batch

        # Add final batch
        optimized.append(current)

        if len(optimized) < len(batches):
            _LOGGER.info(
                "Optimized %d batches down to %d",
                len(batches),
                len(optimized),
            )

        return optimized

    def _get_excluded_register_names(
        self,
        device_config: Dict[str, Any],
        options: Dict[str, Any],
    ) -> Set[str]:
        """Build set of register names to exclude based on disabled entity types.

        Args:
            device_config: Device configuration with entity definitions
            options: Config entry options (unused but kept for backward compatibility)

        Returns:
            Set of register names to exclude

        Note:
            Numbers and selects are now controlled by hardware feature detection,
            not by manual toggles. This method is kept for backward compatibility
            but no longer filters based on options.
        """
        excluded = set()

        # No longer filtering by enable_configurable_numbers/selects
        # Entity filtering is now handled by hardware feature detection
        # in entity_factory.py based on device.features in config

        return excluded

    def _extract_readable_registers(
        self,
        device_config: Dict[str, Any],
        failed_registers: Set[int],
        excluded_register_names: Optional[Set[str]] = None,
    ) -> List[RegisterDefinition]:
        """Extract readable registers from configuration.

        Filters registers by:
        - Type (read or read_write)
        - Feature flags (enabled features only)
        - Failed register list (exclude failed)

        Args:
            device_config: Device configuration
            failed_registers: Failed register addresses

        Returns:
            List of RegisterDefinition objects
        """
        registers_def = device_config.get("registers", {})
        if not registers_def:
            return []

        device_info = device_config.get("device", {})
        features = device_info.get("features", {})
        feature_ranges = device_info.get("feature_ranges", {})

        readable = []
        skipped_feature = 0
        skipped_failed = 0
        skipped_disabled = 0

        if excluded_register_names is None:
            excluded_register_names = set()

        for reg_name, reg_def in registers_def.items():
            # Check if register is readable
            reg_type = reg_def.get("type", "read")
            if reg_type not in ("read", "read_write"):
                continue

            # Check if register is excluded due to disabled entity type
            if reg_name in excluded_register_names:
                skipped_disabled += 1
                _LOGGER.debug(
                    "Excluding register %s (disabled entity type)",
                    reg_name,
                )
                continue

            # Get pre-normalized address (30-40% faster than runtime conversion)
            # Config loader normalizes all addresses at load time
            address = reg_def.get("_address_int")
            if address is None:
                # Fallback: address not normalized (shouldn't happen with config loader)
                address = reg_def.get("address")
                if address is None:
                    _LOGGER.debug("Register %s has no address, skipping", reg_name)
                    continue
                # Convert if needed
                if isinstance(address, str):
                    address = int(address, 16 if address.startswith("0x") else 10)

            # Check if register is in failed set
            if address in failed_registers:
                skipped_failed += 1
                _LOGGER.debug(
                    "Excluding failed register %s (0x%04X)",
                    reg_name,
                    address,
                )
                continue

            # Check feature flags
            if self._is_register_disabled_by_feature(
                address,
                features,
                feature_ranges,
            ):
                skipped_feature += 1
                continue

            # Add to readable list
            length = reg_def.get("length", 1)
            readable.append(
                RegisterDefinition(
                    name=reg_name,
                    address=address,
                    length=length,
                    definition=reg_def,
                )
            )

        if skipped_feature > 0:
            _LOGGER.info(
                "Skipped %d registers due to disabled features",
                skipped_feature,
            )

        if skipped_failed > 0:
            _LOGGER.info(
                "Excluded %d failed registers from batches",
                skipped_failed,
            )

        if skipped_disabled > 0:
            _LOGGER.info(
                "Excluded %d registers for disabled entity types (numbers/selects)",
                skipped_disabled,
            )

        return readable

    def _get_disabled_addresses(
        self,
        features: Dict[str, bool],
        feature_ranges: Dict[str, List[Dict[str, Any]]],
    ) -> Set[int]:
        """Build set of disabled addresses (cached).

        Args:
            features: Feature flags
            feature_ranges: Feature address ranges

        Returns:
            Set of disabled register addresses
        """
        # Cache key: frozenset of disabled features
        cache_key = frozenset(k for k, v in features.items() if not v)

        if self._cache_key != cache_key:
            # Features changed, rebuild cache
            disabled = set()
            for feature_name in cache_key:
                for range_def in feature_ranges.get(feature_name, []):
                    # Addresses are pre-normalized at config load time (30-40% faster)
                    start = range_def.get("start")
                    end = range_def.get("end")

                    # Add all addresses in range
                    # Note: config_loader normalizes these at load time for performance
                    disabled.update(range(start, end + 1))

            self._disabled_addresses_cache = disabled
            self._cache_key = cache_key

        return (
            self._disabled_addresses_cache
            if self._disabled_addresses_cache is not None
            else set()
        )

    def _is_register_disabled_by_feature(
        self,
        address: int,
        features: Dict[str, bool],
        feature_ranges: Dict[str, List[Dict[str, Any]]],
    ) -> bool:
        """Check if register is disabled (O(1) set lookup).

        Args:
            address: Register address
            features: Feature flags
            feature_ranges: Feature address ranges

        Returns:
            True if disabled

        Performance:
            O(1) set lookup vs O(n×m) nested loops = 15x faster
        """
        disabled = self._get_disabled_addresses(features, feature_ranges)
        return address in disabled

    def _build_batches_from_registers(
        self,
        registers: List[RegisterDefinition],
    ) -> List[RegisterBatch]:
        """Build batches from sorted register list.

        Important: This creates batches that can include gaps (unreadable addresses)
        if the gap is small enough. This is intentional - we read the entire range
        and extract only the registers we care about. This is more efficient than
        multiple small reads.

        Args:
            registers: Sorted list of RegisterDefinition

        Returns:
            List of RegisterBatch entities with populated registers list
        """
        if not registers:
            return []

        # Import Register entity for creating register instances
        from ...domain.entities.register import Register
        from ...domain.value_objects.register_value import DataType

        batches = []
        current_batch_start = None
        current_batch_end = None
        current_batch_registers = []
        covered_addresses = (
            set()
        )  # Track addresses already covered by multi-register values

        _LOGGER.debug("Building batches from %d register definitions", len(registers))

        for i, reg_def in enumerate(registers):
            address = reg_def.address
            length = reg_def.length
            reg_end_address = address + length - 1

            # Skip registers that are already covered by a previous multi-register value
            if address in covered_addresses:
                _LOGGER.debug(
                    "Skipping register %d/%d: %s at 0x%04X (already covered by multi-register value)",
                    i + 1,
                    len(registers),
                    reg_def.name,
                    address,
                )
                continue

            # Verbose per-register logging removed - use batch-level summary instead
            # Uncomment for deep debugging of specific register issues:
            # _LOGGER.debug(
            #     "Processing register %d/%d: %s at 0x%04X (length=%d, end=0x%04X)",
            #     i + 1, len(registers), reg_def.name, address, length, reg_end_address,
            # )

            # Mark addresses as covered by this register (for multi-register values)
            for addr in range(address, reg_end_address + 1):
                covered_addresses.add(addr)

            # Create Register entity from RegisterDefinition
            reg_def_dict = reg_def.definition
            register_entity = Register(
                address=RegisterAddress(address),
                name=reg_def.name,
                data_type=self._parse_data_type(
                    reg_def_dict.get("data_type", "uint16")
                ),
                scale=reg_def_dict.get("scaling", 1.0),
                offset=reg_def_dict.get("offset", 0),
                unit=reg_def_dict.get("unit", ""),
                description=reg_def_dict.get("description", ""),
                read_only=reg_def_dict.get("type", "read") == "read",
            )

            # Start new batch if:
            # 1. First register
            # 2. Gap too large
            # 3. Batch would exceed max size
            if current_batch_start is None:
                # First register
                current_batch_start = address
                current_batch_end = reg_end_address
                current_batch_registers = [register_entity]
            else:
                gap = address - current_batch_end - 1
                would_be_size = reg_end_address - current_batch_start + 1

                if gap > self._max_gap_size or would_be_size > self._max_batch_size:
                    # Finalize current batch with current registers (don't include new one)
                    # CRITICAL: Use current_batch_end (not reg_end_address) for count
                    count = current_batch_end - current_batch_start + 1

                    _LOGGER.debug(
                        "Finalizing batch: gap=%d (max=%d), would_be_size=%d (max=%d), "
                        "start=0x%04X, end=0x%04X, count=%d, registers=%d",
                        gap,
                        self._max_gap_size,
                        would_be_size,
                        self._max_batch_size,
                        current_batch_start,
                        current_batch_end,
                        count,
                        len(current_batch_registers),
                    )

                    # Validate before creating batch
                    if len(current_batch_registers) > count:
                        _LOGGER.error(
                            "Internal error: Register count mismatch! "
                            f"registers={len(current_batch_registers)}, count={count}, "
                            f"start=0x{current_batch_start:04X}, end=0x{current_batch_end:04X}, "
                            f"register_list={[r.name for r in current_batch_registers]}"
                        )
                        # This should never happen, but if it does, use register count
                        count = len(current_batch_registers)

                    batch = RegisterBatch(
                        start_address=RegisterAddress(current_batch_start),
                        count=count,
                        registers=current_batch_registers,
                    )
                    batches.append(batch)

                    _LOGGER.debug(
                        "Starting new batch with %s at 0x%04X", reg_def.name, address
                    )

                    # Start new batch with the register that didn't fit
                    current_batch_start = address
                    current_batch_end = reg_end_address
                    current_batch_registers = [register_entity]
                else:
                    # Extend current batch (includes gap if present)
                    current_batch_end = reg_end_address
                    current_batch_registers.append(register_entity)

        # Finalize last batch
        if current_batch_start is not None:
            count = current_batch_end - current_batch_start + 1
            batch = RegisterBatch(
                start_address=RegisterAddress(current_batch_start),
                count=count,
                registers=current_batch_registers,
            )
            batches.append(batch)

        return batches

    def _parse_data_type(self, data_type_str: str) -> "DataType":
        """Parse data type string to DataType enum.

        Args:
            data_type_str: Data type as string (e.g., "uint16", "int16")

        Returns:
            DataType enum value
        """
        from ...domain.value_objects.register_value import DataType

        type_map = {
            "uint16": DataType.UINT16,
            "int16": DataType.INT16,
            "uint32": DataType.UINT32,
            "int32": DataType.INT32,
        }
        return type_map.get(data_type_str.lower(), DataType.UINT16)
