# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""DataUpdateCoordinator for SRNE Inverter BLE communication.

This coordinator manages:
- BLE connection lifecycle
- Modbus RTU protocol over BLE
- Command spacing enforcement
- Data polling and state management
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BATCH_READ_DELAY,
    BLE_NOTIFY_UUID,
    BLE_WRITE_UUID,
    COMMAND_DELAY,
    COMMAND_DELAY_WRITE,
    DEFAULT_SLAVE_ID,
    DOMAIN,
    FUNC_READ_HOLDING,
    FUNC_WRITE_SINGLE,
    MODBUS_ERROR_CODES,
)
from .register_batching import build_register_batches, extract_batch_data

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# MODBUS PROTOCOL IMPLEMENTATION
# ============================================================================


class ModbusProtocol:
    """Modbus RTU protocol implementation for BLE communication."""

    @staticmethod
    def calculate_crc16(data: bytes) -> int:
        """Calculate Modbus CRC-16."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    @classmethod
    def build_read_command(cls, slave_id: int, register: int, count: int = 1) -> bytes:
        """Build Modbus Read Holding Registers (0x03) command."""
        data = struct.pack(">BBHH", slave_id, FUNC_READ_HOLDING, register, count)
        crc = cls.calculate_crc16(data)
        return data + struct.pack("<H", crc)

    @classmethod
    def build_write_command(cls, slave_id: int, register: int, value: int) -> bytes:
        """Build Modbus Write Single Register (0x06) command."""
        data = struct.pack(">BBHH", slave_id, FUNC_WRITE_SINGLE, register, value)
        crc = cls.calculate_crc16(data)
        return data + struct.pack("<H", crc)

    @classmethod
    def decode_response(cls, data: bytes) -> dict[str, Any] | None:
        """Decode Modbus response with 8-byte BLE header.

        Response format: [8-byte header][Modbus RTU frame with CRC]
        """
        if len(data) < 13:  # Minimum: 8 header + 5 Modbus frame
            _LOGGER.debug("Response too short: %d bytes", len(data))
            return None

        # Skip 8-byte header
        if data[:8] == b"\x00" * 8:
            modbus_frame = data[8:]
        else:
            modbus_frame = data

        if len(modbus_frame) < 5:
            _LOGGER.debug("Modbus frame too short: %d bytes", len(modbus_frame))
            return None

        # Verify CRC
        received_crc = struct.unpack("<H", modbus_frame[-2:])[0]
        calculated_crc = cls.calculate_crc16(modbus_frame[:-2])

        if received_crc != calculated_crc:
            _LOGGER.debug(
                "CRC mismatch: received=0x%04X, calculated=0x%04X",
                received_crc,
                calculated_crc,
            )
            return None

        slave_addr = modbus_frame[0]
        function_code = modbus_frame[1]

        # Check for error response
        if function_code & 0x80:
            error_code = modbus_frame[2]
            _LOGGER.debug("Modbus exception: 0x%02X", error_code)
            return {"error": error_code}

        # Decode read response
        if function_code == FUNC_READ_HOLDING:
            byte_count = modbus_frame[2]
            values = []
            for i in range(0, byte_count, 2):
                value = struct.unpack(">H", modbus_frame[3 + i : 5 + i])[0]
                values.append(value)
            return {
                "slave_addr": slave_addr,
                "function": function_code,
                "values": values,
            }

        # Decode write response
        if function_code == FUNC_WRITE_SINGLE:
            register = struct.unpack(">H", modbus_frame[2:4])[0]
            value = struct.unpack(">H", modbus_frame[4:6])[0]
            return {
                "slave_addr": slave_addr,
                "function": function_code,
                "register": register,
                "value": value,
            }

        return None


# ============================================================================
# DATA UPDATE COORDINATOR
# ============================================================================


class SRNEDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for SRNE Inverter data updates via BLE."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, device_config: dict[str, Any]
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            device_config: Device configuration with registers
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),  # Optimized for ~9s avg update time
        )

        self._address = entry.data["address"]
        self._ble_device: BLEDevice | None = None
        self._client: BleakClient | None = None
        self._notification_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10)
        self._last_command_time = 0.0
        self._command_lock = asyncio.Lock()
        self._write_queue: asyncio.Queue[tuple[int, int]] = asyncio.Queue(maxsize=20)
        self._write_task: asyncio.Task | None = None

        # Exponential backoff for reconnection
        self._backoff_time = 1.0
        self._max_backoff = 60.0
        self._last_connection_attempt = 0.0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 20

        # Diagnostic tracking
        self._update_start_time: float | None = None
        self._total_updates: int = 0
        self._failed_reads: int = 0

        # Device configuration and dynamic batching
        self._device_config = device_config
        self._entry = entry
        self._failed_registers: set[int] = set()
        self._batches_need_rebuild = False

        # Dependency tracking for calculated sensors
        self._dependency_map: dict[str, list[str]] = {}
        self._unavailable_sensors: set[str] = set()
        self._build_dependency_map()

        # Build initial batches (will be rebuilt after loading failed registers)
        self._register_batches = build_register_batches(device_config)

        _LOGGER.info(
            "Initialized coordinator for device %s with %d register batches",
            self._address,
            len(self._register_batches),
        )

    async def _load_failed_registers(self) -> None:
        """Load previously failed registers and unavailable sensors from storage."""
        store = Store(
            self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers"
        )

        try:
            data = await store.async_load()
            if data:
                # Load failed registers
                if "failed_registers" in data:
                    self._failed_registers = set(data["failed_registers"])
                    _LOGGER.info(
                        "Loaded %d failed registers from storage: %s",
                        len(self._failed_registers),
                        [f"0x{r:04X}" for r in sorted(self._failed_registers)],
                    )
                    self._rebuild_batches()
                    self._log_dependency_diagnostics()

                if "unavailable_sensors" in data:
                    self._unavailable_sensors = set(data["unavailable_sensors"])
                    if self._unavailable_sensors:
                        _LOGGER.debug(
                            "Loaded %d unavailable sensors from storage: %s",
                            len(self._unavailable_sensors),
                            list(self._unavailable_sensors),
                        )
        except Exception as err:
            _LOGGER.debug("No previous failed registers found: %s", err)
            self._failed_registers = set()
            self._unavailable_sensors = set()

    def _rebuild_batches(self) -> None:
        """Rebuild register batches excluding known failed registers."""
        if not self._failed_registers:
            return

        # Filter device config to exclude failed registers
        filtered_config = self._device_config.copy()
        filtered_registers = {}

        for reg_name, reg_def in self._device_config.get("registers", {}).items():
            address = reg_def.get("address")
            if isinstance(address, str):
                address = int(address, 16 if address.startswith("0x") else 10)

            # Skip if this register is in failed set
            if address not in self._failed_registers:
                filtered_registers[reg_name] = reg_def
            else:
                _LOGGER.debug(
                    "Excluding failed register %s (0x%04X) from batches",
                    reg_name,
                    address,
                )

        filtered_config["registers"] = filtered_registers

        # Rebuild batches with filtered config
        self._register_batches = build_register_batches(filtered_config)

        _LOGGER.info(
            "Rebuilt %d register batches excluding %d failed registers",
            len(self._register_batches),
            len(self._failed_registers),
        )

    def _build_dependency_map(self) -> None:
        """Build reverse dependency map for tracking calculated sensor dependencies."""
        self._dependency_map = {}

        for sensor in self._device_config.get("sensors", []):
            if sensor.get("source_type") == "calculated":
                entity_id = sensor.get("entity_id")
                depends_on = sensor.get("depends_on", [])

                for dep_key in depends_on:
                    if dep_key not in self._dependency_map:
                        self._dependency_map[dep_key] = []
                    self._dependency_map[dep_key].append(entity_id)

        _LOGGER.debug(
            "Built dependency map with %d data keys tracking %d calculated sensors",
            len(self._dependency_map),
            sum(len(v) for v in self._dependency_map.values()),
        )

    def _get_unavailable_sensors(self) -> list[str]:
        """Get list of calculated sensors with missing dependencies."""
        unavailable = set()

        # Check all calculated sensors
        for sensor in self._device_config.get("sensors", []):
            if sensor.get("source_type") == "calculated":
                entity_id = sensor.get("entity_id")
                depends_on = sensor.get("depends_on", [])

                for dep_key in depends_on:
                    if dep_key not in self.data:
                        unavailable.add(entity_id)
                        _LOGGER.debug(
                            "Sensor %s unavailable: missing dependency '%s'",
                            entity_id,
                            dep_key,
                        )
                        break

        return list(unavailable)

    def is_register_failed(self, register_name: str) -> bool:
        """Check if a register has failed and should be hidden.

        Args:
            register_name: Register name (e.g., 'output_frequency')

        Returns:
            True if register is in failed set, False otherwise
        """
        # Get register address
        reg_def = self._device_config.get("registers", {}).get(register_name)
        if not reg_def:
            return False

        address = reg_def.get("address")
        if isinstance(address, str):
            address = int(address, 16 if address.startswith("0x") else 10)

        return address in self._failed_registers

    def is_entity_unavailable(self, entity_id: str) -> bool:
        """Check if entity is unavailable due to missing dependencies."""
        return entity_id in self._unavailable_sensors

    def _log_dependency_diagnostics(self) -> None:
        """Log diagnostic information about failed registers and affected sensors."""
        if not self._failed_registers:
            return

        affected_sensors_by_register = {}

        for reg_name, reg_def in self._device_config.get("registers", {}).items():
            address = reg_def.get("address")
            if isinstance(address, str):
                address = int(address, 16 if address.startswith("0x") else 10)

            if address in self._failed_registers:
                affected_sensors = self._dependency_map.get(reg_name, [])
                if affected_sensors:
                    affected_sensors_by_register[f"{reg_name} (0x{address:04X})"] = affected_sensors

        if affected_sensors_by_register:
            _LOGGER.debug(
                "Failed registers impact %d calculated sensors:",
                len(set(s for sensors in affected_sensors_by_register.values() for s in sensors)),
            )
            for reg, sensors in affected_sensors_by_register.items():
                _LOGGER.debug(
                    "  Register %s affects sensors: %s",
                    reg,
                    ", ".join(sensors),
                )
        else:
            _LOGGER.info(
                "%d failed registers found, but no calculated sensors are affected",
                len(self._failed_registers),
            )

    async def _save_failed_registers(self) -> None:
        """Save failed registers and unavailable sensors to storage."""
        store = Store(
            self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers"
        )
        try:
            unavailable_sensors = self._get_unavailable_sensors() if self.data else []
            self._unavailable_sensors = set(unavailable_sensors)

            await store.async_save({
                "failed_registers": list(self._failed_registers),
                "unavailable_sensors": unavailable_sensors,
            })

            _LOGGER.info(
                "Saved %d failed registers to storage: %s",
                len(self._failed_registers),
                [f"0x{r:04X}" for r in sorted(self._failed_registers)],
            )

            if unavailable_sensors:
                _LOGGER.debug(
                    "%d calculated sensors unavailable due to missing dependencies: %s",
                    len(unavailable_sensors),
                    unavailable_sensors,
                )

            self._rebuild_batches()
            self._log_dependency_diagnostics()
        except Exception as err:
            _LOGGER.error("Failed to save failed registers: %s", err)

    async def clear_failed_registers(self) -> None:
        """Clear failed register cache and force re-scan of all registers."""
        store = Store(
            self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers"
        )

        try:
            await store.async_remove()

            old_count = len(self._failed_registers)
            self._failed_registers.clear()
            self._unavailable_sensors.clear()

            _LOGGER.info(
                "Cleared %d failed registers from cache. All registers will be re-scanned.",
                old_count
            )

            self._rebuild_batches()

            _LOGGER.info(
                "Rebuilt %d register batches for full re-scan",
                len(self._register_batches)
            )

            await self.async_refresh()

            _LOGGER.info("Register re-scan initiated successfully")

        except Exception as err:
            _LOGGER.error("Failed to clear failed registers: %s", err)
            raise

    async def _split_and_retry_batch(
        self, batch_start: int, batch_count: int, register_map: dict[int, str], split_depth: int = 0
    ) -> dict[str, Any]:
        """Split failed batch and retry smaller chunks to isolate unsupported registers.

        Args:
            batch_start: Starting register address
            batch_count: Number of registers in batch
            register_map: Mapping of offset -> register name
            split_depth: Current recursion depth

        Returns:
            Dictionary of successfully read register data
        """
        if split_depth > 10:
            _LOGGER.error(
                "Batch split depth exceeded 10 for 0x%04X (count=%d), aborting",
                batch_start,
                batch_count,
            )
            failed_registers = [batch_start + i for i in range(batch_count)]
            self._failed_registers.update(failed_registers)
            _LOGGER.debug(
                "Marking %d registers as failed: %s",
                len(failed_registers),
                [f"0x{r:04X}" for r in failed_registers],
            )
            return {}
        if batch_count <= 4:
            data = {}
            failed_in_batch = []

            for offset in range(batch_count):
                register_addr = batch_start + offset

                if register_addr in self._failed_registers:
                    _LOGGER.debug("Skipping known failed register 0x%04X", register_addr)
                    continue

                await asyncio.sleep(BATCH_READ_DELAY)

                if self._client is None or not self._client.is_connected:
                    _LOGGER.debug(
                        "BLE connection lost during batch splitting at register 0x%04X. Returning partial data.",
                        register_addr,
                    )
                    break

                try:
                    result = await self._read_register(register_addr, count=1)
                    if result and "values" in result and "error" not in result:
                        from .register_batching import RegisterBatch, extract_batch_data

                        single_batch = RegisterBatch(register_addr, 1, {0: register_map.get(offset, f"reg_0x{register_addr:04X}")})
                        batch_data = extract_batch_data(
                            single_batch,
                            result["values"],
                            self._device_config.get("registers", {}),
                            self._to_signed_int16,
                        )
                        data.update(batch_data)
                        _LOGGER.debug("Register 0x%04X read successfully", register_addr)
                    elif result is None:
                        if self._client is None or not self._client.is_connected:
                            _LOGGER.debug(
                                "BLE connection lost at register 0x%04X. Stopping batch split.",
                                register_addr,
                            )
                            break
                        else:
                            _LOGGER.debug("Register 0x%04X failed", register_addr)
                            failed_in_batch.append(register_addr)
                    else:
                        _LOGGER.debug("Register 0x%04X failed", register_addr)
                        failed_in_batch.append(register_addr)
                except (EOFError, BleakError) as err:
                    _LOGGER.debug(
                        "BLE connection error reading register 0x%04X: %s. Returning partial data.",
                        register_addr,
                        err,
                    )
                    failed_in_batch.append(register_addr)
                    break

            if failed_in_batch:
                self._failed_registers.update(failed_in_batch)
                _LOGGER.info(
                    "Marking %d registers as failed: %s",
                    len(failed_in_batch),
                    [f"0x{r:04X}" for r in failed_in_batch],
                )
                await self._save_failed_registers()

            return data

        mid_point = batch_count // 2
        _LOGGER.debug(
            "Splitting batch 0x%04X (count=%d) at position %d (depth=%d)",
            batch_start,
            batch_count,
            mid_point,
            split_depth,
        )

        data = {}
        first_half_map = {
            k: v for k, v in register_map.items() if k < mid_point
        }
        if first_half_map:
            try:
                await asyncio.sleep(BATCH_READ_DELAY)
                first_result = await self._read_register(batch_start, count=mid_point)
                if first_result and "values" in first_result and "error" not in first_result:
                    # Success - extract data
                    from .register_batching import RegisterBatch, extract_batch_data

                    first_batch = RegisterBatch(batch_start, mid_point, first_half_map)
                    batch_data = extract_batch_data(
                        first_batch,
                        first_result["values"],
                        self._device_config.get("registers", {}),
                        self._to_signed_int16,
                    )
                    data.update(batch_data)
                    _LOGGER.debug(
                        "First half succeeded: 0x%04X (count=%d)", batch_start, mid_point
                    )
                else:
                    # First half failed - recurse
                    _LOGGER.debug("First half failed, splitting further")
                    first_data = await self._split_and_retry_batch(
                        batch_start, mid_point, first_half_map, split_depth + 1
                    )
                    data.update(first_data)
            except (EOFError, BleakError) as err:
                # Graceful disconnect handling
                _LOGGER.debug(
                    "BLE connection error in first half (0x%04X, count=%d): %s. Returning partial data.",
                    batch_start,
                    mid_point,
                    err,
                )
                # Mark all registers in first half as failed
                failed_registers = [batch_start + i for i in range(mid_point)]
                self._failed_registers.update(failed_registers)
                # Continue to second half

        # Try second half with graceful error handling
        second_half_start = batch_start + mid_point
        second_half_count = batch_count - mid_point
        second_half_map = {
            k - mid_point: v for k, v in register_map.items() if k >= mid_point
        }
        if second_half_map:
            try:
                await asyncio.sleep(BATCH_READ_DELAY)
                second_result = await self._read_register(
                    second_half_start, count=second_half_count
                )
                if second_result and "values" in second_result and "error" not in second_result:
                    # Success - extract data
                    from .register_batching import RegisterBatch, extract_batch_data

                    second_batch = RegisterBatch(
                        second_half_start, second_half_count, second_half_map
                    )
                    batch_data = extract_batch_data(
                        second_batch,
                        second_result["values"],
                        self._device_config.get("registers", {}),
                        self._to_signed_int16,
                    )
                    data.update(batch_data)
                    _LOGGER.debug(
                        "Second half succeeded: 0x%04X (count=%d)",
                        second_half_start,
                        second_half_count,
                    )
                else:
                    # Second half failed - recurse
                    _LOGGER.debug("Second half failed, splitting further")
                    second_data = await self._split_and_retry_batch(
                        second_half_start, second_half_count, second_half_map, split_depth + 1
                    )
                    data.update(second_data)
            except (EOFError, BleakError) as err:
                # Graceful disconnect handling
                _LOGGER.debug(
                    "BLE connection error in second half (0x%04X, count=%d): %s. Returning partial data.",
                    second_half_start,
                    second_half_count,
                    err,
                )
                # Mark all registers in second half as failed
                failed_registers = [second_half_start + i for i in range(second_half_count)]
                self._failed_registers.update(failed_registers)

        return data

    @staticmethod
    def _to_signed_int16(value: int) -> int:
        """Convert unsigned 16-bit int to signed.

        Args:
            value: Unsigned 16-bit integer (0-65535)

        Returns:
            Signed 16-bit integer (-32768 to 32767)
        """
        if value >= 0x8000:
            return value - 0x10000
        return value

    def _clear_notification_queue(self) -> None:
        """Clear all items from notification queue."""
        while not self._notification_queue.empty():
            try:
                self._notification_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from inverter using batch reads.

        Batches are generated from register definitions in YAML.
        """
        self._update_start_time = time.time()

        try:
            _LOGGER.debug("Ensuring BLE connection to %s", self._address)
            if not await self._ensure_connection():
                raise UpdateFailed(
                    f"Failed to establish BLE connection to {self._address}"
                )

            data = {}
            registers_def = self._device_config.get("registers", {})

            # Process each batch
            for i, batch in enumerate(self._register_batches, 1):
                _LOGGER.debug(
                    "Reading batch %d/%d: 0x%04X-0x%04X (%d registers)",
                    i,
                    len(self._register_batches),
                    batch.start_address,
                    batch.start_address + batch.count - 1,
                    batch.count,
                )

                # Read batch
                result = await self._read_register(
                    batch.start_address, count=batch.count
                )

                if result and "values" in result and "error" not in result:
                    values = result["values"]

                    batch_data = extract_batch_data(
                        batch, values, registers_def, self._to_signed_int16
                    )

                    data.update(batch_data)

                    _LOGGER.debug(
                        "Batch %d extracted %d values: %s",
                        i,
                        len(batch_data),
                        list(batch_data.keys()),
                    )
                else:
                    _LOGGER.debug(
                        "Batch %d read failed: 0x%04X (count=%d), splitting and retrying...",
                        i,
                        batch.start_address,
                        batch.count,
                    )
                    self._failed_reads += 1

                    split_data = await self._split_and_retry_batch(
                        batch.start_address, batch.count, batch.register_map, split_depth=0
                    )
                    if split_data:
                        data.update(split_data)
                        _LOGGER.info(
                            "Batch splitting recovered %d values from failed batch",
                            len(split_data),
                        )
                    else:
                        _LOGGER.debug(
                            "Batch splitting found no valid registers in batch %d", i
                        )

            data["connected"] = True
            fault_codes = [
                data.get("fault_code_0", 0),
                data.get("fault_code_1", 0),
                data.get("fault_code_2", 0),
                data.get("fault_code_3", 0),
            ]
            data["fault_detected"] = any(code != 0 for code in fault_codes)
            data["fault_bits"] = fault_codes

            # Add diagnostic metrics
            from datetime import datetime, timezone

            update_duration = time.time() - self._update_start_time
            self._total_updates += 1
            data["update_duration"] = update_duration
            data["total_updates"] = self._total_updates
            data["failed_reads"] = self._failed_reads
            data["last_update_time"] = datetime.now(timezone.utc)

            # Get RSSI if available
            try:
                if self._client and self._client.is_connected:
                    rssi = await self._client.get_rssi()
                    data["ble_rssi"] = rssi
            except (AttributeError, NotImplementedError):
                data["ble_rssi"] = None

            _LOGGER.info(
                "Successfully updated all data: %d data points read in %d batches, duration: %.2fs",
                len(data) - 1,
                len(self._register_batches),
                update_duration,
            )

            return data

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error updating data: %s", err, exc_info=True)
            raise UpdateFailed(
                f"Unexpected error communicating with device: {type(err).__name__}: {err}"
            ) from err

    async def _ensure_connection(self) -> bool:
        """Ensure BLE connection is established with exponential backoff."""
        if self._client and self._client.is_connected:
            return True

        if self._consecutive_failures >= self._max_consecutive_failures:
            time_since_last = time.time() - self._last_connection_attempt
            if time_since_last >= self._max_backoff:
                _LOGGER.debug(
                    "Resetting failure counter after %.1fs - attempting recovery",
                    time_since_last,
                )
                self._consecutive_failures = 0
                self._backoff_time = 1.0
            else:
                _LOGGER.error(
                    "Maximum consecutive connection failures (%d) reached. "
                    "Waiting %.1fs before reset attempt.",
                    self._max_consecutive_failures,
                    self._max_backoff - time_since_last,
                )
                return False

        if self._consecutive_failures > 0:
            current_time = time.time()
            time_since_last_attempt = current_time - self._last_connection_attempt

            if time_since_last_attempt < self._backoff_time:
                wait_time = self._backoff_time - time_since_last_attempt
                _LOGGER.debug(
                    "Waiting %.1fs before reconnection attempt (backoff: %.1fs, failures: %d/%d)",
                    wait_time,
                    self._backoff_time,
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                )
                await asyncio.sleep(wait_time)

        self._last_connection_attempt = time.time()

        try:
            if not self._ble_device:
                self._ble_device = bluetooth.async_ble_device_from_address(
                    self.hass, self._address, connectable=True
                )

            if not self._ble_device:
                _LOGGER.error("BLE device not found: %s", self._address)
                self._consecutive_failures += 1
                self._backoff_time = min(self._backoff_time * 2, self._max_backoff)
                _LOGGER.debug(
                    "Device not found, backoff increased to %.1fs (failures: %d/%d)",
                    self._backoff_time,
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                )
                return False

            _LOGGER.debug("Connecting to BLE device %s", self._address)
            try:
                self._client = await asyncio.wait_for(
                    establish_connection(
                        BleakClient,
                        self._ble_device,
                        self._ble_device.address,
                        disconnected_callback=self._on_disconnect,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                _LOGGER.error(
                    "Timeout connecting to BLE device %s after 30 seconds",
                    self._address,
                )
                self._consecutive_failures += 1
                self._backoff_time = min(self._backoff_time * 2, self._max_backoff)
                _LOGGER.debug(
                    "Connection timeout, backoff increased to %.1fs (failures: %d/%d)",
                    self._backoff_time,
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                )
                return False

            if not self._client.is_connected:
                _LOGGER.error("Failed to connect to BLE device")
                return False

            # Subscribe to notifications (10 second timeout)
            try:
                await asyncio.wait_for(
                    self._client.start_notify(
                        BLE_NOTIFY_UUID, self._notification_handler
                    ),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                _LOGGER.error("Timeout subscribing to notifications after 10 seconds")
                if self._client:
                    await self._client.disconnect()
                    self._client = None
                self._consecutive_failures += 1
                self._backoff_time = min(self._backoff_time * 2, self._max_backoff)
                _LOGGER.debug(
                    "Notification subscription failed, backoff increased to %.1fs (failures: %d/%d)",
                    self._backoff_time,
                    self._consecutive_failures,
                    self._max_consecutive_failures,
                )
                return False

            _LOGGER.info("Connected to SRNE inverter at %s", self._address)
            self._backoff_time = 1.0
            self._consecutive_failures = 0
            return True

        except BleakError as err:
            _LOGGER.error("BLE connection error: %s", err)
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
            self._consecutive_failures += 1
            self._backoff_time = min(self._backoff_time * 2, self._max_backoff)
            _LOGGER.debug(
                "BLE error, backoff increased to %.1fs (failures: %d/%d)",
                self._backoff_time,
                self._consecutive_failures,
                self._max_consecutive_failures,
            )
            return False

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle BLE disconnection."""
        try:
            _LOGGER.debug("BLE device disconnected: %s", self._address)
            self._client = None
        except Exception as err:
            _LOGGER.error("Error in disconnect callback: %s", err)

    def _notification_handler(self, sender: Any, data: bytes) -> None:
        """Handle incoming BLE notifications."""
        _LOGGER.debug("Received notification: %s", data.hex())
        try:
            self._notification_queue.put_nowait(data)
        except asyncio.QueueFull:
            _LOGGER.debug("Notification queue full, dropping packet")

    async def _enforce_command_delay(self, is_batch_read: bool = True) -> None:
        """Enforce delay between BLE commands.

        Args:
            is_batch_read: True for batch reads, False for write operations
        """
        delay = BATCH_READ_DELAY if is_batch_read else COMMAND_DELAY_WRITE

        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_command_time

        if elapsed < delay and self._last_command_time > 0:
            wait_time = delay - elapsed
            _LOGGER.debug(
                "Waiting %.1fs before next command (batch_read=%s)",
                wait_time,
                is_batch_read,
            )
            await asyncio.sleep(wait_time)

        self._last_command_time = asyncio.get_event_loop().time()

    async def _read_register(
        self, register: int, count: int = 1, slave_id: int = DEFAULT_SLAVE_ID
    ) -> dict[str, Any] | None:
        """Read register(s) via BLE Modbus.

        Args:
            register: Register address to read.
            count: Number of registers to read.
            slave_id: Modbus slave ID.

        Returns:
            Decoded response or None on error.
        """
        # Check if client is connected before attempting read
        if self._client is None or not self._client.is_connected:
            _LOGGER.debug(
                "Cannot read register 0x%04X: BLE client not connected",
                register,
            )
            return None

        async with self._command_lock:
            # Determine if this is a batch read (count > 1)
            is_batch = count > 1
            await self._enforce_command_delay(is_batch_read=is_batch)

            # Clear notification queue using helper
            self._clear_notification_queue()

            # Build and send command
            command = ModbusProtocol.build_read_command(slave_id, register, count)
            _LOGGER.debug("Reading register 0x%04X: %s", register, command.hex())

            try:
                await self._client.write_gatt_char(
                    BLE_WRITE_UUID, command, response=True
                )
            except BleakError as err:
                _LOGGER.error("Failed to write command: %s", err)
                self._failed_reads += 1
                return None

            # Wait for notification response
            try:
                response = await asyncio.wait_for(
                    self._notification_queue.get(), timeout=3.0
                )
                decoded = ModbusProtocol.decode_response(response)
                _LOGGER.debug("Decoded response: %s", decoded)
                return decoded
            except asyncio.TimeoutError:
                _LOGGER.debug(
                    "Timeout waiting for register 0x%04X response", register
                )
                self._failed_reads += 1
                return None

    async def _authenticate_with_password(self, password: int) -> bool:
        """Authenticate with password before writing protected registers.

        Args:
            password: Password (0 = no password)

        Returns:
            True if authentication succeeded
        """
        if password == 0:
            _LOGGER.debug("No password configured, skipping authentication")
            return True

        _LOGGER.info("Authenticating with password for protected register access")

        async with self._command_lock:
            await self._enforce_command_delay(is_batch_read=False)
            self._clear_notification_queue()

            command = ModbusProtocol.build_write_command(
                DEFAULT_SLAVE_ID, 0xE203, password
            )
            _LOGGER.debug("Sending password authentication: %s", command.hex())

            try:
                await self._client.write_gatt_char(
                    BLE_WRITE_UUID, command, response=True
                )

                response = await asyncio.wait_for(
                    self._notification_queue.get(), timeout=3.0
                )
                decoded = ModbusProtocol.decode_response(response)

                if decoded and "error" not in decoded:
                    _LOGGER.debug("Password authentication successful")
                    return True
                else:
                    error_code = decoded.get("error") if decoded else None
                    if error_code == 0x05:
                        _LOGGER.error(
                            "Password authentication failed: Incorrect password (0x05). "
                            "Try common defaults: 4321, 0000, 111111, or 1111"
                        )
                    else:
                        _LOGGER.error("Password authentication failed: error 0x%02X", error_code or 0)
                    return False

            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.error("Password authentication error: %s", err)
                return False

    async def async_write_register(
        self, register: int, value: int, slave_id: int = DEFAULT_SLAVE_ID
    ) -> bool:
        """Queue write command for execution.

        WARNING: Improper register writes may damage inverter or connected devices.
        Verify parameters before calling.

        Args:
            register: Register address
            value: Value to write
            slave_id: Modbus slave ID

        Returns:
            True if queued successfully

        Raises:
            ValueError: If register or value is out of valid range
        """
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"Invalid register value: {value} (must be 0-65535)")
        if not 0 <= register <= 0xFFFF:
            raise ValueError(f"Invalid register address: {register}")

        if 0xE000 <= register <= 0xE0FF:
            password = self._entry.data.get("inverter_password", 0)
            if password and password != 0:
                _LOGGER.info(
                    "Register 0x%04X is protected, authenticating with password",
                    register
                )
                if not await self._authenticate_with_password(password):
                    _LOGGER.error(
                        "Password authentication failed, cannot write to register 0x%04X. "
                        "Check password in integration settings.",
                        register
                    )
                    return False
                await asyncio.sleep(0.2)

        await self._write_queue.put((register, value))

        async with self._command_lock:
            if self._write_task is None or self._write_task.done():
                self._write_task = asyncio.create_task(self._process_write_queue())

        return True

    async def _process_write_queue(self) -> None:
        """Process write commands with proper spacing."""
        while not self._write_queue.empty():
            try:
                # Use get_nowait to avoid blocking if queue becomes empty
                register, value = self._write_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            async with self._command_lock:
                await self._enforce_command_delay(is_batch_read=False)

                self._clear_notification_queue()

                command = ModbusProtocol.build_write_command(
                    DEFAULT_SLAVE_ID, register, value
                )
                _LOGGER.info(
                    "Writing register 0x%04X = 0x%04X: %s",
                    register,
                    value,
                    command.hex(),
                )

                try:
                    await self._client.write_gatt_char(
                        BLE_WRITE_UUID, command, response=True
                    )

                    response = await asyncio.wait_for(
                        self._notification_queue.get(), timeout=3.0
                    )
                    decoded = ModbusProtocol.decode_response(response)

                    if decoded and "error" not in decoded:
                        _LOGGER.info("Successfully wrote register 0x%04X = %d", register, value)
                    else:
                        error_code = decoded.get("error") if decoded else None

                        if error_code == 0x0B:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Permission denied. "
                                "Configure inverter password in integration settings. "
                                "Common passwords: 4321, 0000, 111111",
                                register
                            )
                        elif error_code == 0x05:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Incorrect password. "
                                "Check password in integration settings.",
                                register
                            )
                        elif error_code == 0x09:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: System locked. "
                                "Configure password in integration settings.",
                                register
                            )
                        elif error_code == 0x02:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Illegal data address",
                                register
                            )
                        elif error_code == 0x03:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Value %d out of range",
                                register, value
                            )
                        elif error_code == 0x07:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Read-only register",
                                register
                            )
                        elif error_code == 0x08:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Cannot modify during operation",
                                register
                            )
                        elif error_code:
                            error_msg = MODBUS_ERROR_CODES.get(error_code, f"Unknown error 0x{error_code:02X}")
                            _LOGGER.error(
                                "Write to register 0x%04X failed: %s",
                                register,
                                error_msg
                            )
                        else:
                            _LOGGER.error(
                                "Write to register 0x%04X failed: Timeout or invalid response",
                                register
                            )

                except (BleakError, asyncio.TimeoutError) as err:
                    _LOGGER.error("Failed to write register 0x%04X: %s", register, err)

            self._write_queue.task_done()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and clean up BLE connection."""
        _LOGGER.debug("Shutting down coordinator")

        if self._write_task and not self._write_task.done():
            self._write_task.cancel()
            try:
                await asyncio.wait_for(self._write_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                _LOGGER.debug("Write task did not complete within timeout")

        if self._client:
            try:
                try:
                    if self._client.is_connected:
                        await asyncio.wait_for(
                            self._client.stop_notify(BLE_NOTIFY_UUID), timeout=5.0
                        )
                except (BleakError, asyncio.TimeoutError, AttributeError) as err:
                    _LOGGER.debug("Could not stop notifications: %s", err)

                try:
                    await asyncio.wait_for(self._client.disconnect(), timeout=5.0)
                    _LOGGER.info("Disconnected from BLE device")
                except (BleakError, asyncio.TimeoutError, AttributeError) as err:
                    _LOGGER.debug("Error disconnecting: %s", err)

            except Exception as err:
                _LOGGER.error("Unexpected error during BLE cleanup: %s", err)

        self._client = None
        self._ble_device = None
