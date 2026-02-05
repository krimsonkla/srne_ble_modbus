"""IProtocol interface for Modbus protocol implementation.

Extracted from protocol.py for one-class-per-file compliance.
"""

from abc import ABC, abstractmethod
from typing import Dict


class IProtocol(ABC):
    """Interface for Modbus protocol implementation.

    The protocol implementation handles Modbus RTU framing, command building,
    and response parsing. It abstracts the low-level protocol details from
    higher-level business logic.

    Modbus RTU Frame Structure:
        Request:  [Slave ID][Function][Start Addr][Count][CRC-16]
        Response: [Slave ID][Function][Byte Count][Data...][CRC-16]
        Error:    [Slave ID][Function+0x80][Error Code][CRC-16]

    Example:
        >>> protocol = ModbusRTUProtocol(crc=ModbusCRC16())
        >>> command = protocol.build_read_command(address=0x0100, count=2)
        >>> response = await transport.send(command)
        >>> data = protocol.decode_response(response)
        >>> print(data)  # {0x0100: 486, 0x0101: 250}
    """

    @abstractmethod
    def build_read_command(self, start_address: int, count: int) -> bytes:
        """Build Modbus read holding registers command (function code 0x03).

        Args:
            start_address: Starting register address (0x0000 - 0xFFFF)
            count: Number of consecutive registers to read (1-125)

        Returns:
            Complete Modbus RTU frame ready to send over transport
            Format: [0x01][0x03][addr_hi][addr_lo][count_hi][count_lo][crc_lo][crc_hi]

        Raises:
            ValueError: If address or count is out of valid range

        Example:
            >>> cmd = protocol.build_read_command(0x0100, 1)
            >>> assert cmd[0] == 0x01  # Slave ID
            >>> assert cmd[1] == 0x03  # Function code (read holding)
            >>> assert len(cmd) == 8   # Command + CRC
        """

    @abstractmethod
    def build_write_command(self, address: int, value: int) -> bytes:
        """Build Modbus write single register command (function code 0x06).

        Args:
            address: Register address to write (0x0000 - 0xFFFF)
            value: 16-bit value to write (0x0000 - 0xFFFF)

        Returns:
            Complete Modbus RTU frame ready to send over transport
            Format: [0x01][0x06][addr_hi][addr_lo][val_hi][val_lo][crc_lo][crc_hi]

        Raises:
            ValueError: If address or value is out of valid range

        Example:
            >>> cmd = protocol.build_write_command(0x0100, 300)
            >>> assert cmd[0] == 0x01  # Slave ID
            >>> assert cmd[1] == 0x06  # Function code (write single)
        """

    @abstractmethod
    def decode_response(self, response: bytes) -> Dict[int, int]:
        """Decode Modbus response into register address-value pairs.

        This method handles:
        - BLE framing header removal (8 bytes: 0xFE 0xFF 0x03 0xFE ...)
        - CRC validation
        - Error response detection (function code with 0x80 bit set)
        - Multi-register response parsing

        Args:
            response: Raw response bytes from transport (includes BLE header)

        Returns:
            Dictionary mapping register addresses to decoded values
            Example: {0x0100: 486, 0x0101: 250}

        Raises:
            ValueError: If response is malformed or CRC invalid
            ModbusError: If device returned error response (exception code)

        Example:
            >>> # Successful response
            >>> response = bytes([
            ...     0xFE, 0xFF, 0x03, 0xFE, 0x01, 0x00, 0x00, 0x00,  # BLE header
            ...     0x01, 0x03, 0x04, 0x01, 0xE6, 0x00, 0xFA, 0x9F, 0x1C  # Modbus
            ... ])
            >>> result = protocol.decode_response(response)
            >>> assert result == {0x0100: 486, 0x0101: 250}

            >>> # Error response
            >>> error_response = bytes([
            ...     0xFE, 0xFF, 0x03, 0xFE, 0x01, 0x00, 0x00, 0x00,
            ...     0x01, 0x83, 0x02, 0xC0, 0xF1  # 0x83 = 0x03 | 0x80 (error)
            ... ])
            >>> protocol.decode_response(error_response)  # Raises ModbusError
        """
