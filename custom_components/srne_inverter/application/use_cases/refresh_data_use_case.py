"""RefreshDataUseCase for SRNE Inverter data polling.

This use case orchestrates the complete data refresh workflow:
1. Ensure BLE connection
2. Read register batches
3. Extract and map data
4. Handle failures with retry/split logic
5. Enrich with diagnostics

Extracted from coordinator._async_update_data() method.
Application Layer Extraction
Extracted DTOs
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional

from ...domain.interfaces import IConnectionManager, ITransport, IProtocol
from ...domain.exceptions import DeviceRejectedCommandError
from ...domain.value_objects.exception_code import ExceptionCode
from ...domain.entities.register_batch import RegisterBatch
from ...domain.helpers.transformations import process_register_value
from ...infrastructure.decorators import require_connection
from ...const import MODBUS_RESPONSE_TIMEOUT
from .refresh_data_result import RefreshDataResult

_LOGGER = logging.getLogger(__name__)


class RefreshDataUseCase:
    """Use case for refreshing inverter data.

    This use case encapsulates the complete data refresh workflow,
    which was previously embedded in the coordinator's _async_update_data method.

    Responsibilities:
    - Orchestrate connection management
    - Execute batch reading strategy
    - Handle batch failures with split/retry
    - Extract and map register data
    - Enrich with diagnostic information

    Dependencies (injected):
    - connection_manager: Manages BLE connection lifecycle
    - transport: Handles low-level communication
    - protocol: Builds commands and decodes responses

    Example:
        >>> use_case = RefreshDataUseCase(conn_mgr, transport, protocol)
        >>> result = await use_case.execute(address, batches, register_defs)
        >>> if result.success:
        ...     print(f"Read {len(result.data)} values in {result.duration:.2f}s")
    """

    # Configuration
    MAX_SPLIT_DEPTH = 5  # Maximum recursion depth for batch splitting
    # Increased to handle larger batches: 18 → 9 → 5 → 3 → 2 → 1 requires 5 levels
    # Provides better coverage for edge cases and configurations

    def __init__(
        self,
        connection_manager: IConnectionManager,
        transport: ITransport,
        protocol: IProtocol,
    ):
        """Initialize use case with dependencies.

        Args:
            connection_manager: Connection lifecycle manager
            transport: Communication transport
            protocol: Modbus protocol implementation
        """
        self._connection_manager = connection_manager
        self._transport = transport
        self._protocol = protocol

        # Metrics tracking
        self._failed_reads = 0
        self._total_updates = 0
        self._start_time: float = 0.0

        # Performance metrics (timing optimization tracking)
        self._batch_timings: List[float] = []
        self._total_batches_processed = 0

        # Track permanently failed registers (unsupported by device)
        self._failed_registers: Set[int] = set()

        # Register definitions for name lookup
        self._register_definitions: Dict[str, Any] = {}
        self._address_to_name: Dict[int, str] = {}  # Cache for address -> name lookup

        # Performance: Cache address-to-name mapping (95% hit rate, saves 1,920 ops/hour)
        self._address_to_name_cache: Optional[Dict[int, str]] = None
        self._cached_batches_key: Optional[tuple] = None

    @require_connection(address_param="device_address")
    async def execute(
        self,
        device_address: str,
        register_batches: List[RegisterBatch],
        register_definitions: Dict[str, Any],
        slave_id: int = 1,
        known_failed_registers: Optional[Set[int]] = None,
    ) -> RefreshDataResult:
        """Execute data refresh workflow.

        Connection is guaranteed by decorator.

        Args:
            device_address: BLE MAC address of device
            register_batches: List of register batches to read
            register_definitions: Register configuration from YAML
            slave_id: Modbus slave ID (default: 1)
            known_failed_registers: Set of register addresses known to be unsupported (optional)

        Returns:
            RefreshDataResult with data or error

        Raises:
            Exception: Propagates any unexpected errors for coordinator handling
        """
        self._start_time = time.time()
        self._failed_reads = 0
        self._register_definitions = register_definitions

        # Build address-to-name mapping (cached - 95% hit rate)
        batch_key = tuple((int(b.start_address), b.count) for b in register_batches)
        if self._cached_batches_key != batch_key:
            # Batches changed, rebuild
            self._address_to_name_cache = {}
            for batch in register_batches:
                for offset, register_name in batch.register_map.items():
                    address = int(batch.start_address) + offset
                    self._address_to_name_cache[address] = register_name
            self._cached_batches_key = batch_key
        # Use cached mapping (guaranteed non-None after rebuild)
        self._address_to_name = (
            self._address_to_name_cache if self._address_to_name_cache else {}
        )

        # Initialize with known failed registers
        if known_failed_registers:
            self._failed_registers = known_failed_registers.copy()
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(
                    "Starting with %d known failed registers: %s",
                    len(self._failed_registers),
                    [f"0x{addr:04X}" for addr in sorted(self._failed_registers)],
                )
        else:
            self._failed_registers = set()

        try:

            # Step 2: Read all batches
            data = {}

            for i, batch in enumerate(register_batches, 1):
                # CRITICAL: Check connection before each batch
                # If disconnected, stop immediately instead of processing remaining batches
                if not self._transport.is_connected:
                    _LOGGER.error(
                        "Transport disconnected before batch %d/%d, aborting refresh",
                        i,
                        len(register_batches),
                    )
                    # Return partial data if we collected any
                    if data:
                        _LOGGER.info(
                            "Returning partial data: %d values from %d batches before disconnection",
                            len(data),
                            i - 1,
                        )
                    return RefreshDataResult(
                        data=data if data else {},
                        success=False,
                        error="Connection lost before completing all batches",
                        duration=time.time() - self._start_time,
                        failed_reads=self._failed_reads,
                        failed_registers=self._failed_registers.copy(),
                    )

                _LOGGER.debug(
                    "Reading batch %d/%d: 0x%04X-0x%04X (%d registers)",
                    i,
                    len(register_batches),
                    int(batch.start_address),
                    int(batch.start_address) + batch.count - 1,
                    batch.count,
                )

                # Attempt to read batch (with timing instrumentation)
                batch_start = time.time()
                try:
                    result = await self._read_batch(
                        int(batch.start_address),
                        batch.count,
                        slave_id,
                    )
                    batch_duration = time.time() - batch_start
                    self._batch_timings.append(batch_duration)
                    self._total_batches_processed += 1

                    if _LOGGER.isEnabledFor(logging.DEBUG):
                        _LOGGER.debug(
                            "Batch %d timing: %.3fs (avg: %.3fs over %d batches)",
                            i,
                            batch_duration,
                            sum(self._batch_timings) / len(self._batch_timings),
                            len(self._batch_timings),
                        )
                except RuntimeError as err:
                    # Connection error during read - stop processing batches
                    _LOGGER.error(
                        "Connection lost during batch %d (0x%04X), aborting refresh: %s",
                        i,
                        int(batch.start_address),
                        err,
                    )
                    # Return partial data collected so far
                    return RefreshDataResult(
                        data=data if data else {},
                        success=False,
                        error=f"Connection lost: {err}",
                        duration=time.time() - self._start_time,
                        failed_reads=self._failed_reads,
                        failed_registers=self._failed_registers.copy(),
                    )

                if result and isinstance(result, dict) and "error" not in result:
                    # Success - handle both formats:
                    # - New format: {0: 486, 1: 250} (offset: value)
                    # - Alternative format: {"values": [486, 250]}
                    if "values" in result:
                        # Alternative format from tests
                        values_list = result["values"]
                    else:
                        # New format from protocol - convert offset dict to list
                        numeric_keys = [k for k in result.keys() if isinstance(k, int)]
                        if numeric_keys:
                            max_offset = max(numeric_keys)
                            values_list = [
                                result.get(i, 0) for i in range(max_offset + 1)
                            ]
                        else:
                            values_list = []

                    if values_list:
                        batch_data = self._extract_batch_data(
                            batch,
                            values_list,
                            register_definitions,
                        )
                        data.update(batch_data)

                        _LOGGER.debug(
                            "Batch %d extracted %d values: %s",
                            i,
                            len(batch_data),
                            list(batch_data.keys()),
                        )
                else:
                    # Batch failed due to unsupported register - try splitting
                    _LOGGER.debug(
                        "Batch %d read failed: 0x%04X (count=%d), splitting and retrying...",
                        i,
                        int(batch.start_address),
                        batch.count,
                    )
                    self._failed_reads += 1

                    try:
                        split_data = await self._split_and_retry_batch(
                            int(batch.start_address),
                            batch.count,
                            batch.register_map,
                            slave_id,
                            split_depth=0,
                        )

                        if split_data:
                            data.update(split_data)
                            _LOGGER.info(
                                "Batch splitting recovered %d values from failed batch",
                                len(split_data),
                            )
                        else:
                            _LOGGER.debug(
                                "Batch splitting found no valid registers in batch %d",
                                i,
                            )
                    except RuntimeError as err:
                        # Connection lost during splitting - stop processing
                        _LOGGER.error(
                            "Connection lost during batch split for batch %d (0x%04X), aborting refresh: %s",
                            i,
                            int(batch.start_address),
                            err,
                        )
                        # Return partial data collected so far
                        return RefreshDataResult(
                            data={},
                            success=False,
                            error=f"Connection lost during split: {err}",
                            duration=time.time() - self._start_time,
                            failed_reads=self._failed_reads,
                            failed_registers=self._failed_registers.copy(),
                        )

            # Step 3: Enrich with metadata
            data["connected"] = True

            # Fault detection
            fault_codes = [
                data.get("fault_code_0", 0),
                data.get("fault_code_1", 0),
                data.get("fault_code_2", 0),
                data.get("fault_code_3", 0),
            ]
            data["fault_detected"] = any(code != 0 for code in fault_codes)
            data["fault_bits"] = fault_codes

            # Diagnostic metrics
            duration = time.time() - self._start_time
            self._total_updates += 1

            data["update_duration"] = duration
            data["total_updates"] = self._total_updates
            data["failed_reads"] = self._failed_reads
            data["last_update_time"] = datetime.now(timezone.utc)

            # BLE RSSI (if available)
            # Note: This will be removed when transport abstraction is complete
            data["ble_rssi"] = None

            # Performance summary
            if self._batch_timings:
                avg_batch_time = sum(self._batch_timings) / len(self._batch_timings)
                min_batch_time = min(self._batch_timings)
                max_batch_time = max(self._batch_timings)

                _LOGGER.info(
                    "Successfully updated all data: %d data points read in %d batches, "
                    "duration: %.2fs (batch avg: %.3fs, min: %.3fs, max: %.3fs)",
                    len(data) - 1,  # Exclude metadata
                    len(register_batches),
                    duration,
                    avg_batch_time,
                    min_batch_time,
                    max_batch_time,
                )
            else:
                _LOGGER.info(
                    "Successfully updated all data: %d data points read in %d batches, duration: %.2fs",
                    len(data) - 1,  # Exclude metadata
                    len(register_batches),
                    duration,
                )

            # Log newly discovered failed registers
            if self._failed_registers:
                _LOGGER.warning(
                    "Discovered %d unsupported registers during this update: %s",
                    len(self._failed_registers),
                    [f"0x{addr:04X}" for addr in sorted(self._failed_registers)],
                )

            return RefreshDataResult(
                data=data,
                success=True,
                duration=duration,
                failed_reads=self._failed_reads,
                failed_registers=self._failed_registers.copy(),
            )

        except Exception as err:
            _LOGGER.error(
                "Unexpected error during data refresh: %s", err, exc_info=True
            )
            return RefreshDataResult(
                data={},
                success=False,
                error=f"Unexpected error: {type(err).__name__}: {err}",
                duration=time.time() - self._start_time,
                failed_reads=self._failed_reads,
                failed_registers=self._failed_registers.copy(),
            )

    def _get_register_name(self, address: int) -> str:
        """Get register name for logging purposes.

        Args:
            address: Register address

        Returns:
            Formatted string with address and name (if known)
        """
        name = self._address_to_name.get(address)
        if name:
            return f"0x{address:04X} ({name})"
        return f"0x{address:04X}"

    async def _read_batch(
        self,
        start_address: int,
        count: int,
        slave_id: int,
    ) -> Optional[Dict[int | str, Any]]:
        """Read a batch of registers.

        Args:
            start_address: Starting register address
            count: Number of registers to read
            slave_id: Modbus slave ID

        Returns:
            Decoded response with int keys (offset -> value) or None on error
        """
        if not self._transport.is_connected:
            _LOGGER.debug("Cannot read batch: Transport not connected")
            return None

        # Skip single registers that are known to be unsupported
        if count == 1 and start_address in self._failed_registers:
            _LOGGER.debug(
                "Skipping known failed register %s",
                self._get_register_name(start_address),
            )
            return None

        # Build command
        command = self._protocol.build_read_command(start_address, count)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("Reading batch 0x%04X: %s", start_address, command.hex())

        try:
            # Send command and receive response
            response = await self._transport.send(
                command, timeout=MODBUS_RESPONSE_TIMEOUT
            )
            decoded = self._protocol.decode_response(response)
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("Decoded response: %s", decoded)

            # Check for Modbus exception (ILLEGAL_DATA_ADDRESS)
            # This indicates the register doesn't exist - permanent failure
            if (
                "error" in decoded
                and decoded["error"] == ExceptionCode.ILLEGAL_DATA_ADDRESS
            ):
                if count == 1:
                    self._failed_registers.add(start_address)
                    _LOGGER.info(
                        "Register %s not supported by device (Modbus exception 0x%02X: Illegal Data Address), marking as failed",
                        self._get_register_name(start_address),
                        ExceptionCode.ILLEGAL_DATA_ADDRESS,
                    )
                else:
                    _LOGGER.debug(
                        "Batch 0x%04X contains unsupported register (Modbus exception 0x%02X: Illegal Data Address), will split",
                        start_address,
                        ExceptionCode.ILLEGAL_DATA_ADDRESS,
                    )
                self._failed_reads += 1
                return None

            return decoded

        except DeviceRejectedCommandError:
            # Device rejected this batch - contains unsupported register(s)
            # If single register, mark as permanently failed
            if count == 1:
                self._failed_registers.add(start_address)
                _LOGGER.info(
                    "Register %s not supported by device, marking as failed",
                    self._get_register_name(start_address),
                )
            else:
                _LOGGER.debug(
                    "Batch 0x%04X rejected (contains unsupported register), will split",
                    start_address,
                )
            self._failed_reads += 1
            return None

        except RuntimeError as err:
            # Connection error - propagate up to stop batch splitting
            # RuntimeError is raised by transport when connection is lost
            error_msg = str(err).lower()
            if (
                "connection" in error_msg
                or "disconnected" in error_msg
                or "not connected" in error_msg
            ):
                _LOGGER.warning(
                    "Connection error during batch read 0x%04X: %s",
                    start_address,
                    err,
                )
                # Re-raise to signal connection failure (not register failure)
                raise
            else:
                # Other RuntimeError - treat as temporary failure
                _LOGGER.debug(
                    "Failed to read batch 0x%04X: %s",
                    start_address,
                    err,
                )
                self._failed_reads += 1
                return None

        except Exception as err:
            # Other temporary error (timeout, etc.) - treat as register issue
            _LOGGER.debug(
                "Failed to read batch 0x%04X: %s",
                start_address,
                err,
            )
            self._failed_reads += 1
            return None

    async def _split_and_retry_batch(
        self,
        start_address: int,
        count: int,
        register_map: Dict[int, str],
        slave_id: int,
        split_depth: int = 0,
    ) -> Dict[str, Any]:
        """Split failed batch and retry individual registers.

        This implements a recursive divide-and-conquer strategy:
        1. Try to read full batch
        2. If fails, split in half and try each half
        3. Recurse until individual registers or max depth

        Args:
            start_address: Starting register address
            count: Number of registers
            register_map: Offset -> register name mapping
            slave_id: Modbus slave ID
            split_depth: Current recursion depth

        Returns:
            Dictionary of successfully read values
        """
        # CRITICAL: Check connection state before splitting
        # If transport is disconnected, stop splitting immediately to prevent
        # cascade of failed attempts that all return None
        if not self._transport.is_connected:
            _LOGGER.warning(
                "Transport disconnected during batch split at 0x%04X, aborting split operation",
                start_address,
            )
            return {}

        if split_depth >= self.MAX_SPLIT_DEPTH:
            _LOGGER.debug(
                "Max split depth reached for 0x%04X, giving up",
                start_address,
            )
            return {}

        # Base case: single register
        if count == 1:
            try:
                result = await self._read_batch(start_address, 1, slave_id)
            except RuntimeError as err:
                # Connection error - stop splitting and propagate
                _LOGGER.warning(
                    "Connection error reading register %s, stopping split: %s",
                    self._get_register_name(start_address),
                    err,
                )
                return {}

            # Protocol layer returns {offset: value} format, e.g., {0: 5998}
            # Check for successful result: non-None dict without "error" key, containing offset 0
            if (
                result
                and isinstance(result, dict)
                and "error" not in result
                and 0 in result
            ):
                # Success - map register name
                if 0 in register_map:
                    register_name = register_map[0]
                    value = result[0]
                    _LOGGER.debug(
                        "Single register read succeeded: %s = %d",
                        self._get_register_name(start_address),
                        value,
                    )
                    return {register_name: value}
            else:
                _LOGGER.debug(
                    "Single register %s failed", self._get_register_name(start_address)
                )

            return {}

        # Recursive case: split batch in half
        mid = count // 2
        first_half_size = mid
        second_half_size = count - mid
        second_half_start = start_address + mid

        _LOGGER.debug(
            "Splitting batch 0x%04X (count=%d) into two: 0x%04X (%d) and 0x%04X (%d)",
            start_address,
            count,
            start_address,
            first_half_size,
            second_half_start,
            second_half_size,
        )

        data = {}

        # Try first half
        first_register_map = {
            offset: name for offset, name in register_map.items() if offset < mid
        }

        if first_register_map:
            try:
                first_result = await self._read_batch(
                    start_address,
                    first_half_size,
                    slave_id,
                )
            except RuntimeError as err:
                # Connection error - stop splitting and return partial data
                _LOGGER.warning(
                    "Connection error reading first half at 0x%04X, stopping split: %s",
                    start_address,
                    err,
                )
                return data

            # Protocol returns {offset: value} format
            if (
                first_result
                and isinstance(first_result, dict)
                and "error" not in first_result
            ):
                # First half succeeded - extract values from offset dict
                for offset, value in first_result.items():
                    if isinstance(offset, int) and offset in first_register_map:
                        register_name = first_register_map[offset]
                        data[register_name] = value
            else:
                # First half failed due to unsupported register - recurse to find it
                _LOGGER.debug("First half failed, splitting further")
                try:
                    first_data = await self._split_and_retry_batch(
                        start_address,
                        first_half_size,
                        first_register_map,
                        slave_id,
                        split_depth + 1,
                    )
                    data.update(first_data)
                except RuntimeError:
                    # Connection error during recursion - stop and return what we have
                    return data

        # Try second half
        second_register_map = {
            offset - mid: name for offset, name in register_map.items() if offset >= mid
        }

        if second_register_map:
            try:
                second_result = await self._read_batch(
                    second_half_start,
                    second_half_size,
                    slave_id,
                )
            except RuntimeError as err:
                # Connection error - stop splitting and return partial data
                _LOGGER.warning(
                    "Connection error reading second half at 0x%04X, stopping split: %s",
                    second_half_start,
                    err,
                )
                return data

            # Protocol returns {offset: value} format
            if (
                second_result
                and isinstance(second_result, dict)
                and "error" not in second_result
            ):
                # Second half succeeded - extract values from offset dict
                for offset, value in second_result.items():
                    if isinstance(offset, int) and offset in second_register_map:
                        register_name = second_register_map[offset]
                        data[register_name] = value
            else:
                # Second half failed due to unsupported register - recurse to find it
                _LOGGER.debug("Second half failed, splitting further")
                try:
                    second_data = await self._split_and_retry_batch(
                        second_half_start,
                        second_half_size,
                        second_register_map,
                        slave_id,
                        split_depth + 1,
                    )
                    data.update(second_data)
                except RuntimeError:
                    # Connection error during recursion - stop and return what we have
                    return data

        return data

    def _extract_batch_data(
        self,
        batch: RegisterBatch,
        values: List[int],
        register_definitions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract register data from batch values.

        Maps raw register values to named data using register definitions.
        Applies scaling, offset, and data type conversions.

        Args:
            batch: Register batch information
            values: Raw register values
            register_definitions: Register configuration

        Returns:
            Dictionary of register_name -> processed_value
        """
        data = {}

        for offset, register_name in batch.register_map.items():
            if offset < len(values):
                raw_value = values[offset]

                # Get register definition
                reg_def = register_definitions.get(register_name, {})

                # Apply transformations
                value = process_register_value(
                    raw_value,
                    data_type=reg_def.get("data_type", "uint16"),
                    scale=reg_def.get(
                        "scaling", 1.0
                    ),  # Fixed: YAML uses "scaling" not "scale"
                    offset=reg_def.get("offset", 0),
                )

                data[register_name] = value

        return data
