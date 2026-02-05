"""Tests for the dynamic config flow system."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import yaml

from custom_components.srne_inverter.config.schema_builder import (
    ConfigFlowSchemaBuilder,
)
from custom_components.srne_inverter.config.page_manager import ConfigPageManager
from custom_components.srne_inverter.config.selector_factory import SelectorFactory
from custom_components.srne_inverter.config.validation_engine import ValidationEngine


@pytest.fixture
def sample_config_data():
    """Create sample configuration data for testing."""
    return {
        "config_pages": {
            "test_page": {
                "order": 1,
                "icon": "mdi:test",
                "danger_level": "safe",
                "translations": {
                    "en": {
                        "title": "Test Page",
                        "description": "Test page description",
                    }
                },
            },
            "dangerous_page": {
                "order": 2,
                "icon": "mdi:alert",
                "danger_level": "dangerous",
                "translations": {
                    "en": {
                        "title": "Dangerous Page",
                        "description": "Dangerous settings",
                        "warning": "These settings can damage equipment",
                    }
                },
            },
        },
        "registers": {
            "test_number": {
                "address": 0xE001,
                "type": "read_write",
                "data_type": "uint16",
                "unit": "A",
                "min": 0,
                "max": 100,
                "scaling": 0.1,
                "default": 50,
                "config_flow": {
                    "page": "test_page",
                    "display_order": 1,
                    "danger_level": "safe",
                    "translations": {
                        "en": {
                            "title": "Test Number",
                            "description": "A test number field",
                            "hint": "Enter a value between 0 and 10",
                        }
                    },
                },
            },
            "test_select": {
                "address": 0xE002,
                "type": "read_write",
                "data_type": "uint16",
                "min": 0,
                "max": 2,
                "default": 0,
                "config_flow": {
                    "page": "test_page",
                    "display_order": 2,
                    "danger_level": "safe",
                    "translations": {
                        "en": {
                            "title": "Test Select",
                            "description": "A test select field",
                        }
                    },
                    "options": {
                        0: {"label": "Option A", "description": "First option"},
                        1: {"label": "Option B", "description": "Second option"},
                        2: {"label": "Option C", "description": "Third option"},
                    },
                },
            },
            "test_boolean": {
                "address": 0xE003,
                "type": "read_write",
                "data_type": "bool",
                "min": 0,
                "max": 1,
                "default": 0,
                "config_flow": {
                    "page": "test_page",
                    "display_order": 3,
                    "danger_level": "warning",
                    "translations": {
                        "en": {
                            "title": "Test Boolean",
                            "description": "A test boolean field",
                        }
                    },
                },
            },
            "test_with_validation": {
                "address": 0xE004,
                "type": "read_write",
                "data_type": "uint16",
                "unit": "V",
                "min": 0,
                "max": 60,
                "scaling": 0.1,
                "default": 48,
                "config_flow": {
                    "page": "dangerous_page",
                    "display_order": 1,
                    "danger_level": "dangerous",
                    "translations": {
                        "en": {
                            "title": "Test Validation",
                            "description": "Field with validation",
                        }
                    },
                    "validation": {
                        "must_be_less_than": "test_higher_value",
                        "warning_if_above": 55.0,
                    },
                },
            },
            "test_higher_value": {
                "address": 0xE005,
                "type": "read_write",
                "data_type": "uint16",
                "unit": "V",
                "min": 0,
                "max": 65,
                "scaling": 0.1,
                "default": 58,
                "config_flow": {
                    "page": "dangerous_page",
                    "display_order": 2,
                    "danger_level": "dangerous",
                    "translations": {
                        "en": {
                            "title": "Test Higher Value",
                            "description": "Must be higher than test_with_validation",
                        }
                    },
                },
            },
        },
        "config_validation": {
            "rules": [
                {
                    "name": "test_cross_field_validation",
                    "fields": ["test_with_validation", "test_higher_value"],
                    "condition": "test_with_validation < test_higher_value",
                    "translations": {
                        "en": {
                            "error": "test_with_validation must be less than test_higher_value"
                        }
                    },
                }
            ]
        },
    }


class TestSelectorFactory:
    """Test the SelectorFactory class."""

    def test_create_number_selector(self):
        """Test creating a number selector."""
        register = {
            "data_type": "uint16",
            "unit": "A",
            "min": 0,
            "max": 100,
            "scaling": 0.1,
        }

        selector = SelectorFactory.create_selector(register)
        assert selector is not None
        assert hasattr(selector, "config")

    def test_create_select_selector(self):
        """Test creating a select selector."""
        register = {
            "data_type": "uint16",
            "config_flow": {
                "options": {
                    0: {"label": "Option A"},
                    1: {"label": "Option B"},
                }
            },
        }

        selector = SelectorFactory.create_selector(register)
        assert selector is not None

    def test_create_boolean_selector(self):
        """Test creating a boolean selector."""
        register = {"data_type": "bool", "min": 0, "max": 1}

        selector = SelectorFactory.create_selector(register)
        assert selector is not None

    def test_get_default_value_with_scaling(self):
        """Test getting default value with scaling."""
        register = {"default": 50, "scaling": 0.1}

        default = SelectorFactory.get_default_value(register)
        assert default == 5.0  # 50 * 0.1

    def test_get_default_value_select(self):
        """Test getting default value for select field."""
        register = {
            "default": 1,
            "config_flow": {"options": {0: {"label": "A"}, 1: {"label": "B"}}},
        }

        default = SelectorFactory.get_default_value(register)
        assert default == "1"  # String value for select

    def test_parse_user_input_with_scaling(self):
        """Test parsing user input with scaling removal."""
        register = {"scaling": 0.1, "data_type": "uint16"}

        parsed = SelectorFactory.parse_user_input(register, 5.0)
        assert parsed == 50.0  # 5.0 / 0.1

    def test_parse_user_input_select(self):
        """Test parsing user input for select field."""
        register = {
            "config_flow": {"options": {0: {"label": "A"}, 1: {"label": "B"}}}
        }

        parsed = SelectorFactory.parse_user_input(register, "1")
        assert parsed == 1  # String to int

    def test_parse_user_input_boolean(self):
        """Test parsing user input for boolean field."""
        register = {"data_type": "bool", "min": 0, "max": 1}

        parsed_true = SelectorFactory.parse_user_input(register, True)
        parsed_false = SelectorFactory.parse_user_input(register, False)

        assert parsed_true == 1
        assert parsed_false == 0


class TestPageManager:
    """Test the ConfigPageManager class."""

    def test_get_page_order(self, sample_config_data):
        """Test getting ordered page list."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        pages = manager.get_page_order()
        assert len(pages) == 2
        assert pages[0] == "test_page"  # order: 1
        assert pages[1] == "dangerous_page"  # order: 2

    def test_get_page_metadata(self, sample_config_data):
        """Test getting page metadata."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        metadata = manager.get_page_metadata("test_page")
        assert metadata["order"] == 1
        assert metadata["icon"] == "mdi:test"
        assert metadata["danger_level"] == "safe"

    def test_get_page_registers(self, sample_config_data):
        """Test getting registers for a page."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        registers = manager.get_page_registers("test_page")
        assert len(registers) == 3
        # Check ordering
        assert registers[0][0] == "test_number"  # display_order: 1
        assert registers[1][0] == "test_select"  # display_order: 2
        assert registers[2][0] == "test_boolean"  # display_order: 3

    def test_get_page_registers_with_values(self, sample_config_data):
        """Test getting registers filtered by current values."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        # Only registers in current_values should be returned
        current_values = {"test_number": 5.0, "test_select": "1"}

        registers = manager.get_page_registers("test_page", current_values)
        assert len(registers) == 2
        assert registers[0][0] == "test_number"
        assert registers[1][0] == "test_select"

    def test_get_danger_level(self, sample_config_data):
        """Test getting danger level for a page."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        assert manager.get_danger_level("test_page") == "safe"
        assert manager.get_danger_level("dangerous_page") == "dangerous"

    def test_requires_warning(self, sample_config_data):
        """Test checking if page requires warning."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        assert not manager.requires_warning("test_page")  # safe
        assert manager.requires_warning("dangerous_page")  # dangerous

    def test_get_warning_message(self, sample_config_data):
        """Test getting warning message for a page."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        message = manager.get_warning_message("dangerous_page")
        assert message == "These settings can damage equipment"

    def test_get_page_translation(self, sample_config_data):
        """Test getting page translations."""
        manager = ConfigPageManager(
            sample_config_data["config_pages"], sample_config_data["registers"]
        )

        translation = manager.get_page_translation("test_page", "en")
        assert translation["title"] == "Test Page"
        assert translation["description"] == "Test page description"


