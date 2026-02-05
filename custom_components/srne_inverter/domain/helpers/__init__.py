"""Domain helper functions."""

from .address_helpers import (
    address_in_range,
    calculate_register_count,
    format_address,
    parse_address,
)
from .transformations import (
    apply_precision,
    apply_scaling,
    convert_to_signed_int16,
    convert_to_unsigned_int16,
    encode_register_value,
    process_register_value,
)
from .validators import (
    ValidationError,
    validate_not_none,
    validate_range,
    validate_register_address,
    validate_register_value,
    validate_type,
)

__all__ = [
    # Address helpers
    "parse_address",
    "format_address",
    "address_in_range",
    "calculate_register_count",
    # Transformations
    "apply_scaling",
    "apply_precision",
    "convert_to_signed_int16",
    "convert_to_unsigned_int16",
    "process_register_value",
    "encode_register_value",
    # Validators
    "ValidationError",
    "validate_register_address",
    "validate_register_value",
    "validate_range",
    "validate_not_none",
    "validate_type",
]
