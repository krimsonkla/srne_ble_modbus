"""RegisterInfoProtocol for register information.

Extracted from batch_strategy.py for one-class-per-file compliance.
Uses Protocol suffix per team consensus to distinguish from entity classes.
"""

from typing import Protocol


class RegisterInfoProtocol(Protocol):
    """Protocol for register information.

    This uses structural typing (Protocol) rather than inheritance,
    so any object with these attributes can be used.
    """

    address: int  # Register address (0x0000 - 0xFFFF)
    name: str  # Register name for logging
