"""Use cases for SRNE Inverter application.

Use cases represent application-specific business rules.
They orchestrate the flow of data to and from entities,
and direct entities to use their business rules.

Each use case should:
- Have a single public method (execute/handle)
- Accept input via data structures (DTOs)
- Return output via data structures (DTOs)
- Coordinate domain entities and services
- Be independent of frameworks

Extracted from coordinator.
One class per file.
"""

from .refresh_data_result import RefreshDataResult
from .refresh_data_use_case import RefreshDataUseCase
from .write_register_result import WriteRegisterResult
from .write_register_use_case import WriteRegisterUseCase

__all__ = [
    "RefreshDataResult",
    "RefreshDataUseCase",
    "WriteRegisterResult",
    "WriteRegisterUseCase",
]
