"""Cross-Entity Validation rule.

Validate against multiple entity values.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

import logging
from typing import Any

from .validation_rule import ValidationRule
from .validation_result import ValidationResult

_LOGGER = logging.getLogger(__name__)


class CrossEntityValidation(ValidationRule):
    """Validate against multiple entity values.

    YAML configuration:
        type: cross_entity
        entities: [discharge_stop_soc, low_soc_alarm, switch_to_ac_soc]
        condition: "discharge_stop_soc < low_soc_alarm < switch_to_ac_soc"
        error: "SOC thresholds must be in ascending order"
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Check condition across multiple entities.

        Args:
            value: Value to validate
            context: Must contain 'coordinator' and 'entity_id' keys

        Returns:
            ValidationResult indicating if cross-entity condition is met
        """
        entities = self.config.get("entities", [])
        condition = self.config.get("condition")
        coordinator = context.get("coordinator")
        current_entity_id = context.get("entity_id")

        if not entities or not condition:
            return ValidationResult(
                valid=False,
                errors=[
                    "Invalid cross-entity validation config: missing entities or condition"
                ],
            )

        if not coordinator:
            return ValidationResult(
                valid=False,
                errors=["Coordinator not available for cross-entity validation"],
            )

        # Build evaluation context with all entity values
        eval_context = {}
        for entity in entities:
            if entity == current_entity_id:
                # Use the value being validated for current entity
                eval_context[entity] = value
            else:
                # Get value from coordinator
                entity_value = coordinator.data.get(entity)
                if entity_value is None:
                    return ValidationResult(
                        valid=False,
                        errors=[
                            f"Entity '{entity}' value not available for validation"
                        ],
                    )
                eval_context[entity] = entity_value

        # Evaluate condition
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
                "Error evaluating cross-entity condition '%s': %s",
                condition,
                e,
            )
            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
            )
