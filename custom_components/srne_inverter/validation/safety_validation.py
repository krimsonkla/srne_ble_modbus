"""Safety Validation rule.

Safety check with configurable severity level.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

import logging
from typing import Any

from .validation_rule import ValidationRule
from .validation_result import ValidationResult

_LOGGER = logging.getLogger(__name__)


class SafetyValidation(ValidationRule):
    """Safety check with configurable severity level.

    YAML configuration:
        type: safety
        condition: "value < 10"
        warning: "Very deep discharge may reduce battery life"
        level: warning  # 'error', 'warning', or 'info'
        variables:
            battery_capacity: battery_capacity  # Optional
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Evaluate safety condition and return appropriate severity.

        Args:
            value: Value to validate
            context: Must contain 'coordinator' key

        Returns:
            ValidationResult with error, warning, or info based on level
        """
        condition = self.config.get("condition")
        level = self.config.get("level", "warning")
        variables = self.config.get("variables", {})
        coordinator = context.get("coordinator")

        if not condition:
            return ValidationResult(
                valid=False,
                errors=["Invalid safety validation config: missing condition"],
            )

        # Build evaluation context
        eval_context = {"value": value}

        # Add variables from coordinator data (if available)
        if coordinator:
            for var_name, entity_id in variables.items():
                var_value = coordinator.data.get(entity_id)
                if var_value is not None:
                    eval_context[var_name] = var_value

        # Evaluate condition
        try:
            result = eval(condition, {"__builtins__": {}}, eval_context)

            if not result:
                # Format message based on what's available
                if self.warning_message:
                    message = (
                        self.warning_message.format(**eval_context)
                        if "{" in self.warning_message
                        else self.warning_message
                    )
                elif self.error_message:
                    message = (
                        self.error_message.format(**eval_context)
                        if "{" in self.error_message
                        else self.error_message
                    )
                else:
                    message = "Safety check failed"

                # Return based on level
                if level == "error":
                    return ValidationResult(valid=False, errors=[message])
                elif level == "warning":
                    return ValidationResult(valid=True, warnings=[message])
                else:  # info
                    return ValidationResult(valid=True, info=[message])

            return ValidationResult(valid=True)

        except Exception as e:
            _LOGGER.error(
                "Error evaluating safety condition '%s': %s",
                condition,
                e,
            )
            # Safety validation errors are non-blocking by default
            return ValidationResult(
                valid=True,
                warnings=[f"Could not evaluate safety check: {str(e)}"],
            )
