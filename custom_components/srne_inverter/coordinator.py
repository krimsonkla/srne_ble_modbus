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

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .domain.helpers.address_helpers import format_address
from .domain.helpers.transformations import convert_to_signed_int16
from .const import (
    DEFAULT_SLAVE_ID,
    DOMAIN,
    TIMING_SAMPLE_SIZE,
)

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# DATA UPDATE COORDINATOR
# ============================================================================


class SRNEDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for SRNE Inverter data updates via BLE."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_config: dict[str, Any],
        transport: Any = None,
        connection_manager: Any = None,
        refresh_data_use_case: Any = None,
        write_register_use_case: Any = None,
        batch_builder: Any = None,
        register_mapper: Any = None,
        transaction_manager: Any = None,
        timing_collector: Any = None,
        timeout_learner: Any = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            entry: Config entry
            device_config: Device configuration with registers
            transport: Optional injected ITransport implementation
            connection_manager: Optional injected IConnectionManager implementation
            refresh_data_use_case: Optional RefreshDataUseCase
            write_register_use_case: Optional WriteRegisterUseCase
            batch_builder: Optional BatchBuilderService
            register_mapper: Optional RegisterMapperService
            transaction_manager: Optional TransactionManagerService
            timing_collector: Optional TimingCollector for Phase 2 measurement
            timeout_learner: Optional TimeoutLearner for Phase 3 learning
        """
        # Get update interval from options, default to 60s
        update_interval_seconds = entry.options.get("update_interval", 60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds),
        )

        _LOGGER.info(
            "Initialized coordinator with %ds update interval (ephemeral connection pattern)",
            update_interval_seconds,
        )

        self._address = entry.data["address"]

        # Injected dependencies
        self._transport = transport
        self._connection_manager = connection_manager
        self._refresh_data_use_case = refresh_data_use_case
        self._write_register_use_case = write_register_use_case
        self._batch_builder = batch_builder
        self._register_mapper = register_mapper
        self._transaction_manager = transaction_manager
        self._timing_collector = timing_collector
        self._timeout_learner = timeout_learner

        # Device configuration and dynamic batching
        self._device_config = device_config
        self._entry = entry
        self._failed_registers: set[int] = set()
        self._batches_need_rebuild = False

        # Phase 4: Learned timeout persistence
        self._learned_timeouts: dict[str, float] = {}
        self._update_counter: int = 0

        # Dependency tracking for calculated sensors
        self._dependency_map: dict[str, list[str]] = {}
        self._unavailable_sensors: set[str] = set()
        self._build_dependency_map()

        # Don't build batches here - will be built in _load_storage() after loading storage
        # This avoids processing all registers twice (once here, once after loading failed registers)
        self._register_batches = []

        _LOGGER.debug(
            "Initialized coordinator for device %s (batches will be built after loading storage)",
            self._address,
        )

    def _apply_learned_timeouts(self, learned_timeouts: dict[str, float]) -> None:
        """Apply learned timeouts to transport (Phase 5: Runtime Application).

        Args:
            learned_timeouts: Dict mapping operation -> timeout (seconds)
        """
        if learned_timeouts and self._transport:
            if hasattr(self._transport, "set_learned_timeouts"):
                self._transport.set_learned_timeouts(learned_timeouts)
                _LOGGER.info("Applied learned timeouts to transport")
            else:
                _LOGGER.debug(
                    "Transport does not support learned timeouts (Phase 5 not active)"
                )

    async def _update_learned_timeouts(self) -> None:
        """Calculate and update learned timeouts (Phase 3 + Phase 4).

        Uses TimeoutLearner to calculate optimal timeouts from TimingCollector data.
        Applies learned timeouts to transport and saves to storage.
        """
        if not self._timeout_learner:
            return

        # Calculate learned timeouts for known operations
        # Note: BLE send includes the full Modbus transaction (write + read)
        operations = ["ble_send"]
        new_timeouts = {}

        for operation in operations:
            learned = self._timeout_learner.calculate_timeout(operation)
            if learned:
                new_timeouts[operation] = learned.timeout
                _LOGGER.debug(
                    "Learned timeout for %s: %.2fs (from %d samples, P95=%.2fms)",
                    operation,
                    learned.timeout,
                    learned.based_on_samples,
                    learned.p95_measured * 1000,
                )

        # Only update if we have new learned values
        if new_timeouts:
            # Check if timeouts changed significantly (>10% change)
            should_save = False
            for op, new_val in new_timeouts.items():
                old_val = self._learned_timeouts.get(op)
                if old_val is None or abs(new_val - old_val) / old_val > 0.1:
                    should_save = True
                    break

            if should_save:
                self._learned_timeouts.update(new_timeouts)
                self._apply_learned_timeouts(self._learned_timeouts)
                await self._save_storage()
                _LOGGER.info(
                    "Updated and saved learned timeouts: %s",
                    {op: f"{val:.2f}s" for op, val in new_timeouts.items()},
                )

    async def _load_storage(self) -> None:
        """Load all persistent storage (failed registers, unavailable sensors, learned timeouts)."""
        store = Store(self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers")

        try:
            data = await store.async_load()
            if data:
                # Load failed registers
                if "failed_registers" in data:
                    self._failed_registers = set(data["failed_registers"])
                    _LOGGER.info(
                        "Loaded %d failed registers from storage: %s",
                        len(self._failed_registers),
                        [format_address(r) for r in sorted(self._failed_registers)],
                    )

                    # Debug: Print detailed information about each failed register
                    if self._failed_registers and _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug("Failed registers detailed breakdown:")
                        sorted_failed = sorted(self._failed_registers)

                        # Build reverse lookup: address -> register name
                        address_to_name = {}
                        if "registers" in self._device_config:
                            for reg_name, reg_def in self._device_config[
                                "registers"
                            ].items():
                                address = reg_def.get("address")
                                if address is not None:
                                    # Convert hex string to int if needed
                                    if isinstance(address, str):
                                        address = int(
                                            address,
                                            16 if address.startswith("0x") else 10,
                                        )
                                    address_to_name[address] = reg_name

                        # Log each failed register with its name
                        for addr in sorted_failed:
                            reg_name = address_to_name.get(addr, "UNKNOWN")
                            _LOGGER.debug(
                                "  - %s (%d): %s",
                                format_address(addr),
                                addr,
                                reg_name,
                            )

                        # Log address ranges for pattern analysis
                        if len(sorted_failed) > 1:
                            ranges = []
                            range_start = sorted_failed[0]
                            range_end = sorted_failed[0]

                            for addr in sorted_failed[1:]:
                                if addr == range_end + 1:
                                    # Consecutive address, extend range
                                    range_end = addr
                                else:
                                    # Gap found, save current range and start new one
                                    if range_start == range_end:
                                        ranges.append(format_address(range_start))
                                    else:
                                        ranges.append(
                                            f"{format_address(range_start)}-{format_address(range_end)}"
                                        )
                                    range_start = addr
                                    range_end = addr

                            # Add final range
                            if range_start == range_end:
                                ranges.append(format_address(range_start))
                            else:
                                ranges.append(
                                    f"{format_address(range_start)}-{format_address(range_end)}"
                                )

                            _LOGGER.debug(
                                "Failed register address ranges: %s", ", ".join(ranges)
                            )

                if "unavailable_sensors" in data:
                    self._unavailable_sensors = set(data["unavailable_sensors"])
                    if self._unavailable_sensors:
                        _LOGGER.debug(
                            "Loaded %d unavailable sensors from storage: %s",
                            len(self._unavailable_sensors),
                            list(self._unavailable_sensors),
                        )

                # Phase 4: Load and apply learned timeouts
                if "learned_timeouts" in data:
                    self._learned_timeouts = data["learned_timeouts"]
                    if self._learned_timeouts:
                        _LOGGER.info(
                            "Loaded %d learned timeout(s) from storage: %s",
                            len(self._learned_timeouts),
                            {op: f"{val:.2f}s" for op, val in self._learned_timeouts.items()},
                        )
                        # Apply learned timeouts to transport (Phase 5: Runtime Application)
                        self._apply_learned_timeouts(self._learned_timeouts)

        except Exception as err:
            _LOGGER.debug("No previous failed registers found: %s", err)
            self._failed_registers = set()
            self._unavailable_sensors = set()

        # Sync loaded failed registers to transaction manager
        # This ensures the batch builder gets the correct failed register set
        if self._failed_registers:
            self._transaction_manager.initialize_failed_registers(
                self._failed_registers
            )
            _LOGGER.debug(
                "Synced %d failed registers to transaction manager",
                len(self._failed_registers),
            )

        # Always rebuild batches after loading storage (whether failed registers exist or not)
        # This ensures we only process the full register list once
        self._rebuild_batches()
        self._log_dependency_diagnostics()

    def _rebuild_batches(self) -> None:
        """Rebuild register batches using BatchBuilderService."""
        try:
            failed_registers = self._transaction_manager.get_failed_registers()

            # Pass config entry options to batch builder so it can filter
            # registers based on disabled entity types (numbers/selects)
            options = self._entry.options if self._entry else {}

            self._register_batches = self._batch_builder.build_batches(
                device_config=self._device_config,
                failed_registers=failed_registers,
                options=options,
            )

            self._transaction_manager.acknowledge_batch_rebuild()

            _LOGGER.info(
                "Built %d register batches for device %s (excluding %d failed registers)",
                len(self._register_batches),
                self._address,
                len(failed_registers),
            )

        except Exception as err:
            _LOGGER.error("Error rebuilding batches: %s", err)
            # Keep existing batches on error

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
                    affected_sensors_by_register[
                        f"{reg_name} ({format_address(address)})"
                    ] = affected_sensors

        if affected_sensors_by_register:
            _LOGGER.debug(
                "Failed registers impact %d calculated sensors:",
                len(
                    set(
                        s
                        for sensors in affected_sensors_by_register.values()
                        for s in sensors
                    )
                ),
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

    async def _save_storage(self) -> None:
        """Save all persistent storage (failed registers, unavailable sensors, learned timeouts)."""
        store = Store(self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers")
        try:
            unavailable_sensors = self._get_unavailable_sensors() if self.data else []
            self._unavailable_sensors = set(unavailable_sensors)

            # Phase 4: Include learned timeouts in storage
            storage_data = {
                "failed_registers": list(self._failed_registers),
                "unavailable_sensors": unavailable_sensors,
                "learned_timeouts": self._learned_timeouts,
            }

            await store.async_save(storage_data)

            _LOGGER.info(
                "Saved %d failed registers to storage: %s",
                len(self._failed_registers),
                [format_address(r) for r in sorted(self._failed_registers)],
            )

            if unavailable_sensors:
                _LOGGER.debug(
                    "%d calculated sensors unavailable due to missing dependencies: %s",
                    len(unavailable_sensors),
                    unavailable_sensors,
                )

            if self._learned_timeouts:
                _LOGGER.debug(
                    "Saved %d learned timeout(s): %s",
                    len(self._learned_timeouts),
                    {op: f"{val:.2f}s" for op, val in self._learned_timeouts.items()},
                )

            self._rebuild_batches()
            self._log_dependency_diagnostics()
        except Exception as err:
            _LOGGER.error("Failed to save failed registers: %s", err)

    async def clear_failed_registers(self) -> None:
        """Clear failed register cache and force re-scan of all registers."""
        store = Store(self.hass, 1, f"{DOMAIN}_{self._entry.entry_id}_failed_registers")

        try:
            await store.async_remove()

            old_count = len(self._failed_registers)
            self._failed_registers.clear()
            self._unavailable_sensors.clear()

            _LOGGER.info(
                "Cleared %d failed registers from cache. All registers will be re-scanned.",
                old_count,
            )

            self._rebuild_batches()

            _LOGGER.info(
                "Rebuilt %d register batches for full re-scan",
                len(self._register_batches),
            )

            await self.async_refresh()

            _LOGGER.info("Register re-scan initiated successfully")

        except Exception as err:
            _LOGGER.error("Failed to clear failed registers: %s", err)
            raise

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from inverter using RefreshDataUseCase.

        Implements ephemeral connection pattern:
        - Connect before reads
        - Disconnect after completion (success or error)

        Exception handling pattern:
        - Raises UpdateFailed on errors
        - Propagates to Home Assistant DataUpdateCoordinator
        - On first refresh, ConfigEntryNotReady triggers HA retry mechanism
        """
        try:
            result = await self._refresh_data_use_case.execute(
                device_address=self._address,
                register_batches=self._register_batches,
                register_definitions=self._device_config.get("registers", {}),
            )

            if not result.success:
                raise UpdateFailed(result.error)

            # CRITICAL FIX: Persist newly discovered failed registers
            # Without this, batches are re-split every cycle
            if result.failed_registers:
                new_failed = result.failed_registers - self._failed_registers
                if new_failed:
                    _LOGGER.info(
                        "Discovered %d new failed register(s): %s",
                        len(new_failed),
                        [format_address(r) for r in sorted(new_failed)],
                    )
                    self._failed_registers.update(result.failed_registers)
                    # Save to persistent storage and rebuild batches
                    await self._save_storage()

            # Phase 4: Periodic saving of learned timeouts (every 10 updates)
            self._update_counter += 1
            if self._update_counter % 10 == 0:
                await self._update_learned_timeouts()

            return result.data

        # Retry strategy:
        # - TimeoutError (30s): Temporary issues (device busy), retry soon
        # - Connection errors (60s): Lost connection, needs stabilization time
        # - Other errors: Use normal update_interval (60s from __init__)
        # Note: retry_after requires Home Assistant 2025.11+
        except TimeoutError as err:
            # Temporary issue (device busy/slow) - retry sooner
            _LOGGER.warning("Timeout communicating with inverter: %s", err)
            raise UpdateFailed(
                f"Communication timeout: {err}",
                retry_after=30,  # Retry in 30s instead of normal 60s interval
            ) from err
        except (ConnectionError, RuntimeError) as err:
            # Connection lost - needs time to stabilize
            _LOGGER.warning("Connection lost to inverter: %s", err)
            raise UpdateFailed(
                f"Connection lost: {err}",
                retry_after=60,  # Retry in 60s to allow connection recovery
            ) from err
        except Exception as err:
            # Other errors - use normal update interval
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error fetching inverter data: {err}") from err

    async def async_read_register(self, register: int) -> int | None:
        """Read a single register value.

        Args:
            register: Register address to read

        Returns:
            Register value as integer, or None if read failed
        """
        try:
            # Use the transport directly to read a single register
            if not self._transport:
                _LOGGER.error("Transport not available for register read")
                return None

            # Connect if not connected
            if not self._transport.is_connected:
                await self._connection_manager.connect(self._address)

            # Read single register (1 word)
            result = await self._transport.read_holding_registers(
                address=register,
                count=1,
            )

            if result and len(result) > 0:
                return result[0]

            return None

        except Exception as err:
            _LOGGER.error("Read register 0x%04X error: %s", register, err)
            return None

    async def async_write_register(
        self,
        register: int,
        value: int,
        slave_id: int = DEFAULT_SLAVE_ID,
    ) -> bool:
        """Write register value using WriteRegisterUseCase.

        WARNING: Improper register writes may damage inverter or connected devices.
        Verify parameters before calling.

        Args:
            register: Register address
            value: Value to write
            slave_id: Modbus slave ID (unused)

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            password = self._entry.data.get("inverter_password", 0)

            result = await self._write_register_use_case.execute(
                register=register,
                value=value,
                password=password,
            )

            if not result.success:
                _LOGGER.error(
                    "Failed to write register 0x%04X: %s",
                    register,
                    result.error,
                )

            return result.success

        except Exception as err:
            _LOGGER.error("Write register error: %s", err)
            return False

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and clean up resources."""
        _LOGGER.debug("Shutting down coordinator")

        # Transport cleanup via injected dependency
        try:
            if self._transport and self._transport.is_connected:
                await self._transport.disconnect()
                _LOGGER.info("Disconnected from BLE device")
        except Exception as err:
            _LOGGER.error("Unexpected error during disconnect: %s", err)
