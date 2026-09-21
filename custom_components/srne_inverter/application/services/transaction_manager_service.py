"""TransactionManagerService for managing write operations.

This service tracks failed registers and signals when read batches need
rebuilding.

It used to own a write queue as well -- queue_write/next_transaction/
has_pending_writes/get_queue_size over an asyncio.Queue. That queue was
removed on 2026-09-21 because nothing outside its own unit tests ever called
it: coordinator.async_write_register() went straight to
WriteRegisterUseCase.execute(), so writes were never queued and never drained.
It read like coordination that existed, which is worse than none.

Overlapping reads and writes are serialised at the transport instead --
see BLETransport.send() -- which costs a write about one batch of waiting
(~0.85s) rather than up to a full refresh cycle (~19s).
"""

import logging
from typing import Set, Optional

from ...domain.interfaces import IFailedRegisterRepository

_LOGGER = logging.getLogger(__name__)


class TransactionManagerService:
    """Service for managing write transactions and failed registers.

    Maintains state about which registers have failed and should be excluded
    from reads.

    Responsibilities:
    - Track failed registers
    - Persist failed register state
    - Signal when batches need rebuilding

    Example:
        >>> manager = TransactionManagerService(repository)
        >>> await manager.mark_register_failed(0x0200)
        >>> failed = manager.get_failed_registers()
    """

    def __init__(
        self,
        failed_register_repository: Optional[IFailedRegisterRepository] = None,
    ):
        """Initialize transaction manager.

        Args:
            failed_register_repository: Repository for persisting failed registers
        """
        self._repository = failed_register_repository
        self._failed_registers: Set[int] = set()
        self._batches_need_rebuild = False

    async def mark_register_failed(self, register: int) -> None:
        """Mark a register as failed.

        Failed registers are excluded from batch reads and persisted
        to storage for cross-session memory.

        Args:
            register: Register address that failed

        Example:
            >>> await manager.mark_register_failed(0x0200)
            >>> assert 0x0200 in manager.get_failed_registers()
        """
        if register not in self._failed_registers:
            self._failed_registers.add(register)
            self._batches_need_rebuild = True

            _LOGGER.warning(
                "Marked register 0x%04X as failed, will exclude from future reads",
                register,
            )

            # Persist to storage
            if self._repository:
                await self._repository.save_failed_registers(
                    list(self._failed_registers)
                )

    async def mark_register_recovered(self, register: int) -> None:
        """Mark a previously failed register as recovered.

        Args:
            register: Register address that recovered

        Example:
            >>> await manager.mark_register_recovered(0x0200)
            >>> assert 0x0200 not in manager.get_failed_registers()
        """
        if register in self._failed_registers:
            self._failed_registers.remove(register)
            self._batches_need_rebuild = True

            _LOGGER.info(
                "Register 0x%04X recovered, will include in future reads",
                register,
            )

            # Persist to storage
            if self._repository:
                await self._repository.save_failed_registers(
                    list(self._failed_registers)
                )

    def get_failed_registers(self) -> Set[int]:
        """Get set of failed register addresses.

        Returns:
            Set of failed register addresses

        Example:
            >>> failed = manager.get_failed_registers()
            >>> for reg in failed:
            ...     print(f"Register 0x{reg:04X} is failed")
        """
        return self._failed_registers.copy()

    async def load_failed_registers(self) -> None:
        """Load failed registers from persistent storage.

        Called during initialization to restore failed register state
        from previous session.

        Example:
            >>> await manager.load_failed_registers()
            >>> # Failed registers from previous session now loaded
        """
        if not self._repository:
            _LOGGER.debug("No repository configured, cannot load failed registers")
            return

        try:
            failed = await self._repository.load_failed_registers()

            if failed:
                self._failed_registers = set(failed)
                self._batches_need_rebuild = True

                _LOGGER.info(
                    "Loaded %d failed registers from storage: %s",
                    len(self._failed_registers),
                    [f"0x{r:04X}" for r in sorted(self._failed_registers)],
                )
            else:
                _LOGGER.debug("No failed registers found in storage")

        except Exception as err:
            _LOGGER.error("Error loading failed registers: %s", err)
            self._failed_registers = set()

    def needs_batch_rebuild(self) -> bool:
        """Check if register batches need rebuilding.

        Returns True if failed registers have changed since last rebuild.

        Returns:
            True if batches need rebuilding

        Example:
            >>> if manager.needs_batch_rebuild():
            ...     # Rebuild batches excluding failed registers
            ...     manager.acknowledge_batch_rebuild()
        """
        return self._batches_need_rebuild

    def acknowledge_batch_rebuild(self) -> None:
        """Acknowledge that batches have been rebuilt.

        Resets the needs_rebuild flag.

        Example:
            >>> # After rebuilding batches
            >>> manager.acknowledge_batch_rebuild()
            >>> assert not manager.needs_batch_rebuild()
        """
        self._batches_need_rebuild = False
        _LOGGER.debug("Batch rebuild acknowledged")

    def clear_failed_registers(self) -> None:
        """Clear all failed registers (for testing/recovery).

        Example:
            >>> manager.clear_failed_registers()
            >>> assert len(manager.get_failed_registers()) == 0
        """
        count = len(self._failed_registers)
        self._failed_registers.clear()
        self._batches_need_rebuild = True

        _LOGGER.info("Cleared %d failed registers", count)

    def initialize_failed_registers(self, failed_registers: Set[int]) -> None:
        """Initialize failed registers from external source (e.g., coordinator storage).

        This is used when the coordinator loads failed registers from its own
        storage and needs to sync them to the transaction manager.

        Args:
            failed_registers: Set of failed register addresses

        Example:
            >>> manager.initialize_failed_registers({0x0110, 0x0111})
            >>> assert manager.needs_batch_rebuild()
        """
        if failed_registers:
            self._failed_registers = failed_registers.copy()
            self._batches_need_rebuild = True

            _LOGGER.debug(
                "Initialized %d failed registers from external source",
                len(self._failed_registers),
            )

    def get_statistics(self) -> dict:
        """Get transaction manager statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = manager.get_statistics()
            >>> print(f"Failed registers: {stats['failed_registers_count']}")
        """
        return {
            "failed_registers_count": len(self._failed_registers),
            "failed_registers": [f"0x{r:04X}" for r in sorted(self._failed_registers)],
            "needs_batch_rebuild": self._batches_need_rebuild,
        }
