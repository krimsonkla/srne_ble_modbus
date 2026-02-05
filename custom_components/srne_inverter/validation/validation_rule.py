"""Validation Rule abstract base class.

Abstract base class for all validation rules.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

from abc import ABC, abstractmethod
from typing import Any

from .validation_result import ValidationResult


class ValidationRule(ABC):
    """Abstract base class for validation rules.

    All validation rules must implement the validate() method which takes
    a value and context, returning a ValidationResult.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize validation rule.

        Args:
            config: Configuration dictionary from YAML
        """
        self.config = config
        self.error_message = config.get("error", "Validation failed")
        self.warning_message = config.get("warning")
        self.info_message = config.get("info")

    @abstractmethod
    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Validate a value against this rule.

        Args:
            value: The value to validate
            context: Validation context (entity values, coordinator data, etc.)

        Returns:
            ValidationResult with errors, warnings, and info
        """
