"""Domain entities for SRNE Inverter integration.

Entities are domain objects that have:
- Identity (can be distinguished by ID, even if all other attributes same)
- Mutable state (unlike value objects)
- Business logic and behavior
- Lifecycle (created, modified, deleted)

Key differences from value objects:
- Entities: Identity-based equality (same ID = same entity)
- Value Objects: Value-based equality (same values = equal)

Example:
    >>> # Two devices with same data are different entities
    >>> device1 = Device(id="dev1", name="Inverter")
    >>> device2 = Device(id="dev2", name="Inverter")
    >>> assert device1 != device2  # Different IDs

    >>> # Two addresses with same value are equal value objects
    >>> addr1 = RegisterAddress(0x0100)
    >>> addr2 = RegisterAddress(0x0100)
    >>> assert addr1 == addr2  # Same value
"""

from .register import Register
from .device import Device
from .register_batch import RegisterBatch
from .transaction_state import TransactionState
from .write_transaction import WriteTransaction

__all__ = [
    "Register",
    "Device",
    "RegisterBatch",
    "TransactionState",
    "WriteTransaction",
]
