# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""Write transaction manager for safe register writes with rollback capability.

Features:
- Atomic writes with read-before-write
- Read-verify after write
- Automatic rollback on failure
- Transaction logging
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .coordinator import SRNEDataUpdateCoordinator

from .const import COMMAND_DELAY_WRITE

_LOGGER = logging.getLogger(__name__)


@dataclass
class WriteTransaction:
    """Represents a single write transaction."""

    entity_id: str
    register: int
    old_value: int | None
    new_value: int
    timestamp: datetime
    status: str  # 'pending', 'in_progress', 'committed', 'rolled_back', 'failed'
    error: str | None = None
    verified_value: int | None = None
    rollback_attempted: bool = False
    rollback_success: bool | None = None


@dataclass
class WriteResult:
    """Result of a write transaction."""

    success: bool
    error: str | None = None
    old_value: int | None = None
    new_value: int | None = None
    verified_value: int | None = None
    rollback_attempted: bool = False
    rollback_success: bool | None = None


class WriteTransactionManager:
    """Manages write transactions with rollback support.

    This manager ensures safe register writes by:
    1. Reading current value before write (for rollback)
    2. Writing new value to register
    3. Waiting for inverter processing
    4. Read-verifying written value
    5. Rolling back on verification failure
    6. Logging all transactions for audit

    Example:
        ```python
        transaction_mgr = WriteTransactionManager(coordinator)

        result = await transaction_mgr.execute_write(
            entity_id="battery_capacity",
            register=0xE002,
            value=200,
            scale=1.0
        )

        if result.success:
            print("Write successful")
        else:
            print(f"Write failed: {result.error}")
        ```
    """

    def __init__(self, coordinator: SRNEDataUpdateCoordinator) -> None:
        """Initialize transaction manager.

        Args:
            coordinator: Data update coordinator for register access
        """
        self._coordinator = coordinator
        self._active_transactions: dict[str, WriteTransaction] = {}
        self._history: list[WriteTransaction] = []
        self._transaction_lock = asyncio.Lock()

        _LOGGER.debug("WriteTransactionManager initialized")

    async def execute_write(
        self,
        entity_id: str,
        register: int,
        value: int,
        scale: float = 1.0,
        verify: bool = True,
    ) -> WriteResult:
        """Execute a register write with transaction logging and rollback.

        This method performs a complete write transaction:
        1. Validate inputs
        2. Read current value (for rollback)
        3. Write new value
        4. Wait for inverter processing (200ms)
        5. Read-verify written value (if verify=True)
        6. Rollback on failure

        Args:
            entity_id: Entity identifier for tracking
            register: Register address to write
            value: Scaled register value to write (0-65535)
            scale: Scaling factor for display (informational only)
            verify: Whether to read-verify after write

        Returns:
            WriteResult with success status and details

        Example:
            ```python
            # Write battery capacity (200 Ah)
            result = await mgr.execute_write(
                entity_id="battery_capacity",
                register=0xE002,
                value=200,  # Already scaled
                scale=1.0,
                verify=True
            )
            ```
        """
        # Validate inputs
        if not 0 <= value <= 0xFFFF:
            error_msg = f"Invalid register value: {value} (must be 0-65535)"
            _LOGGER.error(error_msg)
            return WriteResult(success=False, error=error_msg)

        if not 0 <= register <= 0xFFFF:
            error_msg = f"Invalid register address: 0x{register:04X}"
            _LOGGER.error(error_msg)
            return WriteResult(success=False, error=error_msg)

        # Use lock to prevent concurrent writes to same entity
        async with self._transaction_lock:
            # Check if transaction already active for this entity
            if entity_id in self._active_transactions:
                _LOGGER.debug(
                    "Transaction already active for %s, waiting for completion",
                    entity_id,
                )
                # In production, could implement queuing here
                return WriteResult(
                    success=False,
                    error=f"Transaction already active for {entity_id}",
                )

            # Step 1: Read current value for rollback capability
            _LOGGER.debug(
                "Step 1: Reading current value of register 0x%04X for rollback",
                register,
            )
            old_value = await self._read_register_value(register)

            if old_value is None:
                _LOGGER.debug(
                    "Could not read current value of register 0x%04X, proceeding without rollback capability",
                    register,
                )

            # Step 2: Create transaction record
            transaction = WriteTransaction(
                entity_id=entity_id,
                register=register,
                old_value=old_value,
                new_value=value,
                timestamp=datetime.now(timezone.utc),
                status="pending",
            )

            self._active_transactions[entity_id] = transaction

            try:
                # Step 3: Write new value to register
                _LOGGER.info(
                    "Step 2: Writing register 0x%04X = %d (entity: %s)",
                    register,
                    value,
                    entity_id,
                )
                transaction.status = "in_progress"

                write_success = await self._write_register_value(register, value)

                if not write_success:
                    transaction.status = "failed"
                    transaction.error = "Write command failed"
                    return WriteResult(
                        success=False,
                        error="Write command failed",
                        old_value=old_value,
                        new_value=value,
                    )

                # Step 4: Wait for inverter to process write (200ms)
                _LOGGER.debug("Step 3: Waiting 200ms for inverter to process write")
                await asyncio.sleep(0.2)

                # Step 5: Read-verify written value (if enabled)
                if verify:
                    _LOGGER.debug("Step 4: Read-verifying written value")
                    verified_value = await self._read_register_value(register)
                    transaction.verified_value = verified_value

                    if verified_value is None:
                        transaction.status = "failed"
                        transaction.error = "Read-verify failed: could not read register"

                        # Attempt rollback
                        if old_value is not None:
                            _LOGGER.debug(
                                "Verification failed, attempting rollback to %d",
                                old_value,
                            )
                            rollback_success = await self._rollback_write(
                                register, old_value
                            )
                            transaction.rollback_attempted = True
                            transaction.rollback_success = rollback_success

                        return WriteResult(
                            success=False,
                            error="Read-verify failed: could not read register",
                            old_value=old_value,
                            new_value=value,
                            verified_value=None,
                            rollback_attempted=transaction.rollback_attempted,
                            rollback_success=transaction.rollback_success,
                        )

                    # Check if verified value matches written value
                    if verified_value != value:
                        transaction.status = "failed"
                        transaction.error = (
                            f"Verification failed: wrote {value}, read {verified_value}"
                        )

                        # Attempt rollback
                        if old_value is not None:
                            _LOGGER.debug(
                                "Verification mismatch (wrote=%d, read=%d), "
                                "attempting rollback to %d",
                                value,
                                verified_value,
                                old_value,
                            )
                            rollback_success = await self._rollback_write(
                                register, old_value
                            )
                            transaction.rollback_attempted = True
                            transaction.rollback_success = rollback_success

                        return WriteResult(
                            success=False,
                            error=f"Verification failed: wrote {value}, read {verified_value}",
                            old_value=old_value,
                            new_value=value,
                            verified_value=verified_value,
                            rollback_attempted=transaction.rollback_attempted,
                            rollback_success=transaction.rollback_success,
                        )

                    _LOGGER.info(
                        "Step 5: Write verified successfully (register 0x%04X = %d)",
                        register,
                        verified_value,
                    )
                else:
                    _LOGGER.debug("Write verification skipped (verify=False)")
                    verified_value = None

                # Step 6: Success - commit transaction
                transaction.status = "committed"
                _LOGGER.info(
                    "Transaction committed successfully for %s (register 0x%04X)",
                    entity_id,
                    register,
                )

                return WriteResult(
                    success=True,
                    old_value=old_value,
                    new_value=value,
                    verified_value=verified_value,
                )

            except asyncio.TimeoutError:
                transaction.status = "failed"
                transaction.error = "Write timeout (exceeded 2 seconds)"
                _LOGGER.error(
                    "Write timeout for entity %s (register 0x%04X)",
                    entity_id,
                    register,
                )

                return WriteResult(
                    success=False,
                    error="Write timeout (exceeded 2 seconds)",
                    old_value=old_value,
                    new_value=value,
                )

            except Exception as err:
                transaction.status = "failed"
                transaction.error = f"Unexpected error: {type(err).__name__}: {err}"
                _LOGGER.exception(
                    "Unexpected error in write transaction for %s",
                    entity_id,
                )

                return WriteResult(
                    success=False,
                    error=f"Unexpected error: {type(err).__name__}: {err}",
                    old_value=old_value,
                    new_value=value,
                )

            finally:
                # Move transaction to history and remove from active
                self._history.append(transaction)
                del self._active_transactions[entity_id]

    async def rollback_transaction(self, entity_id: str) -> bool:
        """Manually rollback an active transaction.

        Args:
            entity_id: Entity identifier

        Returns:
            True if rollback successful, False otherwise
        """
        transaction = self._active_transactions.get(entity_id)

        if not transaction:
            _LOGGER.error("No active transaction found for entity %s", entity_id)
            return False

        if transaction.old_value is None:
            _LOGGER.error(
                "Cannot rollback transaction for %s: no old value available",
                entity_id,
            )
            return False

        _LOGGER.info(
            "Manually rolling back transaction for %s to value %d",
            entity_id,
            transaction.old_value,
        )

        rollback_success = await self._rollback_write(
            transaction.register, transaction.old_value
        )

        transaction.rollback_attempted = True
        transaction.rollback_success = rollback_success

        if rollback_success:
            transaction.status = "rolled_back"
        else:
            transaction.status = "failed"
            transaction.error = "Manual rollback failed"

        return rollback_success

    def get_transaction_history(
        self, entity_id: str | None = None, limit: int | None = None
    ) -> list[WriteTransaction]:
        """Get transaction history with optional filtering.

        Args:
            entity_id: Filter by entity ID (optional)
            limit: Maximum number of transactions to return (optional)

        Returns:
            List of WriteTransaction objects (most recent first)
        """
        history = self._history.copy()

        # Filter by entity_id if provided
        if entity_id:
            history = [t for t in history if t.entity_id == entity_id]

        # Sort by timestamp (most recent first)
        history.sort(key=lambda t: t.timestamp, reverse=True)

        # Apply limit if provided
        if limit:
            history = history[:limit]

        return history

    def get_active_transactions(self) -> dict[str, WriteTransaction]:
        """Get all active transactions.

        Returns:
            Dictionary mapping entity_id to WriteTransaction
        """
        return self._active_transactions.copy()

    def clear_history(self) -> None:
        """Clear transaction history (for testing/maintenance)."""
        _LOGGER.info("Clearing transaction history (%d entries)", len(self._history))
        self._history.clear()

    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================

    async def _read_register_value(self, register: int) -> int | None:
        """Read single register value from inverter.

        Args:
            register: Register address

        Returns:
            Register value or None on error
        """
        try:
            # Use coordinator's internal read method
            result = await self._coordinator._read_register(register, count=1)

            if result and "values" in result and len(result["values"]) > 0:
                return result["values"][0]
            else:
                _LOGGER.debug("Failed to read register 0x%04X", register)
                return None

        except Exception as err:
            _LOGGER.error(
                "Error reading register 0x%04X: %s",
                register,
                err,
            )
            return None

    async def _write_register_value(self, register: int, value: int) -> bool:
        """Write single register value to inverter.

        Args:
            register: Register address
            value: Value to write (0-65535)

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Use coordinator's write method with proper delay
            success = await self._coordinator.async_write_register(register, value)
            return success

        except Exception as err:
            _LOGGER.error(
                "Error writing register 0x%04X: %s",
                register,
                err,
            )
            return False

    async def _rollback_write(self, register: int, old_value: int) -> bool:
        """Attempt to rollback a failed write by restoring old value.

        Args:
            register: Register address
            old_value: Previous value to restore

        Returns:
            True if rollback succeeded, False otherwise
        """
        try:
            _LOGGER.debug(
                "Attempting rollback: restoring register 0x%04X to value %d",
                register,
                old_value,
            )

            # Write old value back
            success = await self._write_register_value(register, old_value)

            if not success:
                _LOGGER.error("Rollback write failed for register 0x%04X", register)
                return False

            # Wait for inverter to process
            await asyncio.sleep(0.2)

            # Verify rollback
            verified_value = await self._read_register_value(register)

            if verified_value is None:
                _LOGGER.error(
                    "Rollback verification failed: could not read register 0x%04X",
                    register,
                )
                return False

            if verified_value != old_value:
                _LOGGER.error(
                    "Rollback verification failed: wrote %d, read %d",
                    old_value,
                    verified_value,
                )
                return False

            _LOGGER.info(
                "Rollback successful: register 0x%04X restored to %d",
                register,
                old_value,
            )
            return True

        except Exception as err:
            _LOGGER.exception(
                "Error during rollback for register 0x%04X: %s",
                register,
                err,
            )
            return False
