"""Enum Validation rule.

Validate that value is in an allowed set of values.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

from typing import Any

from .validation_rule import ValidationRule
from .validation_result import ValidationResult


class EnumValidation(ValidationRule):
    """Validate that value is in an allowed set of values.

    YAML configuration:
        type: enum
        allowed: [12, 24, 36, 48]
        error: "Battery voltage must be 12V, 24V, 36V, or 48V"
        level: warning  # Optional: 'error' (default) or 'warning'
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Check if value is in allowed set.

        Args:
            value: Value to validate
            context: Validation context (unused)

        Returns:
            ValidationResult indicating if value is in allowed set
        """
        allowed = self.config.get("allowed", [])
        level = self.config.get("level", "error")

        if value not in allowed:
            message = (
                self.error_message.format(value=value, allowed=allowed)
                if "{" in self.error_message
                else self.error_message
            )

            # Check if this is a warning (non-blocking) or error (blocking)
            if level == "warning":
                return ValidationResult(valid=True, warnings=[message])
            else:
                return ValidationResult(valid=False, errors=[message])

        return ValidationResult(valid=True)