class TestValidationEngine:
    """Test the ValidationEngine class."""

    def test_validate_field_range(self, sample_config_data):
        """Test basic range validation."""
        engine = ValidationEngine(sample_config_data["config_validation"])
        register = sample_config_data["registers"]["test_number"]

        # Valid value
        is_valid, error = engine.validate_field(
            "test_number", register, 5.0, {}
        )
        assert is_valid
        assert error is None

        # Too low (min is 0 * 0.1 = 0)
        is_valid, error = engine.validate_field(
            "test_number", register, -1.0, {}
        )
        assert not is_valid
        assert "between" in error

        # Too high (max is 100 * 0.1 = 10)
        is_valid, error = engine.validate_field(
            "test_number", register, 11.0, {}
        )
        assert not is_valid
        assert "between" in error

    def test_validate_field_must_be_less_than(self, sample_config_data):
        """Test must_be_less_than validation."""
        engine = ValidationEngine(sample_config_data["config_validation"])
        register = sample_config_data["registers"]["test_with_validation"]

        all_values = {"test_higher_value": 58.0}

        # Valid: 48.0 < 58.0
        is_valid, error = engine.validate_field(
            "test_with_validation", register, 48.0, all_values
        )
        assert is_valid

        # Invalid: 60.0 >= 58.0
        is_valid, error = engine.validate_field(
            "test_with_validation", register, 60.0, all_values
        )
        assert not is_valid
        assert "less than" in error

    def test_validate_all_fields(self, sample_config_data):
        """Test validating all fields including cross-field rules."""
        engine = ValidationEngine(sample_config_data["config_validation"])
        registers = sample_config_data["registers"]

        # Valid values
        values = {"test_with_validation": 48.0, "test_higher_value": 58.0}
        is_valid, errors = engine.validate_all_fields(values, registers)
        assert is_valid
        assert len(errors) == 0

        # Invalid: violates cross-field rule
        values = {"test_with_validation": 60.0, "test_higher_value": 58.0}
        is_valid, errors = engine.validate_all_fields(values, registers)
        assert not is_valid
        assert len(errors) > 0

    def test_is_safe_condition(self):
        """Test condition safety checker."""
        # Safe conditions
        assert ValidationEngine._is_safe_condition("10 < 20")
        assert ValidationEngine._is_safe_condition("5.5 >= 3.2")
        assert ValidationEngine._is_safe_condition("(10 + 5) <= 20")

        # Unsafe conditions
        assert not ValidationEngine._is_safe_condition("import os")
        assert not ValidationEngine._is_safe_condition("eval()")
        assert not ValidationEngine._is_safe_condition("__import__")


