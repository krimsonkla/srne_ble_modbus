"""Value Objects for SRNE Inverter domain.

Value Objects are immutable domain primitives that:
- Have no identity (equality based on value, not reference)
- Are immutable (cannot be changed after creation)
- Validate their invariants at construction
- Encapsulate related data and behavior

Benefits:
- Type safety (can't pass wrong type to functions)
- Self-validating (invalid states impossible)
- Explicit intent (RegisterAddress vs int makes code clearer)
- Immutability prevents accidental changes
"""

from .register_address import RegisterAddress
from .register_value import RegisterValue
from .device_state import DeviceState
from .function_code import FunctionCode
from .exception_code import ExceptionCode
from .modbus_frame import ModbusFrame

__all__ = [
    "RegisterAddress",
    "RegisterValue",
    "DeviceState",
    "FunctionCode",
    "ExceptionCode",
    "ModbusFrame",
]
