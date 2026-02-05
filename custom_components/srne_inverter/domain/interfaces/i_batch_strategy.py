"""IBatchStrategy interface for register batching strategies.

Extracted from batch_strategy.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod
from typing import List

from .register_info_protocol import RegisterInfoProtocol
from .register_batch_protocol import RegisterBatchProtocol


class IBatchStrategy(ABC):
    """Interface for register batching strategies.

    Implementations of this interface determine how to group registers
    into efficient read batches. Different strategies can optimize for:
    - Minimum number of requests (larger batches)
    - Reliability (smaller batches, less failure impact)
    - Device limitations (max registers per request)

    Example:
        >>> strategy = FixedSizeBatchStrategy(max_batch_size=8)
        >>> batches = strategy.build_batches(registers)
        >>> for batch in batches:
        ...     print(f"Reading {batch.count} registers from 0x{batch.start_address:04X}")
    """

    @abstractmethod
    def build_batches(
        self, registers: List[RegisterInfoProtocol]
    ) -> List[RegisterBatchProtocol]:
        """Build optimal batches from list of registers.

        This method analyzes the register addresses and groups them into
        batches. Registers must be sorted by address.

        Strategy considerations:
        - Modbus can read max 125 registers per request (protocol limit)
        - Smaller batches are more reliable (less impact from single failure)
        - Larger batches are faster (fewer round trips)
        - Non-consecutive addresses require separate batches

        Args:
            registers: List of registers to batch, sorted by address

        Returns:
            List of batches, each containing consecutive registers

        Raises:
            ValueError: If registers list is empty or not sorted

        Example:
            >>> registers = [
            ...     Register(address=0x0100, name="battery_voltage"),
            ...     Register(address=0x0101, name="battery_current"),
            ...     Register(address=0x0103, name="battery_soc"),  # Gap!
            ...     Register(address=0x0104, name="battery_temp"),
            ... ]
            >>> batches = strategy.build_batches(registers)
            >>> # Result: 2 batches due to gap at 0x0102
            >>> assert len(batches) == 2
            >>> assert batches[0].start_address == 0x0100
            >>> assert batches[0].count == 2  # 0x0100-0x0101
            >>> assert batches[1].start_address == 0x0103
            >>> assert batches[1].count == 2  # 0x0103-0x0104
        """

    @abstractmethod
    def split_batch(self, batch: RegisterBatchProtocol) -> List[RegisterBatchProtocol]:
        """Split large batch into smaller batches.

        Used when a batch fails - split it into smaller batches and retry.
        This helps isolate problematic registers.

        Args:
            batch: Batch to split

        Returns:
            List of smaller batches covering same register range

        Example:
            >>> original = RegisterBatch(start_address=0x0100, count=8, registers=[...])
            >>> smaller_batches = strategy.split_batch(original)
            >>> # Could split into 2 batches of 4, or 4 batches of 2, etc.
            >>> assert sum(b.count for b in smaller_batches) == original.count
        """

    @property
    @abstractmethod
    def max_batch_size(self) -> int:
        """Get maximum registers per batch.

        Returns:
            Maximum number of registers this strategy will batch together

        Example:
            >>> strategy = FixedSizeBatchStrategy(max_batch_size=16)
            >>> assert strategy.max_batch_size == 16
        """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Get human-readable strategy name for logging.

        Returns:
            Strategy name (e.g., "fixed_size", "variable_size", "adaptive")

        Example:
            >>> print(f"Using {strategy.strategy_name} batching strategy")
        """
