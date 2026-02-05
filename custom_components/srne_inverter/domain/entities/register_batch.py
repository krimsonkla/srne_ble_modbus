"""RegisterBatch entity for grouped register reads.

A RegisterBatch represents a group of consecutive registers that can be
read in a single Modbus request.
"""

from dataclasses import dataclass, field
from typing import Any, List
from ..value_objects import RegisterAddress


@dataclass
class RegisterBatch:
    """Domain entity representing a batch of registers to read together.

    A batch must contain consecutive registers (no gaps) to be valid for
    a single Modbus read request.

    Attributes:
        start_address: First register address in batch
        count: Number of consecutive registers
        registers: List of Register entities in this batch
        priority: Batch priority (higher = read first)
        max_retries: Maximum retry attempts on failure

    Example:
        >>> from .register import Register
        >>> batch = RegisterBatch(
        ...     start_address=RegisterAddress(0x0100),
        ...     count=2,
        ...     registers=[
        ...         Register(RegisterAddress(0x0100), "battery_voltage"),
        ...         Register(RegisterAddress(0x0101), "battery_current"),
        ...     ],
        ... )
        >>> assert batch.is_valid()
        >>> assert batch.end_address.value == 0x0101
    """

    start_address: RegisterAddress
    count: int
    registers: List[Any] = field(default_factory=list)  # List[Register]
    priority: int = 0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Validate batch after initialization."""
        if self.count <= 0:
            raise ValueError(f"Batch count must be positive, got {self.count}")

        if self.count > 125:
            raise ValueError(
                f"Batch count exceeds Modbus limit of 125, got {self.count}"
            )

        # Note: We allow len(registers) < count because batches can have gaps.
        # For example, a batch might span 0x0100-0x0103 (count=4) but only
        # have registers at 0x0100 and 0x0103 (len=2), with a gap at 0x0101-0x0102.
        # This is intentional - we read the entire range and extract only the
        # registers we care about.
        if len(self.registers) > self.count:
            raise ValueError(
                f"Register list length ({len(self.registers)}) "
                f"exceeds count ({self.count})"
            )

    @property
    def end_address(self) -> RegisterAddress:
        """Get the last register address in batch.

        Returns:
            End address (start_address + count - 1)

        Example:
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=4,
            ... )
            >>> assert batch.end_address.value == 0x0103
        """
        return self.start_address + (self.count - 1)

    @property
    def address_range(self) -> range:
        """Get range of addresses in batch.

        Returns:
            Range from start to end address (inclusive)

        Example:
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=3,
            ... )
            >>> addresses = list(batch.address_range)
            >>> assert addresses == [0x0100, 0x0101, 0x0102]
        """
        return range(int(self.start_address), int(self.end_address) + 1)

    def is_valid(self) -> bool:
        """Validate that batch is properly formed.

        Checks:
        - Count is positive and within Modbus limits
        - Registers (if provided) don't exceed count
        - All registers fall within batch address range

        Note: Batches can have gaps, so len(registers) < count is valid.

        Returns:
            True if batch is valid

        Example:
            >>> from .register import Register
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=2,
            ...     registers=[
            ...         Register(RegisterAddress(0x0100), "reg1"),
            ...         Register(RegisterAddress(0x0101), "reg2"),
            ...     ],
            ... )
            >>> assert batch.is_valid()
        """
        # Basic validation
        if self.count <= 0 or self.count > 125:
            return False

        # If registers provided, validate they fall within batch range
        if len(self.registers) > 0:
            # Check registers don't exceed count
            if len(self.registers) > self.count:
                return False

            # Check all registers are within batch address range
            for register in self.registers:
                if not self.contains_address(int(register.address)):
                    return False

        return True

    def contains_address(self, address: int) -> bool:
        """Check if address is within this batch.

        Args:
            address: Register address to check

        Returns:
            True if address is in batch range

        Example:
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=4,
            ... )
            >>> assert batch.contains_address(0x0100)
            >>> assert batch.contains_address(0x0103)
            >>> assert not batch.contains_address(0x0104)
        """
        return address in self.address_range

    @property
    def register_map(self) -> dict[int, str]:
        """Build register map (offset -> name) from registers list.

        Returns:
            Dictionary mapping offset (from start_address) to register name

        Example:
            >>> from .register import Register
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=2,
            ...     registers=[
            ...         Register(RegisterAddress(0x0100), "reg1"),
            ...         Register(RegisterAddress(0x0101), "reg2"),
            ...     ],
            ... )
            >>> assert batch.register_map == {0: "reg1", 1: "reg2"}
        """
        result = {}
        for register in self.registers:
            offset = int(register.address) - int(self.start_address)
            result[offset] = register.name
        return result

    def split(self, max_size: int) -> List["RegisterBatch"]:
        """Split large batch into smaller batches.

        Args:
            max_size: Maximum registers per batch

        Returns:
            List of smaller batches

        Raises:
            ValueError: If max_size is invalid

        Example:
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=8,
            ... )
            >>> smaller = batch.split(max_size=4)
            >>> assert len(smaller) == 2
            >>> assert smaller[0].count == 4
            >>> assert smaller[1].count == 4
        """
        if max_size <= 0:
            raise ValueError(f"Max size must be positive, got {max_size}")

        if self.count <= max_size:
            return [self]

        batches = []
        current_address = self.start_address
        remaining_count = self.count
        register_index = 0

        while remaining_count > 0:
            batch_size = min(max_size, remaining_count)

            # Get registers for this batch
            batch_registers = []
            if self.registers:
                batch_registers = self.registers[
                    register_index : register_index + batch_size
                ]
                register_index += batch_size

            batch = RegisterBatch(
                start_address=current_address,
                count=batch_size,
                registers=batch_registers,
                priority=self.priority,
                max_retries=self.max_retries,
            )
            batches.append(batch)

            current_address = current_address + batch_size
            remaining_count -= batch_size

        return batches

    def to_dict(self) -> dict:
        """Convert batch to dictionary representation.

        Returns:
            Dictionary with batch attributes

        Example:
            >>> batch = RegisterBatch(
            ...     start_address=RegisterAddress(0x0100),
            ...     count=2,
            ... )
            >>> data = batch.to_dict()
            >>> assert data["start_address"] == 0x0100
            >>> assert data["count"] == 2
        """
        return {
            "start_address": int(self.start_address),
            "start_address_hex": self.start_address.to_hex(),
            "end_address": int(self.end_address),
            "end_address_hex": self.end_address.to_hex(),
            "count": self.count,
            "register_names": [r.name for r in self.registers],
            "priority": self.priority,
            "max_retries": self.max_retries,
            "is_valid": self.is_valid(),
        }

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"RegisterBatch({self.start_address.to_hex()}-"
            f"{self.end_address.to_hex()}, count={self.count})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"RegisterBatch(start_address={self.start_address!r}, "
            f"count={self.count}, registers={len(self.registers)})"
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on address range.

        Two batches are equal if they cover the same address range.

        Args:
            other: Object to compare with

        Returns:
            True if same address range
        """
        if not isinstance(other, RegisterBatch):
            return False
        return self.start_address == other.start_address and self.count == other.count

    def __hash__(self) -> int:
        """Hash based on address range for use in sets/dicts."""
        return hash((self.start_address, self.count))

    def __lt__(self, other: "RegisterBatch") -> bool:
        """Compare batches for sorting.

        Batches are sorted by:
        1. Priority (descending)
        2. Start address (ascending)

        Args:
            other: Other batch to compare

        Returns:
            True if self should come before other
        """
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority first
        return int(self.start_address) < int(other.start_address)
