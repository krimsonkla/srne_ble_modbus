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
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinator import SRNEDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


# ============================================================================
# VALIDATION RESULT
# ============================================================================


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        valid: Whether validation passed (no errors)
        errors: List of error messages (blocking)
        warnings: List of warning messages (non-blocking)
        info: List of informational messages
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def merge(self, other: ValidationResult) -> None:
        """Merge another validation result into this one.

        Args:
            other: ValidationResult to merge
        """
        self.valid = self.valid and other.valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)

    def __str__(self) -> str:
        """Return string representation of validation result."""
        parts = []
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {', '.join(self.warnings)}")
        if self.info:
            parts.append(f"Info: {', '.join(self.info)}")
        return " | ".join(parts) if parts else "Valid"


# ============================================================================
# VALIDATION RULE BASE CLASS
# ============================================================================


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
    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
        """Validate a value against this rule.

        Args:
            value: The value to validate
            context: Validation context (entity values, coordinator data, etc.)

        Returns:
            ValidationResult with errors, warnings, and info
        """


# ============================================================================
# RANGE VALIDATION
# ============================================================================


class RangeValidation(ValidationRule):
    """Validate that value is within a specified range.

    YAML configuration:
        type: range
        min: 0
        max: 100
        error: "Value must be between 0 and 100"
    """

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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
                self.error_message.format(
                    value=value, min=min_val, max=max_val
                )
                if "{" in self.error_message
                else self.error_message
            )

        # Check maximum bound
        if max_val is not None and value > max_val:
            errors.append(
                self.error_message.format(
                    value=value, min=min_val, max=max_val
                )
                if "{" in self.error_message
                else self.error_message
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ============================================================================
# RELATIONSHIP VALIDATION
# ============================================================================


class RelationshipValidation(ValidationRule):
    """Validate relationship with another entity's value.

    YAML configuration:
        type: relationship
        entity: max_charge_current
        condition: "value <= related_value"
        error: "AC charge cannot exceed total charge current"
    """

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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
                errors=["Invalid relationship validation config: missing entity or condition"],
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
                        self.error_message.format(
                            value=value,
                            related_value=related_value,
                            related_entity=related_entity,
                        )
                        if "{" in self.error_message
                        else self.error_message
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


# ============================================================================
# CROSS-ENTITY VALIDATION
# ============================================================================


class CrossEntityValidation(ValidationRule):
    """Validate against multiple entity values.

    YAML configuration:
        type: cross_entity
        entities: [discharge_stop_soc, low_soc_alarm, switch_to_ac_soc]
        condition: "discharge_stop_soc < low_soc_alarm < switch_to_ac_soc"
        error: "SOC thresholds must be in ascending order"
    """

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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
                errors=["Invalid cross-entity validation config: missing entities or condition"],
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
                        errors=[f"Entity '{entity}' value not available for validation"],
                    )
                eval_context[entity] = entity_value

        # Evaluate condition
        try:
            result = eval(condition, {"__builtins__": {}}, eval_context)

            if not result:
                return ValidationResult(
                    valid=False,
                    errors=[
                        self.error_message.format(**eval_context)
                        if "{" in self.error_message
                        else self.error_message
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


# ============================================================================
# ENUM VALIDATION
# ============================================================================


class EnumValidation(ValidationRule):
    """Validate that value is in an allowed set of values.

    YAML configuration:
        type: enum
        allowed: [12, 24, 36, 48]
        error: "Battery voltage must be 12V, 24V, 36V, or 48V"
        level: warning  # Optional: 'error' (default) or 'warning'
    """

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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


# ============================================================================
# EXPRESSION VALIDATION
# ============================================================================


class ExpressionValidation(ValidationRule):
    """Validate using a custom Python expression.

    YAML configuration:
        type: expression
        condition: "(value * battery_voltage / 12) < 16.0"
        variables:
          battery_voltage: battery_rated_voltage
        error: "Voltage exceeds maximum for battery type"
    """

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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
                    errors=[f"Variable '{var_name}' (entity '{entity_id}') not available"],
                )
            eval_context[var_name] = var_value

        # Evaluate expression
        try:
            result = eval(condition, {"__builtins__": {}}, eval_context)

            if not result:
                return ValidationResult(
                    valid=False,
                    errors=[
                        self.error_message.format(**eval_context)
                        if "{" in self.error_message
                        else self.error_message
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


# ============================================================================
# SAFETY VALIDATION
# ============================================================================


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

    async def validate(
        self, value: Any, context: dict[str, Any]
    ) -> ValidationResult:
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


# ============================================================================
# VALIDATION FRAMEWORK
# ============================================================================


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

    def __init__(self, coordinator: SRNEDataUpdateCoordinator) -> None:
        """Initialize validation framework.

        Args:
            coordinator: Data update coordinator for accessing entity values
        """
        self._coordinator = coordinator
        self._rules: dict[str, list[ValidationRule]] = {}

    def register_rules(
        self, entity_id: str, rules: list[dict[str, Any]]
    ) -> None:
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

    async def validate(
        self, entity_id: str, value: Any
    ) -> ValidationResult:
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
