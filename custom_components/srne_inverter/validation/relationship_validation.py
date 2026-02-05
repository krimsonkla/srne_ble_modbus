"""Relationship Validation rule.

Validate relationship with another entity's value.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..coordinator import SRNEDataUpdateCoordinator

from .validation_rule import ValidationRule
from .validation_result import ValidationResult

_LOGGER = logging.getLogger(__name__)


class RelationshipValidation(ValidationRule):
    """Validate relationship with another entity's value.

    YAML configuration:
        type: relationship
        entity: max_charge_current
        condition: "value <= related_value"
        error: "AC charge cannot exceed total charge current"
    """

    async def validate(self, value: Any, context: dict[str, Any]) -> ValidationResult:
        """Check relationship condition with related entity.

        Args:
            value: Value to validate
            context: Must contain 'coordinator' key

        Returns:
            ValidationResult indicating if relationship condition is met
        """
        related_entity = self.config.get("entity")
        condition = self.config.get("condition")
        coordinator = context.get("coordinator")

        if not related_entity or not condition:
            return ValidationResult(
                valid=False,
                errors=[
                    "Invalid relationship validation config: missing entity or condition"
                ],
            )

        if not coordinator:
            return ValidationResult(
                valid=False,
                errors=["Coordinator not available for relationship validation"],
            )

        # Get related entity value
        related_value = coordinator.data.get(related_entity)
        if related_value is None:
            return ValidationResult(
                valid=False,
                errors=[f"Related entity '{related_entity}' value not available"],
            )

        # Evaluate condition
        try:
            # Create safe evaluation context
            eval_context = {
                "value": value,
                "related_value": related_value,
            }
            result = eval(condition, {"__builtins__": {}}, eval_context)

            if not result:
                return ValidationResult(
                    valid=False,
                    errors=[
                        (
                            self.error_message.format(
                                value=value,
                                related_value=related_value,
                                related_entity=related_entity,
                            )
                            if "{" in self.error_message
                            else self.error_message
                        )
                    ],
                )

            return ValidationResult(valid=True)

        except Exception as e:
            _LOGGER.error(
                "Error evaluating relationship condition '%s': %s",
                condition,
                e,
            )
            return ValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"],
            )
