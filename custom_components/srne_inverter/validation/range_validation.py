"""Range Validation rule.

Validate that value is within a specified range.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

from typing import Any

from .validation_rule import ValidationRule
from .validation_result import ValidationResult


class RangeValidation(ValidationRule):
    """Validate that value is within a specified range.

    YAML configuration:
        type: range
        min: 0
        max: 100
        error: "Value must be between 0 and 100"
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Check if value is within min/max bounds.

        Args:
            value: Numeric value to validate
            context: Validation context (unused)

        Returns:
            ValidationResult indicating if value is in range
        """
        min_val = self.config.get("min")
        max_val = self.config.get("max")

        errors = []

        # Check minimum bound
        if min_val is not None and value < min_val:
            errors.append(
                self.error_message.format(value=value, min=min_val, max=max_val)
                if "{" in self.error_message
                else self.error_message
            )

        # Check maximum bound
        if max_val is not None and value > max_val:
            errors.append(
                self.error_message.format(value=value, min=min_val, max=max_val)
                if "{" in self.error_message
                else self.error_message
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors)
