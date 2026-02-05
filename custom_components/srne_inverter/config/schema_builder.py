"""Dynamic schema builder for SRNE Inverter config flow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

from .page_manager import ConfigPageManager
from .selector_factory import SelectorFactory
from .validation_engine import ValidationEngine

_LOGGER = logging.getLogger(__name__)


class ConfigFlowSchemaBuilder:
    """Builds dynamic config flow schemas from YAML configuration."""

    def __init__(self, yaml_path: str | Path | None = None):
        """
        Initialize the schema builder.

        Args:
            yaml_path: Path to entities_pilot.yaml file
        """
        self.yaml_path = yaml_path
        self._config_data: dict[str, Any] | None = None
        self._page_manager: ConfigPageManager | None = None
        self._validation_engine: ValidationEngine | None = None

    def load_config(self) -> bool:
        """
        Load configuration from YAML file (lazy - only when first accessed).

        Returns:
            True if successful
        """
        # Already loaded - return immediately
        if self._config_data is not None:
            return True

        if self.yaml_path is None:
            # Auto-detect path
            config_dir = Path(__file__).parent
            self.yaml_path = config_dir / "entities_pilot.yaml"

        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                self._config_data = yaml.safe_load(f)

            # Initialize managers
            config_pages = self._config_data.get("config_pages", {})
            registers = self._config_data.get("registers", {})
            config_validation = self._config_data.get("config_validation", {})

            self._page_manager = ConfigPageManager(config_pages, registers)
            self._validation_engine = ValidationEngine(config_validation)

            _LOGGER.info(
                "Loaded config with %d pages and %d registers",
                len(config_pages),
                len(registers),
            )
            return True

        except Exception as e:
            _LOGGER.error("Failed to load YAML config: %s", str(e))
            return False

    def _ensure_config_loaded(self) -> bool:
        """
        Ensure config is loaded before use.

        Returns:
            True if config is loaded successfully
        """
        if self._config_data is None:
            return self.load_config()
        return True

    def get_pages(self) -> list[str]:
        """
        Get ordered list of config flow pages.

        Returns:
            List of page IDs
        """
        if not self._ensure_config_loaded():
            return []
        if self._page_manager is None:
            return []
        return self._page_manager.get_page_order()

    def build_schema(
        self,
        page_id: str,
        current_values: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """
        Build voluptuous schema for a config page.

        Args:
            page_id: Page identifier
            current_values: Current configuration values

        Returns:
            Voluptuous schema for the page
        """
        if not self._ensure_config_loaded():
            raise ValueError("Failed to load config")

        if self._page_manager is None or self._config_data is None:
            raise ValueError("Config not loaded. Call load_config() first.")

        registers = self._config_data.get("registers", {})
        page_registers = self._page_manager.get_page_registers(
            page_id, current_values
        )

        schema_dict = {}

        for reg_key, reg_data in page_registers:
            # Get current value for default
            if current_values and reg_key in current_values:
                default_value = current_values[reg_key]
            else:
                default_value = SelectorFactory.get_default_value(reg_data)

            # Create selector
            selector_obj = SelectorFactory.create_selector(reg_data)

            if selector_obj is None:
                _LOGGER.debug(
                    "Could not create selector for register %s", reg_key
                )
                continue

            # CRITICAL FIX: Convert default_value to string for select fields
            # Select options use string keys (e.g., "8") but coordinator returns
            # numeric values (e.g., 8). Must convert for proper matching.
            if default_value is not None:
                # Check if this is a select field (has "values" or "options")
                if reg_data.get("values") or reg_data.get("config_flow", {}).get("options"):
                    # Convert numeric default to string to match select option values
                    default_value = str(default_value)
                    _LOGGER.debug(
                        "Converted default value to string for select field %s: %s",
                        reg_key,
                        default_value,
                    )

            # Add to schema with optional wrapper and default
            if default_value is not None:
                schema_dict[vol.Optional(reg_key, default=default_value)] = (
                    selector_obj
                )
            else:
                schema_dict[vol.Optional(reg_key)] = selector_obj

        return vol.Schema(schema_dict)

    def validate_user_input(
        self,
        page_id: str,
        user_input: dict[str, Any],
        all_values: dict[str, Any],
    ) -> tuple[bool, dict[str, str]]:
        """
        Validate user input for a page.

        Args:
            page_id: Page identifier
            user_input: User input from form
            all_values: All current configuration values

        Returns:
            Tuple of (is_valid, error_dict)
        """
        if not self._ensure_config_loaded():
            return (True, {})

        if self._validation_engine is None or self._config_data is None:
            return (True, {})

        registers = self._config_data.get("registers", {})

        # Validate each field in user input
        errors = {}
        for key, value in user_input.items():
            if key in registers:
                is_valid, error_msg = self._validation_engine.validate_field(
                    key, registers[key], value, all_values
                )
                if not is_valid:
                    errors[key] = error_msg

        return (len(errors) == 0, errors)

    def parse_user_input(
        self, user_input: dict[str, Any]
    ) -> dict[str, int | float | bool]:
        """
        Parse user input values to raw register values.

        Args:
            user_input: User input from form (scaled values)

        Returns:
            Dictionary of raw register values (unscaled)
        """
        if not self._ensure_config_loaded() or self._config_data is None:
            return user_input

        registers = self._config_data.get("registers", {})
        parsed = {}

        for key, value in user_input.items():
            if key in registers:
                parsed[key] = SelectorFactory.parse_user_input(
                    registers[key], value
                )
            else:
                parsed[key] = value

        return parsed

    def get_page_metadata(self, page_id: str) -> dict[str, Any]:
        """
        Get metadata for a page.

        Args:
            page_id: Page identifier

        Returns:
            Page metadata
        """
        if not self._ensure_config_loaded():
            return {}
        if self._page_manager is None:
            return {}
        return self._page_manager.get_page_metadata(page_id)

    def get_page_translation(
        self, page_id: str, lang: str = "en"
    ) -> dict[str, str]:
        """
        Get translations for a page.

        Args:
            page_id: Page identifier
            lang: Language code

        Returns:
            Translation dictionary
        """
        if not self._ensure_config_loaded():
            return {}
        if self._page_manager is None:
            return {}
        return self._page_manager.get_page_translation(page_id, lang)

    def requires_warning(self, page_id: str) -> bool:
        """
        Check if page requires warning confirmation.

        Args:
            page_id: Page identifier

        Returns:
            True if warning required
        """
        if not self._ensure_config_loaded():
            return False
        if self._page_manager is None:
            return False
        return self._page_manager.requires_warning(page_id)

    def get_warning_message(self, page_id: str, lang: str = "en") -> str:
        """
        Get warning message for a page.

        Args:
            page_id: Page identifier
            lang: Language code

        Returns:
            Warning message
        """
        if not self._ensure_config_loaded():
            return ""
        if self._page_manager is None:
            return ""
        return self._page_manager.get_warning_message(page_id, lang)

    def get_danger_level(self, page_id: str) -> str:
        """
        Get danger level for a page.

        Args:
            page_id: Page identifier

        Returns:
            Danger level: safe, warning, dangerous, critical
        """
        if not self._ensure_config_loaded():
            return "safe"
        if self._page_manager is None:
            return "safe"
        return self._page_manager.get_danger_level(page_id)

    def get_register_translation(
        self, register_key: str, lang: str = "en"
    ) -> dict[str, str]:
        """
        Get translation for a register.

        Args:
            register_key: Register key
            lang: Language code

        Returns:
            Translation dictionary with title, description, hint
        """
        if not self._ensure_config_loaded() or self._config_data is None:
            return {}

        registers = self._config_data.get("registers", {})
        if register_key not in registers:
            return {}

        reg_data = registers[register_key]
        config_flow = reg_data.get("config_flow", {})
        translations = config_flow.get("translations", {})

        return translations.get(lang, {})

    def get_all_writable_registers(self) -> dict[str, dict[str, Any]]:
        """
        Get all writable registers from config.

        Returns:
            Dictionary of writable register definitions
        """
        if not self._ensure_config_loaded() or self._config_data is None:
            return {}

        registers = self._config_data.get("registers", {})
        writable = {}

        for key, data in registers.items():
            reg_type = data.get("type", "read")
            if reg_type in ("read_write", "write", "rw"):
                writable[key] = data

        return writable

    def get_register_by_address(self, address: int) -> tuple[str, dict] | None:
        """
        Get register by its address.

        Args:
            address: Register address (e.g., 0xE001)

        Returns:
            Tuple of (register_key, register_data) or None
        """
        if not self._ensure_config_loaded() or self._config_data is None:
            return None

        registers = self._config_data.get("registers", {})
        for key, data in registers.items():
            if data.get("address") == address:
                return (key, data)

        return None
