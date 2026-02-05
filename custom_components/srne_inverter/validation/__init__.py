"""Validation framework for configurable register writes.

This module provides a comprehensive validation system supporting:
- Range validation (min/max bounds)
- Relationship validation (compare with other entity values)
- Cross-entity validation (validate against multiple entities)
- Enum validation (allowed discrete values)
- Expression validation (custom Python expressions)
- Safety validation (warnings for critical settings)

Architecture:
- ValidationRule: Abstract base class for all validation rules
- ValidationResult: Result container with errors, warnings, and info messages
- ValidationFramework: Main framework for executing validation rules
- YAML-driven: Rules defined in entity configuration files

Extracted to separate files for one-class-per-file compliance.
"""

from .validation_result import ValidationResult
from .validation_rule import ValidationRule
from .range_validation import RangeValidation
from .relationship_validation import RelationshipValidation
from .cross_entity_validation import CrossEntityValidation
from .enum_validation import EnumValidation
from .expression_validation import ExpressionValidation
from .safety_validation import SafetyValidation
from .validation_framework import ValidationFramework

__all__ = [
    "ValidationResult",
    "ValidationRule",
    "RangeValidation",
    "RelationshipValidation",
    "CrossEntityValidation",
    "EnumValidation",
    "ExpressionValidation",
    "SafetyValidation",
    "ValidationFramework",
]
