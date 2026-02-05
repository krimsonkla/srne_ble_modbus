"""Register Definition DTO.

Data Transfer Object representing a register definition from configuration.
Extracted from batch_builder_service.py for one-class-per-file compliance.
Application Layer Cleanup
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RegisterDefinition:
    """Represents a register definition from configuration.

    Attributes:
        name: Register name
        address: Register address
        length: Number of consecutive registers (for 32-bit values)
        definition: Full register definition from config
    """

    name: str
    address: int
    length: int
    definition: Dict[str, Any]
