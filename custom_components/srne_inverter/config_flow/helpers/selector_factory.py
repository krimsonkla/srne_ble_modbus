"""Selector factory for creating Home Assistant selectors from YAML configuration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)


class SelectorFactory:
    """Factory for creating Home Assistant selectors from register metadata."""

    @staticmethod
    def create_selector(register: dict[str, Any]) -> selector.Selector | None:
        """
        Create a Home Assistant selector from register metadata.

        Args:
            register: Register definition with metadata

        Returns:
            Home Assistant selector or None if unsupported
        """
        data_type = register.get("data_type", "uint16")
        scaling = register.get("scaling", 1)
        unit = register.get("unit", "")
        min_val = register.get("min", 0)
        max_val = register.get("max", 65535)
        values = register.get("values")
        options = register.get("config_flow", {}).get("options")

        # Check if this is a select/enum type (has values or options)
        if values or options:
            return SelectorFactory._create_select_selector(register, values, options)

        # Check if this is a boolean type
        if data_type == "bool" or (min_val == 0 and max_val == 1 and not scaling):
            return SelectorFactory._create_boolean_selector(register)

        # Otherwise, create a number selector
        return SelectorFactory._create_number_selector(
            register, min_val, max_val, scaling, unit, data_type
        )

    @staticmethod
    def _create_select_selector(
        register: dict[str, Any],
        values: dict[int, str] | None,
        options: dict[int, dict[str, str]] | None,
    ) -> selector.SelectSelector:
        """Create a select selector for enumerated values."""
        select_options = []

        if options:
            # Use detailed options from config_flow metadata
            for value, option_data in options.items():
                select_options.append(
                    selector.SelectOptionDict(
                        value=str(value),
                        label=option_data.get("label", str(value)),
                    )
                )
        elif values:
            # Use simple values mapping
            for value, label in values.items():
                select_options.append(
                    selector.SelectOptionDict(
                        value=str(value),
                        label=label,
                    )
                )

        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=select_options,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

    @staticmethod
    def _create_boolean_selector(register: dict[str, Any]) -> selector.BooleanSelector:
        """Create a boolean selector."""
        return selector.BooleanSelector()

    @staticmethod
    def _create_number_selector(
        register: dict[str, Any],
        min_val: float,
        max_val: float,
        scaling: float,
        unit: str,
        data_type: str,
    ) -> selector.NumberSelector:
        """Create a number selector with appropriate constraints."""
        # Determine step size based on scaling
        if scaling == 1:
            step = 1.0
        elif scaling == 0.1:
            step = 0.1
        elif scaling == 0.01:
            step = 0.01
        elif scaling == 0.001:
            step = 0.001
        else:
            step = scaling

        # Apply scaling to min/max if needed
        scaled_min = min_val * scaling
        scaled_max = max_val * scaling

        # Determine number mode based on range
        if scaled_max - scaled_min > 1000:
            mode = selector.NumberSelectorMode.BOX
        else:
            mode = selector.NumberSelectorMode.BOX

        config = {
            "min": scaled_min,
            "max": scaled_max,
            "step": step,
            "mode": mode,
        }

        # Add unit if specified
        if unit:
            config["unit_of_measurement"] = unit

        return selector.NumberSelector(selector.NumberSelectorConfig(**config))

    @staticmethod
    def parse_user_input(
        register: dict[str, Any], user_value: Any
    ) -> int | float | bool:
        """
        Parse user input value back to raw register value.

        Args:
            register: Register definition
            user_value: Value from user input (scaled)

        Returns:
            Raw value to write to register (unscaled)
        """
        if user_value is None:
            return None

        # For select/enum types, convert string back to int
        values = register.get("values")
        options = register.get("config_flow", {}).get("options")
        if values or options:
            try:
                return int(user_value)
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Invalid enum value %s for register %s",
                    user_value,
                    register.get("name"),
                )
                return None

        # For boolean types
        data_type = register.get("data_type", "uint16")
        min_val = register.get("min", 0)
        max_val = register.get("max", 65535)
        scaling = register.get("scaling", 1)

        if data_type == "bool" or (min_val == 0 and max_val == 1 and not scaling):
            return 1 if user_value else 0

        # For numeric types, remove scaling
        try:
            return user_value / scaling
        except (TypeError, ZeroDivisionError):
            _LOGGER.debug(
                "Invalid numeric value %s for register %s",
                user_value,
                register.get("name"),
            )
            return None
