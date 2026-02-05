"""RegisterBatchProtocol for batch information.

Extracted from batch_strategy.py for one-class-per-file compliance.
Uses Protocol suffix per team consensus to distinguish from RegisterBatch entity.
"""

from typing import List, Protocol

from .register_info_protocol import RegisterInfoProtocol


class RegisterBatchProtocol(Protocol):
    """Protocol for a batch of registers to read together.

    A batch represents a contiguous range of registers that can be
    read in a single Modbus request.
    """

    start_address: int  # First register address in batch
    count: int  # Number of consecutive registers
    registers: List[RegisterInfoProtocol]  # Registers included in this batch