class TestConfigFlowSchemaBuilder:
    """Test the ConfigFlowSchemaBuilder class."""

    @pytest.fixture
    def temp_yaml_file(self, tmp_path, sample_config_data):
        """Create a temporary YAML file for testing."""
        yaml_file = tmp_path / "entities_pilot.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_config_data, f)
        return yaml_file

    def test_load_config_success(self, temp_yaml_file):
        """Test successfully loading configuration."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        success = builder.load_config()

        assert success
        assert builder._config_data is not None
        assert builder._page_manager is not None
        assert builder._validation_engine is not None

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading config with non-existent file."""
        builder = ConfigFlowSchemaBuilder(yaml_path=tmp_path / "nonexistent.yaml")
        success = builder.load_config()

        assert not success

    def test_get_pages(self, temp_yaml_file):
        """Test getting list of pages."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        pages = builder.get_pages()
        assert len(pages) == 2
        assert "test_page" in pages
        assert "dangerous_page" in pages

    def test_build_schema(self, temp_yaml_file):
        """Test building schema for a page."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        current_values = {
            "test_number": 5.0,
            "test_select": "1",
            "test_boolean": True,
        }

        schema = builder.build_schema("test_page", current_values)
        assert schema is not None
        assert len(schema.schema) == 3  # 3 registers on test_page

    def test_validate_user_input(self, temp_yaml_file):
        """Test validating user input."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        # Valid input
        user_input = {"test_with_validation": 48.0}
        all_values = {"test_with_validation": 48.0, "test_higher_value": 58.0}

        is_valid, errors = builder.validate_user_input(
            "dangerous_page", user_input, all_values
        )
        assert is_valid
        assert len(errors) == 0

        # Invalid input
        user_input = {"test_with_validation": 60.0}
        all_values = {"test_with_validation": 60.0, "test_higher_value": 58.0}

        is_valid, errors = builder.validate_user_input(
            "dangerous_page", user_input, all_values
        )
        assert not is_valid
        assert len(errors) > 0

    def test_parse_user_input(self, temp_yaml_file):
        """Test parsing user input."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        user_input = {
            "test_number": 5.0,  # Scaled value (display)
            "test_select": "1",  # String value
            "test_boolean": True,  # Boolean
        }

        parsed = builder.parse_user_input(user_input)

        assert parsed["test_number"] == 50.0  # Unscaled (5.0 / 0.1)
        assert parsed["test_select"] == 1  # Integer
        assert parsed["test_boolean"] == 1  # 1 for True

    def test_get_page_metadata(self, temp_yaml_file):
        """Test getting page metadata."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        metadata = builder.get_page_metadata("test_page")
        assert metadata["order"] == 1
        assert metadata["danger_level"] == "safe"

    def test_requires_warning(self, temp_yaml_file):
        """Test checking if page requires warning."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        assert not builder.requires_warning("test_page")
        assert builder.requires_warning("dangerous_page")

    def test_get_all_writable_registers(self, temp_yaml_file):
        """Test getting all writable registers."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        writable = builder.get_all_writable_registers()
        assert len(writable) == 5  # All test registers are read_write

    def test_get_register_by_address(self, temp_yaml_file):
        """Test getting register by address."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        result = builder.get_register_by_address(0xE001)
        assert result is not None
        key, data = result
        assert key == "test_number"
        assert data["address"] == 0xE001

        # Non-existent address
        result = builder.get_register_by_address(0xFFFF)
        assert result is None

    def test_get_register_translation(self, temp_yaml_file):
        """Test getting register translation."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        translation = builder.get_register_translation("test_number", "en")
        assert translation["title"] == "Test Number"
        assert translation["description"] == "A test number field"
        assert translation["hint"] == "Enter a value between 0 and 10"


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    @pytest.fixture
    def temp_yaml_file(self, tmp_path, sample_config_data):
        """Create a temporary YAML file for testing."""
        yaml_file = tmp_path / "entities_pilot.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_config_data, f)
        return yaml_file

    def test_complete_form_submission_flow(self, temp_yaml_file):
        """Test a complete form submission flow."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        # Step 1: Build schema
        current_values = {
            "test_number": 5.0,
            "test_select": "1",
            "test_boolean": True,
        }
        schema = builder.build_schema("test_page", current_values)
        assert schema is not None

        # Step 2: User submits form
        user_input = {
            "test_number": 7.5,  # New scaled value
            "test_select": "2",  # Changed option
            "test_boolean": False,  # Changed boolean
        }

        # Step 3: Validate input
        all_values = {**current_values, **user_input}
        is_valid, errors = builder.validate_user_input(
            "test_page", user_input, all_values
        )
        assert is_valid

        # Step 4: Parse input for register write
        parsed = builder.parse_user_input(user_input)
        assert parsed["test_number"] == 75.0  # Unscaled
        assert parsed["test_select"] == 2  # Integer
        assert parsed["test_boolean"] == 0  # 0 for False

    def test_cross_field_validation_scenario(self, temp_yaml_file):
        """Test cross-field validation scenario."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        # Set up initial values
        current_values = {
            "test_with_validation": 48.0,
            "test_higher_value": 58.0,
        }

        # User tries to set invalid values (validation should fail)
        user_input = {
            "test_with_validation": 60.0,  # Higher than test_higher_value
        }

        all_values = {**current_values, **user_input}
        is_valid, errors = builder.validate_user_input(
            "dangerous_page", user_input, all_values
        )

        assert not is_valid
        assert "test_with_validation" in errors

    def test_danger_level_workflow(self, temp_yaml_file):
        """Test danger level warning workflow."""
        builder = ConfigFlowSchemaBuilder(yaml_path=temp_yaml_file)
        builder.load_config()

        # Check if dangerous page requires warning
        assert builder.requires_warning("dangerous_page")

        # Get warning message
        warning = builder.get_warning_message("dangerous_page")
        assert "damage equipment" in warning

        # Get danger level
        level = builder.get_danger_level("dangerous_page")
        assert level == "dangerous"
