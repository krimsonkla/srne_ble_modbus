"""ModbusFrame value object.

Represents a complete Modbus RTU frame with validation.
"""

from dataclasses import dataclass
from typing import Optional

from .function_code import FunctionCode
from .exception_code import ExceptionCode


@dataclass(frozen=True)
class ModbusFrame:
    """Immutable Modbus RTU frame.

    Represents a complete Modbus RTU frame with all components.
    Can represent both requests and responses.

    Modbus RTU Frame Structure:
        Request:  [Slave ID][Function][Data...][CRC-16]
        Response: [Slave ID][Function][Data...][CRC-16]
        Error:    [Slave ID][Function+0x80][Exception Code][CRC-16]

    Attributes:
        slave_id: Modbus slave ID (typically 0x01)
        function_code: Modbus function code
        data: Frame data bytes (variable length)
        crc: CRC-16 checksum (2 bytes)

    Example:
        >>> # Read request frame
        >>> frame = ModbusFrame(
        ...     slave_id=0x01,
        ...     function_code=FunctionCode.READ_HOLDING_REGISTERS,
        ...     data=bytes([0x01, 0x00, 0x00, 0x01]),  # addr + count
        ...     crc=0xD404
        ... )
        >>> assert frame.is_request
        >>> assert not frame.is_error

        >>> # Error response frame
        >>> error_frame = ModbusFrame(
        ...     slave_id=0x01,
        ...     function_code=FunctionCode.ERROR_READ_HOLDING,
        ...     data=bytes([ExceptionCode.ILLEGAL_DATA_ADDRESS]),
        ...     crc=0x1234
        ... )
        >>> assert error_frame.is_error
    """

    slave_id: int
    function_code: FunctionCode
    data: bytes
    crc: int

    # Constants
    BLE_HEADER_SIZE = 8  # BLE framing adds 8-byte header
    BLE_HEADER_PREFIX = bytes([0xFE, 0xFF, 0x03, 0xFE])

    def __post_init__(self) -> None:
        """Validate frame components.

        Raises:
            ValueError: If any component is invalid
        """
        if not isinstance(self.slave_id, int) or not (0 <= self.slave_id <= 0xFF):
            raise ValueError(f"Slave ID must be 0-255, got {self.slave_id}")

        if not isinstance(self.function_code, (int, FunctionCode)):
            raise TypeError(
                f"Function code must be int or FunctionCode, "
                f"got {type(self.function_code).__name__}"
            )

        if not isinstance(self.data, (bytes, bytearray)):
            raise TypeError(f"Data must be bytes, got {type(self.data).__name__}")

        if not isinstance(self.crc, int) or not (0 <= self.crc <= 0xFFFF):
            raise ValueError(f"CRC must be 0-65535, got {self.crc}")

    @property
    def is_error(self) -> bool:
        """Check if frame is an error response.

        Error responses have the 0x80 bit set in function code.

        Returns:
            True if frame represents an error response

        Example:
            >>> frame = ModbusFrame(0x01, FunctionCode.ERROR_READ_HOLDING, b'\\x02', 0x1234)
            >>> assert frame.is_error is True
        """
        return (self.function_code & 0x80) == 0x80

    @property
    def is_request(self) -> bool:
        """Check if frame is a request (not response or error).

        Returns:
            True if frame is a request

        Example:
            >>> frame = ModbusFrame(0x01, FunctionCode.READ_HOLDING_REGISTERS, b'', 0x1234)
            >>> assert frame.is_request is True
        """
        return not self.is_error

    @property
    def exception_code(self) -> Optional[ExceptionCode]:
        """Get exception code if frame is error response.

        Returns:
            Exception code if error frame, None otherwise

        Example:
            >>> error_frame = ModbusFrame(0x01, 0x83, bytes([0x02]), 0x1234)
            >>> assert error_frame.exception_code == ExceptionCode.ILLEGAL_DATA_ADDRESS
        """
        if self.is_error and len(self.data) >= 1:
            try:
                return ExceptionCode(self.data[0])
            except ValueError:
                return None
        return None

    def to_bytes(self) -> bytes:
        """Convert frame to raw bytes (without BLE header).

        Returns:
            Complete Modbus RTU frame as bytes

        Example:
            >>> frame = ModbusFrame(0x01, 0x03, bytes([0x01, 0x00, 0x00, 0x01]), 0xD404)
            >>> raw = frame.to_bytes()
            >>> assert raw == bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x01, 0x04, 0xD4])
        """
        crc_bytes = self.crc.to_bytes(2, byteorder="little")  # CRC is little-endian
        return bytes([self.slave_id, self.function_code]) + self.data + crc_bytes

    def to_bytes_with_ble_header(self) -> bytes:
        """Convert frame to raw bytes with BLE framing header.

        The SRNE device uses an 8-byte BLE header before the Modbus frame:
        [0xFE][0xFF][0x03][0xFE][0x01][0x00][0x00][0x00][Modbus frame...]

        Returns:
            Complete frame with BLE header

        Example:
            >>> frame = ModbusFrame(0x01, 0x03, bytes([0x02]), 0x1234)
            >>> raw = frame.to_bytes_with_ble_header()
            >>> assert raw[:4] == bytes([0xFE, 0xFF, 0x03, 0xFE])
        """
        ble_header = self.BLE_HEADER_PREFIX + bytes([0x01, 0x00, 0x00, 0x00])
        return ble_header + self.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, has_ble_header: bool = True) -> "ModbusFrame":
        """Parse ModbusFrame from raw bytes.

        Args:
            data: Raw frame bytes (with or without BLE header)
            has_ble_header: True if data includes 8-byte BLE header

        Returns:
            Parsed ModbusFrame

        Raises:
            ValueError: If data is too short or invalid

        Example:
            >>> # With BLE header
            >>> raw = bytes([
            ...     0xFE, 0xFF, 0x03, 0xFE, 0x01, 0x00, 0x00, 0x00,  # BLE header
            ...     0x01, 0x03, 0x02, 0x01, 0xE6, 0xB9, 0xF8  # Modbus
            ... ])
            >>> frame = ModbusFrame.from_bytes(raw)
            >>> assert frame.slave_id == 0x01
            >>> assert frame.function_code == 0x03
        """
        # Remove BLE header if present
        if has_ble_header:
            if len(data) < cls.BLE_HEADER_SIZE:
                raise ValueError(
                    f"Data too short for BLE header, "
                    f"expected at least {cls.BLE_HEADER_SIZE} bytes, got {len(data)}"
                )
            data = data[cls.BLE_HEADER_SIZE :]

        # Minimum Modbus frame: slave + function + CRC = 4 bytes
        if len(data) < 4:
            raise ValueError(
                f"Modbus frame too short, minimum 4 bytes, got {len(data)}"
            )

        slave_id = data[0]
        function_code = FunctionCode(data[1])
        frame_data = data[2:-2]  # Everything except slave, function, and CRC
        crc = int.from_bytes(data[-2:], byteorder="little")

        return cls(
            slave_id=slave_id,
            function_code=function_code,
            data=frame_data,
            crc=crc,
        )

    def __str__(self) -> str:
        """String representation for logging."""
        error_str = " (ERROR)" if self.is_error else ""
        return (
            f"ModbusFrame(slave={self.slave_id:#04x}, "
            f"func={self.function_code:#04x}{error_str}, "
            f"data={len(self.data)} bytes)"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return (
            f"ModbusFrame(slave_id={self.slave_id:#04x}, "
            f"function_code={self.function_code:#04x}, "
            f"data={self.data.hex()}, crc={self.crc:#06x})"
        )
