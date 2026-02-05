"""Write Register Result DTO.

Data Transfer Object representing the result of a register write operation.
Extracted from write_register_use_case.py for one-class-per-file compliance.
Application Layer Cleanup
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WriteRegisterResult:
    """Result of register write operation.

    Attributes:
        success: Whether write was successful
        error: Error message if failed
        error_code: Modbus error code if applicable
        register: Register address that was written
        value: Value that was written
    """

    success: bool
    error: str = ""
    error_code: Optional[int] = None
    register: int = 0
    value: int = 0
