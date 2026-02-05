"""Validation engine for cross-field config flow validation."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class ValidationEngine:
    """Handles validation of configuration values including cross-field validation."""

    def __init__(self, validation_rules: dict[str, Any]):
        """
        Initialize the validation engine.

        Args:
            validation_rules: Validation rules from YAML config_validation section
        """
        self.rules = validation_rules.get("rules", []) if validation_rules else []

    def validate_field(
        self,
        register_key: str,
        register_data: dict[str, Any],
        value: Any,
        all_values: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate a single field value.

        Args:
            register_key: Register key being validated
            register_data: Register metadata
            value: Value to validate
            all_values: All current configuration values

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic range validation
        min_val = register_data.get("min")
        max_val = register_data.get("max")
        scaling = register_data.get("scaling", 1)

        if min_val is not None and max_val is not None:
            scaled_min = min_val * scaling
            scaled_max = max_val * scaling

            try:
                num_value = float(value)
                if num_value < scaled_min or num_value > scaled_max:
                    return (
                        False,
                        f"Value must be between {scaled_min} and {scaled_max}",
                    )
            except (ValueError, TypeError):
                pass  # Not a numeric value, skip range check

        # Field-specific validation from config_flow metadata
        validation = register_data.get("config_flow", {}).get("validation", {})

        # Check must_be_less_than
        if "must_be_less_than" in validation:
            other_key = validation["must_be_less_than"]
            if other_key in all_values:
                try:
                    if float(value) >= float(all_values[other_key]):
                        return (
                            False,
                            f"Must be less than {other_key.replace('_', ' ')}",
                        )
                except (ValueError, TypeError):
                    pass

        # Check must_be_greater_than
        if "must_be_greater_than" in validation:
            other_key = validation["must_be_greater_than"]
            if other_key in all_values:
                try:
                    if float(value) <= float(all_values[other_key]):
                        return (
                            False,
                            f"Must be greater than {other_key.replace('_', ' ')}",
                        )
                except (ValueError, TypeError):
                    pass

        # Check must_be_less_than_or_equal_to
        if "must_be_less_than_or_equal_to" in validation:
            other_key = validation["must_be_less_than_or_equal_to"]
            if other_key in all_values:
                try:
                    if float(value) > float(all_values[other_key]):
                        return (
                            False,
                            f"Must be less than or equal to {other_key.replace('_', ' ')}",
                        )
                except (ValueError, TypeError):
                    pass

        # Check must_be_greater_than_or_equal_to
        if "must_be_greater_than_or_equal_to" in validation:
            other_key = validation["must_be_greater_than_or_equal_to"]
            if other_key in all_values:
                try:
                    if float(value) < float(all_values[other_key]):
                        return (
                            False,
                            f"Must be greater than or equal to {other_key.replace('_', ' ')}",
                        )
                except (ValueError, TypeError):
                    pass

        # Warning if above threshold (not an error, just a warning)
        if "warning_if_above" in validation:
            threshold = validation["warning_if_above"]
            try:
                if float(value) > threshold:
                    _LOGGER.debug(
                        "%s value %s exceeds recommended threshold %s",
                        register_key,
                        value,
                        threshold,
                    )
            except (ValueError, TypeError):
                pass

        return (True, None)

    def validate_all_fields(
        self, values: dict[str, Any], registers: dict[str, Any]
    ) -> tuple[bool, dict[str, str]]:
        """
        Validate all fields including cross-field validation.

        Args:
            values: All configuration values to validate
            registers: Register metadata

        Returns:
            Tuple of (all_valid, field_errors_dict)
        """
        errors = {}

        # Validate each field
        for key, value in values.items():
            if key in registers:
                is_valid, error_msg = self.validate_field(
                    key, registers[key], value, values
                )
                if not is_valid:
                    errors[key] = error_msg

        # Apply global cross-field validation rules
        for rule in self.rules:
            rule_errors = self._apply_validation_rule(rule, values)
            errors.update(rule_errors)

        return (len(errors) == 0, errors)

    def _apply_validation_rule(
        self, rule: dict[str, Any], values: dict[str, Any]
    ) -> dict[str, str]:
        """
        Apply a global validation rule.

        Args:
            rule: Validation rule definition
            values: Current configuration values

        Returns:
            Dictionary of field errors
        """
        errors = {}

        fields = rule.get("fields", [])
        condition = rule.get("condition", "")
        translations = rule.get("translations", {})
        error_msg = translations.get("en", {}).get("error", "Validation failed")

        # Check if all fields are present
        if not all(field in values for field in fields):
            return errors

        # Evaluate the condition
        # For safety, we only support a limited set of simple conditions
        try:
            # Replace field names with their values in the condition
            eval_condition = condition
            for field in fields:
                eval_condition = eval_condition.replace(field, str(values[field]))

            # Safely evaluate simple comparison expressions
            # Only allow comparisons, no function calls or complex expressions
            if not self._is_safe_condition(eval_condition):
                _LOGGER.error("Unsafe validation condition: %s", condition)
                return errors

            # Evaluate the condition
            if not eval(eval_condition, {"__builtins__": {}}, {}):
                # Condition failed, add error to first field
                errors[fields[0]] = error_msg

        except Exception as e:
            _LOGGER.error(
                "Error evaluating validation rule %s: %s",
                rule.get("name"),
                str(e),
            )

        return errors

    @staticmethod
    def _is_safe_condition(condition: str) -> bool:
        """
        Check if a condition expression is safe to evaluate.

        Args:
            condition: Condition string to check

        Returns:
            True if condition appears safe
        """
        # Only allow numbers, operators, parentheses, and whitespace
        allowed_chars = set("0123456789.<>=!()&| \t")
        return all(c in allowed_chars for c in condition)

    def get_typical_range(
        self, register_data: dict[str, Any], battery_voltage: int | None = None
    ) -> tuple[float, float] | None:
        """
        Get typical/recommended range for a register.

        Args:
            register_data: Register metadata
            battery_voltage: Current battery system voltage (12/24/48V)

        Returns:
            Tuple of (min, max) typical values or None
        """
        validation = register_data.get("config_flow", {}).get("validation", {})

        # Check for voltage-dependent typical ranges
        typical_range = validation.get("typical_range")
        if isinstance(typical_range, dict) and battery_voltage:
            voltage_key = f"{battery_voltage}V"
            if voltage_key in typical_range:
                return tuple(typical_range[voltage_key])
        elif isinstance(typical_range, list) and len(typical_range) == 2:
            return tuple(typical_range)

        return None
