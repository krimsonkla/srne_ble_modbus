"""Configuration page manager for organizing config flow pages."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class ConfigPageManager:
    """Manages configuration pages and their registers."""

    def __init__(self, config_pages: dict[str, Any], registers: dict[str, Any]):
        """
        Initialize the page manager.

        Args:
            config_pages: Page definitions from YAML
            registers: Register definitions from YAML
        """
        self.config_pages = config_pages or {}
        self.registers = registers or {}
        self._page_registers_cache: dict[str, list[tuple[str, dict]]] = {}

    def get_page_order(self) -> list[str]:
        """
        Get ordered list of page IDs.

        Returns:
            List of page IDs sorted by order field
        """
        pages = []
        for page_id, page_data in self.config_pages.items():
            order = page_data.get("order", 999)
            pages.append((order, page_id))

        pages.sort()
        return [page_id for _, page_id in pages]

    def get_page_metadata(self, page_id: str) -> dict[str, Any]:
        """
        Get metadata for a specific page.

        Args:
            page_id: Page identifier

        Returns:
            Page metadata including translations
        """
        return self.config_pages.get(page_id, {})

    def get_page_registers(
        self, page_id: str, current_values: dict[str, Any] | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Get all registers for a specific page.

        Args:
            page_id: Page identifier
            current_values: Current register values to check visibility

        Returns:
            List of (register_key, register_data) tuples sorted by display_order
        """
        # Check cache first
        if page_id in self._page_registers_cache:
            registers = self._page_registers_cache[page_id]
        else:
            # Build list of registers for this page
            registers = []
            for reg_key, reg_data in self.registers.items():
                config_flow = reg_data.get("config_flow", {})
                if config_flow.get("page") == page_id:
                    display_order = config_flow.get("display_order", 999)
                    registers.append((display_order, reg_key, reg_data))

            # Sort by display_order
            registers.sort()
            registers = [(key, data) for _, key, data in registers]

            # Cache the result
            self._page_registers_cache[page_id] = registers

        # Filter based on visibility if current_values provided
        if current_values is not None:
            visible_registers = []
            for reg_key, reg_data in registers:
                if self._is_register_visible(reg_key, reg_data, current_values):
                    visible_registers.append((reg_key, reg_data))
            return visible_registers

        return registers

    def _is_register_visible(
        self,
        reg_key: str,
        reg_data: dict[str, Any],
        current_values: dict[str, Any],
    ) -> bool:
        """
        Check if a register should be visible based on current values.

        Args:
            reg_key: Register key
            reg_data: Register data
            current_values: Current configuration values

        Returns:
            True if register should be shown
        """
        # For now, always show registers that have been read
        # In the future, we can add conditional visibility based on:
        # - Battery type (hide lead-acid settings for lithium)
        # - Working mode (hide grid-tie settings for off-grid)
        # - Other register values

        # Hide registers that haven't been read yet
        if reg_key not in current_values:
            return False

        return True

    def get_page_translation(self, page_id: str, lang: str = "en") -> dict[str, str]:
        """
        Get translations for a page.

        Args:
            page_id: Page identifier
            lang: Language code (default: en)

        Returns:
            Translation dictionary with title, description, warning
        """
        page_data = self.config_pages.get(page_id, {})
        translations = page_data.get("translations", {})
        return translations.get(lang, {})

    def get_danger_level(self, page_id: str) -> str:
        """
        Get danger level for a page.

        Args:
            page_id: Page identifier

        Returns:
            Danger level: safe, warning, dangerous, critical
        """
        page_data = self.config_pages.get(page_id, {})
        return page_data.get("danger_level", "safe")

    def requires_warning(self, page_id: str) -> bool:
        """
        Check if page requires a warning dialog.

        Args:
            page_id: Page identifier

        Returns:
            True if danger_level is dangerous or critical
        """
        danger_level = self.get_danger_level(page_id)
        return danger_level in ("dangerous", "critical")

    def get_warning_message(self, page_id: str, lang: str = "en") -> str:
        """
        Get warning message for a page.

        Args:
            page_id: Page identifier
            lang: Language code

        Returns:
            Warning message string
        """
        translations = self.get_page_translation(page_id, lang)
        return translations.get("warning", "")

    def clear_cache(self):
        """Clear the page registers cache."""
        self._page_registers_cache.clear()
