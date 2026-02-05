"""WriteRegisterUseCase for SRNE Inverter register writes.

This use case orchestrates the register write workflow:
1. Validate register address and value
2. Authenticate with password (if protected register)
3. Execute write via protocol/transport
4. Handle errors and report results

Extracted from coordinator.async_write_register() and _process_write_queue().
Application Layer Extraction
Extracted WriteRegisterResult DTO
"""

import logging
from typing import Optional

from ...domain.helpers.address_helpers import format_address
from ...domain.interfaces import ITransport, IProtocol
from ...domain.value_objects.exception_code import ExceptionCode
from ...const import (
    DEFAULT_SLAVE_ID,
    MODBUS_ERROR_CODES,
    MODBUS_RESPONSE_TIMEOUT,
    MODBUS_WRITE_TIMEOUT,
)
from .write_register_result import WriteRegisterResult

_LOGGER = logging.getLogger(__name__)


class WriteRegisterUseCase:
    """Use case for writing inverter registers.

    This use case encapsulates the register write workflow,
    which was previously embedded in coordinator methods.

    Responsibilities:
    - Validate register address and value
    - Handle password authentication for protected registers
    - Execute write via protocol/transport
    - Decode and interpret error responses
    - Provide detailed error messages

    Protected Registers:
    - Range 0xE000-0xE0FF requires password authentication
    - Password register: 0xE203

    Dependencies (injected):
    - transport: Handles low-level communication
    - protocol: Builds commands and decodes responses

    Example:
        >>> use_case = WriteRegisterUseCase(transport, protocol)
        >>> result = await use_case.execute(0xE003, 5000, password=4321)
        >>> if result.success:
        ...     print(f"Successfully wrote {result.value} to 0x{result.register:04X}")
    """

    # Protected register range
    PROTECTED_REGISTER_START = 0xE000
    PROTECTED_REGISTER_END = 0xE0FF
    PASSWORD_REGISTER = 0xE203

    # Valid register/value ranges
    MIN_REGISTER = 0x0000
    MAX_REGISTER = 0xFFFF
    MIN_VALUE = 0x0000
    MAX_VALUE = 0xFFFF

    def __init__(
        self,
        transport: ITransport,
        protocol: IProtocol,
    ):
        """Initialize use case with dependencies.

        Args:
            transport: Communication transport
            protocol: Modbus protocol implementation
        """
        self._transport = transport
        self._protocol = protocol

    async def execute(
        self,
        register: int,
        value: int,
        password: int = 0,
        slave_id: int = DEFAULT_SLAVE_ID,
    ) -> WriteRegisterResult:
        """Execute register write operation.

        Args:
            register: Register address to write
            value: Value to write (0-65535)
            password: Password for protected registers (default: 0 = no password)
            slave_id: Modbus slave ID (default: 1)

        Returns:
            WriteRegisterResult with success/error information

        Raises:
            ValueError: If register or value is out of valid range
        """
        # Step 1: Validate inputs
        if not self.MIN_REGISTER <= register <= self.MAX_REGISTER:
            raise ValueError(
                f"Invalid register address: {format_address(register)} "
                f"(must be {format_address(self.MIN_REGISTER)}-{format_address(self.MAX_REGISTER)})"
            )

        if not self.MIN_VALUE <= value <= self.MAX_VALUE:
            raise ValueError(
                f"Invalid register value: {value} (must be 0-{self.MAX_VALUE})"
            )

        # Step 2: Authenticate if protected register
        if self._is_protected_register(register):
            if password and password != 0:
                _LOGGER.info(
                    "Register 0x%04X is protected, authenticating with password",
                    register,
                )

                auth_result = await self._authenticate_with_password(password, slave_id)

                if not auth_result.success:
                    _LOGGER.error(
                        "Password authentication failed, cannot write to register 0x%04X. "
                        "Check password in integration settings.",
                        register,
                    )
                    return WriteRegisterResult(
                        success=False,
                        error=f"Authentication failed: {auth_result.error}",
                        error_code=auth_result.error_code,
                        register=register,
                        value=value,
                    )
            else:
                _LOGGER.warning(
                    "Attempting to write protected register 0x%04X without password. "
                    "This will likely fail. Configure password in integration settings.",
                    register,
                )

        # Step 3: Execute write
        return await self._write_register(register, value, slave_id)

    async def _authenticate_with_password(
        self,
        password: int,
        slave_id: int,
    ) -> WriteRegisterResult:
        """Authenticate with password before writing protected registers.

        Args:
            password: Password value
            slave_id: Modbus slave ID

        Returns:
            WriteRegisterResult indicating authentication success/failure
        """
        if password == 0:
            return WriteRegisterResult(
                success=True,
                register=self.PASSWORD_REGISTER,
                value=0,
            )

        _LOGGER.debug(
            "Sending password authentication to register 0x%04X", self.PASSWORD_REGISTER
        )

        # Build authentication command
        command = self._protocol.build_write_command(
            self.PASSWORD_REGISTER,
            password,
        )

        try:
            # Send authentication
            response = await self._transport.send(
                command, timeout=MODBUS_RESPONSE_TIMEOUT
            )
            decoded = self._protocol.decode_response(response)

            if decoded and "error" not in decoded:
                _LOGGER.debug("Password authentication successful")
                return WriteRegisterResult(
                    success=True,
                    register=self.PASSWORD_REGISTER,
                    value=password,
                )
            else:
                error_code = decoded.get("error") if decoded else None
                error_msg = self._get_error_message(error_code, self.PASSWORD_REGISTER)

                if error_code == ExceptionCode.ACKNOWLEDGE:
                    error_msg = (
                        "Incorrect password. "
                        "Try common defaults: 4321, 0000, 111111, or 1111"
                    )

                _LOGGER.error("Password authentication failed: %s", error_msg)

                return WriteRegisterResult(
                    success=False,
                    error=error_msg,
                    error_code=error_code,
                    register=self.PASSWORD_REGISTER,
                    value=password,
                )

        except Exception as err:
            _LOGGER.error("Password authentication error: %s", err)
            return WriteRegisterResult(
                success=False,
                error=f"Authentication error: {err}",
                register=self.PASSWORD_REGISTER,
                value=password,
            )

    async def _write_register(
        self,
        register: int,
        value: int,
        slave_id: int,
    ) -> WriteRegisterResult:
        """Write value to register.

        Args:
            register: Register address
            value: Value to write
            slave_id: Modbus slave ID

        Returns:
            WriteRegisterResult with success/error information
        """
        # Build write command
        command = self._protocol.build_write_command(register, value)

        _LOGGER.info(
            "Writing register 0x%04X = 0x%04X: %s",
            register,
            value,
            command.hex(),
        )

        try:
            # Send write command
            response = await self._transport.send(command, timeout=MODBUS_WRITE_TIMEOUT)
            decoded = self._protocol.decode_response(response)

            if decoded and "error" not in decoded:
                _LOGGER.info(
                    "Successfully wrote register 0x%04X = %d",
                    register,
                    value,
                )
                return WriteRegisterResult(
                    success=True,
                    register=register,
                    value=value,
                )
            else:
                error_code = decoded.get("error") if decoded else None
                error_msg = self._get_error_message(error_code, register, value)

                _LOGGER.error(
                    "Write to register 0x%04X failed: %s",
                    register,
                    error_msg,
                )

                return WriteRegisterResult(
                    success=False,
                    error=error_msg,
                    error_code=error_code,
                    register=register,
                    value=value,
                )

        except Exception as err:
            _LOGGER.error("Failed to write register 0x%04X: %s", register, err)
            return WriteRegisterResult(
                success=False,
                error=f"Write error: {err}",
                register=register,
                value=value,
            )

    def _is_protected_register(self, register: int) -> bool:
        """Check if register is in protected range.

        Args:
            register: Register address

        Returns:
            True if protected, False otherwise
        """
        return self.PROTECTED_REGISTER_START <= register <= self.PROTECTED_REGISTER_END

    def _get_error_message(
        self,
        error_code: Optional[int],
        register: int,
        value: Optional[int] = None,
    ) -> str:
        """Get human-readable error message for error code.

        Args:
            error_code: Modbus error code
            register: Register address
            value: Value (if applicable)

        Returns:
            Detailed error message
        """
        if error_code == ExceptionCode.GATEWAY_TARGET_NO_RESPONSE:
            return (
                "Permission denied. "
                "Configure inverter password in integration settings. "
                "Common passwords: 4321, 0000, 111111"
            )
        elif error_code == ExceptionCode.ACKNOWLEDGE:
            return "Incorrect password. " "Check password in integration settings."
        elif error_code == ExceptionCode.PASSWORD_PROTECTION:
            return "System locked. " "Configure password in integration settings."
        elif error_code == ExceptionCode.ILLEGAL_DATA_ADDRESS:
            return f"Illegal data address: {format_address(register)}"
        elif error_code == ExceptionCode.ILLEGAL_DATA_VALUE:
            if value is not None:
                return f"Value {value} out of range for register {format_address(register)}"
            else:
                return f"Value out of range for register {format_address(register)}"
        elif error_code == ExceptionCode.PARAMETER_READ_ONLY:
            return f"Read-only register: {format_address(register)}"
        elif error_code == ExceptionCode.MEMORY_PARITY_ERROR:
            return f"Cannot modify register {format_address(register)} during operation"
        elif error_code:
            # Look up error code in MODBUS_ERROR_CODES
            return MODBUS_ERROR_CODES.get(
                error_code,
                f"Unknown error 0x{error_code:02X}",
            )
        else:
            return "Timeout or invalid response"
