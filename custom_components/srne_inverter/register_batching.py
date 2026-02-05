"""Automatic register batching for optimized Modbus reads.

This module analyzes register definitions from device configuration and
automatically generates optimized batch read operations.
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Batching parameters
MAX_REGISTERS_PER_BATCH = 32  # Modbus standard limit
MAX_GAP_SIZE = 5  # Maximum gap between registers before splitting batch


class RegisterBatch:
    """Represents a single batch read operation."""

    def __init__(
        self,
        start_address: int,
        count: int,
        register_map: dict[int, str],
    ) -> None:
        """Initialize a register batch.

        Args:
            start_address: Starting register address
            count: Number of registers to read
            register_map: Mapping of offset -> register_name
        """
        self.start_address = start_address
        self.count = count
        self.register_map = register_map  # {offset: register_name}

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"RegisterBatch(0x{self.start_address:04X}, "
            f"count={self.count}, fields={len(self.register_map)})"
        )


def build_register_batches(config: dict[str, Any]) -> list[RegisterBatch]:
    """Build optimized register batches from device configuration.

    Args:
        config: Device configuration dict with 'registers' section

    Returns:
        List of RegisterBatch objects, sorted by address
    """
    registers_def = config.get("registers", {})
    if not registers_def:
        _LOGGER.debug("No registers defined in configuration")
        return []

    device_config = config.get("device", {})
    features = device_config.get("features", {})
    feature_ranges = device_config.get("feature_ranges", {})

    readable_registers = []
    skipped_feature_registers = 0

    for reg_name, reg_def in registers_def.items():
        reg_type = reg_def.get("type", "read")
        if reg_type in ("read", "read_write"):
            address = reg_def.get("address")
            if address is None:
                _LOGGER.debug("Register %s has no address, skipping", reg_name)
                continue

            if isinstance(address, str):
                address = int(address, 16 if address.startswith("0x") else 10)

            skip_register = False
            for feature_name, ranges in feature_ranges.items():
                feature_enabled = features.get(feature_name, True)

                if not feature_enabled:
                    for range_def in ranges:
                        start_addr = range_def.get("start")
                        end_addr = range_def.get("end")

                        # Convert hex to int if needed
                        if isinstance(start_addr, str):
                            start_addr = int(start_addr, 16 if start_addr.startswith("0x") else 10)
                        if isinstance(end_addr, str):
                            end_addr = int(end_addr, 16 if end_addr.startswith("0x") else 10)

                        if start_addr <= address <= end_addr:
                            skip_register = True
                            skipped_feature_registers += 1
                            _LOGGER.debug(
                                "Skipping register %s (0x%04X) - requires disabled feature '%s'",
                                reg_name,
                                address,
                                feature_name,
                            )
                            break

                if skip_register:
                    break

            if skip_register:
                continue

            length = reg_def.get("length", 1)

            readable_registers.append(
                {
                    "name": reg_name,
                    "address": address,
                    "length": length,  # Number of consecutive registers
                    "definition": reg_def,
                }
            )

    if not readable_registers:
        _LOGGER.debug("No readable registers found")
        return []

    # Sort by address
    readable_registers.sort(key=lambda r: r["address"])

    if skipped_feature_registers > 0:
        _LOGGER.info(
            "Skipped %d registers due to disabled features (not supported by this inverter model)",
            skipped_feature_registers,
        )

    _LOGGER.debug(
        "Found %d readable registers, address range: 0x%04X-0x%04X",
        len(readable_registers),
        readable_registers[0]["address"],
        readable_registers[-1]["address"],
    )

    # Build batches
    batches = []
    current_batch_start = None
    current_batch_registers = {}
    last_address = None

    for reg_info in readable_registers:
        address = reg_info["address"]
        reg_name = reg_info["name"]
        length = reg_info["length"]

        # Calculate the ending address for this register (accounting for multi-register)
        reg_end_address = address + length - 1

        # Start new batch if:
        # 1. First register
        # 2. Gap too large
        # 3. Batch would exceed MAX_REGISTERS_PER_BATCH
        if current_batch_start is None:
            # First register - start new batch
            current_batch_start = address
            current_batch_registers = {0: reg_name}
            last_address = reg_end_address

        else:
            gap = address - last_address - 1
            batch_size = reg_end_address - current_batch_start + 1

            if gap > MAX_GAP_SIZE or batch_size > MAX_REGISTERS_PER_BATCH:
                # Finalize current batch
                count = last_address - current_batch_start + 1
                batches.append(
                    RegisterBatch(current_batch_start, count, current_batch_registers)
                )

                # Start new batch
                current_batch_start = address
                current_batch_registers = {0: reg_name}
                last_address = reg_end_address
            else:
                # Add to current batch
                offset = address - current_batch_start
                current_batch_registers[offset] = reg_name
                last_address = reg_end_address

    # Finalize last batch
    if current_batch_start is not None:
        count = last_address - current_batch_start + 1
        batches.append(
            RegisterBatch(current_batch_start, count, current_batch_registers)
        )

    _LOGGER.info(
        "Generated %d batches from %d registers", len(batches), len(readable_registers)
    )
    for i, batch in enumerate(batches, 1):
        _LOGGER.debug(
            "Batch %d: 0x%04X-0x%04X (%d regs, %d mapped)",
            i,
            batch.start_address,
            batch.start_address + batch.count - 1,
            batch.count,
            len(batch.register_map),
        )

    return batches


def extract_batch_data(
    batch: RegisterBatch,
    values: list[int],
    registers_def: dict[str, Any],
    to_signed_fn: callable,
) -> dict[str, Any]:
    """Extract data from batch read response.

    Args:
        batch: RegisterBatch that was read
        values: Raw register values from Modbus response
        registers_def: Register definitions from config
        to_signed_fn: Function to convert uint16 to int16

    Returns:
        Dict of register_name -> scaled_value
    """
    data = {}
    processed_offsets = set()  # Track which offsets we've consumed

    for offset, reg_name in batch.register_map.items():
        # Skip if already processed as part of multi-register value
        if offset in processed_offsets:
            continue

        if offset >= len(values):
            _LOGGER.debug(
                "Offset %d for register %s exceeds response length %d",
                offset,
                reg_name,
                len(values),
            )
            continue

        reg_def = registers_def.get(reg_name, {})
        length = reg_def.get("length", 1)

        # Handle multi-register values (32-bit, 64-bit, etc.)
        if length > 1:
            # Combine multiple registers into single value
            if offset + length > len(values):
                _LOGGER.debug(
                    "Multi-register value %s (length=%d) at offset %d exceeds response length %d",
                    reg_name,
                    length,
                    offset,
                    len(values),
                )
                continue

            # Combine registers: high word first (big-endian)
            raw_value = 0
            for i in range(length):
                raw_value = (raw_value << 16) | values[offset + i]
                processed_offsets.add(offset + i)

        else:
            # Single register value
            raw_value = values[offset]
            processed_offsets.add(offset)

            # Handle signed conversion for 16-bit values
            data_type = reg_def.get("data_type", "uint16")
            if data_type == "int16":
                raw_value = to_signed_fn(raw_value)

        # Apply scaling
        scaling = reg_def.get("scaling", 1)
        if scaling != 1:
            scaled_value = raw_value * scaling
        else:
            scaled_value = raw_value

        data[reg_name] = scaled_value

    return data
