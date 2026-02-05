"""Validation Framework.

Main validation framework for register writes.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..coordinator import SRNEDataUpdateCoordinator

from .validation_result import ValidationResult
from .validation_rule import ValidationRule
from .range_validation import RangeValidation
from .relationship_validation import RelationshipValidation
from .cross_entity_validation import CrossEntityValidation
from .enum_validation import EnumValidation
from .expression_validation import ExpressionValidation
from .safety_validation import SafetyValidation

_LOGGER = logging.getLogger(__name__)


class ValidationFramework:
    """Main validation framework for register writes.

    This framework:
    - Parses validation rules from YAML configuration
    - Executes rules in order
    - Aggregates results (errors, warnings, info)
    - Supports async validation for cross-entity checks
    """

    # Mapping of rule types to validation classes
    RULE_TYPES = {
        "range": RangeValidation,
        "relationship": RelationshipValidation,
        "cross_entity": CrossEntityValidation,
        "enum": EnumValidation,
        "expression": ExpressionValidation,
        "safety": SafetyValidation,
    }

    def __init__(self, coordinator: "SRNEDataUpdateCoordinator") -> None:
        """Initialize validation framework.

        Args:
            coordinator: Data update coordinator for accessing entity values
        """
        self._coordinator = coordinator
        self._rules: dict[str, list[ValidationRule]] = {}

    def register_rules(self, entity_id: str, rules: list[dict[str, Any]]) -> None:
        """Register validation rules for an entity.

        Args:
            entity_id: Entity identifier
            rules: List of rule configurations from YAML
        """
        parsed_rules = []

        for rule_config in rules:
            rule_type = rule_config.get("type")
            if rule_type not in self.RULE_TYPES:
                _LOGGER.debug(
                    "Unknown validation rule type '%s' for entity '%s'",
                    rule_type,
                    entity_id,
                )
                continue

            # Create rule instance
            rule_class = self.RULE_TYPES[rule_type]
            rule = rule_class(rule_config)
            parsed_rules.append(rule)

        self._rules[entity_id] = parsed_rules
        _LOGGER.debug(
            "Registered %d validation rules for entity '%s'",
            len(parsed_rules),
            entity_id,
        )

    async def validate(self, entity_id: str, value: Any) -> ValidationResult:
        """Validate a value against all registered rules for an entity.

        Args:
            entity_id: Entity identifier
            value: Value to validate

        Returns:
            Aggregated ValidationResult
        """
        rules = self._rules.get(entity_id, [])

        if not rules:
            # No rules registered, validation passes
            return ValidationResult(valid=True)

        # Build validation context
        context = {
            "coordinator": self._coordinator,
            "entity_id": entity_id,
        }

        # Execute all rules
        result = ValidationResult(valid=True)

        for rule in rules:
            try:
                rule_result = await rule.validate(value, context)
                result.merge(rule_result)

            except Exception as e:
                _LOGGER.exception(
                    "Error executing validation rule for entity '%s': %s",
                    entity_id,
                    e,
                )
                result.valid = False
                result.errors.append(f"Validation error: {str(e)}")

        return result

    async def validate_with_rules(
        self, value: Any, rules: list[dict[str, Any]], entity_id: str | None = None
    ) -> ValidationResult:
        """Validate a value against a list of rules (without registration).

        Args:
            value: Value to validate
            rules: List of rule configurations
            entity_id: Optional entity identifier for context

        Returns:
            Aggregated ValidationResult
        """
        result = ValidationResult(valid=True)

        # Build validation context
        context = {
            "coordinator": self._coordinator,
            "entity_id": entity_id,
        }

        for rule_config in rules:
            rule_type = rule_config.get("type")
            if rule_type not in self.RULE_TYPES:
                _LOGGER.debug("Unknown validation rule type: %s", rule_type)
                continue

            # Create rule instance
            rule_class = self.RULE_TYPES[rule_type]
            rule = rule_class(rule_config)

            try:
                rule_result = await rule.validate(value, context)
                result.merge(rule_result)

            except Exception as e:
                _LOGGER.exception("Error executing validation rule: %s", e)
                result.valid = False
                result.errors.append(f"Validation error: {str(e)}")

        return result
