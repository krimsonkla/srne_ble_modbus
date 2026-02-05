"""Expression Validation rule.

Validate using a custom Python expression.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

import logging
from typing import Any

from .validation_rule import ValidationRule
from .validation_result import ValidationResult

_LOGGER = logging.getLogger(__name__)


class ExpressionValidation(ValidationRule):
    """Validate using a custom Python expression.

    YAML configuration:
        type: expression
        condition: "(value * battery_voltage / 12) < 16.0"
        variables:
          battery_voltage: battery_rated_voltage
        error: "Voltage exceeds maximum for battery type"
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Evaluate custom Python expression.

        Args:
            value: Value to validate
            context: Must contain 'coordinator' key

        Returns:
            ValidationResult indicating if expression evaluates to True
        """
        condition = self.config.get("condition")
        variables = self.config.get("variables", {})
        coordinator = context.get("coordinator")

        if not condition:
            return ValidationResult(
                valid=False,
                errors=["Invalid expression validation config: missing condition"],
            )

        if not coordinator:
            return ValidationResult(
                valid=False,
                errors=["Coordinator not available for expression validation"],
            )

        # Build evaluation context
        eval_context = {"value": value}

        # Add variables from coordinator data
        for var_name, entity_id in variables.items():
            var_value = coordinator.data.get(entity_id)
            if var_value is None:
                return ValidationResult(
                    valid=False,
                    errors=[
                        f"Variable '{var_name}' (entity '{entity_id}') not available"
                    ],
                )
            eval_context[var_name] = var_value

        # Evaluate expression
        try:
            result = eval(condition, {"__builtins__": {}}, eval_context)

            if not result:
                return ValidationResult(
                    valid=False,
                    errors=[
                        (
                            self.error_message.format(**eval_context)
                            if "{" in self.error_message
                            else self.error_message
                        )
                    ],
                )

            return ValidationResult(valid=True)

        except Exception as e:
            _LOGGER.error(
                "Error evaluating expression '%s': %s",
                condition,
                e,
            )
            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
            )
