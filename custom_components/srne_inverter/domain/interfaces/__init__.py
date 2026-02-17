"""Domain interfaces for SRNE Inverter integration.

This module defines the contracts (interfaces) that infrastructure implementations
must fulfill. Using these interfaces enables:
- Dependency Inversion: High-level policy doesn't depend on low-level details
- Testability: Easy to mock/fake implementations for testing
- Flexibility: Swap implementations (BLE → Serial, etc.) without changing domain logic
"""

from .i_crc import ICRC
from .i_protocol import IProtocol
from .i_transport import ITransport
from .i_connection_manager import IConnectionManager
from .i_repository import IRepository
from .i_failed_register_repository import IFailedRegisterRepository
from .register_info_protocol import RegisterInfoProtocol
from .register_batch_protocol import RegisterBatchProtocol
from .i_batch_strategy import IBatchStrategy
from .i_disabled_entity_service import IDisabledEntityService

__all__ = [
    "ICRC",
    "IProtocol",
    "ITransport",
    "IConnectionManager",
    "IRepository",
    "IFailedRegisterRepository",
    "RegisterInfoProtocol",
    "RegisterBatchProtocol",
    "IBatchStrategy",
    "IDisabledEntityService",
]
