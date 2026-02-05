"""ICRC interface for CRC calculation algorithms.

Extracted from protocol.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod


class ICRC(ABC):
    """Interface for CRC calculation algorithms.

    CRC (Cyclic Redundancy Check) is used to detect transmission errors.
    Modbus RTU uses CRC-16 with polynomial 0xA001.

    Example:
        >>> crc = ModbusCRC16()
        >>> data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x01])
        >>> checksum = crc.calculate(data)
        >>> assert 0 <= checksum <= 0xFFFF
    """

    @abstractmethod
    def calculate(self, data: bytes) -> int:
        """Calculate CRC checksum for given data.

        Args:
            data: Byte array to calculate CRC for

        Returns:
            CRC checksum as 16-bit unsigned integer (0-65535)

        Raises:
            ValueError: If data is empty or invalid
        """
