"""Configuration loader for entity definitions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def load_entity_config(
    hass: HomeAssistant,
    entry: ConfigEntry,
    config_filename: str = "entities.yaml",
) -> dict[str, Any]:
    """Load and validate entity configuration from YAML.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        config_filename: Name of config file to load (default: entities.yaml)

    Returns:
        Validated configuration dict

    Raises:
        ValueError: If configuration is invalid
        FileNotFoundError: If configuration file not found
    """
    # Get configuration file path
    integration_dir = Path(__file__).parent
    config_file = integration_dir / "config" / config_filename

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    # Load YAML asynchronously
    try:
        config = await hass.async_add_executor_job(
            lambda: yaml.safe_load(config_file.read_text())
        )
    except yaml.YAMLError as err:
        raise ValueError(f"Invalid YAML: {err}") from err

    if not config:
        raise ValueError("Configuration file is empty")

    # Require version 2.0
    if "version" not in config:
        raise ValueError("Configuration missing required 'version' field")

    version = str(config.get("version"))
    if not version.startswith("2."):
        raise ValueError(
            f"Configuration version {version} not supported. Only version 2.0+ is supported."
        )

    config["_version"] = version

    # Validate device profile and process register definitions
    _validate_device_profile(config)
    _process_register_definitions(config)

    # Apply defaults
    defaults = config.get("defaults", {})
    for entity_type in ["sensors", "switches", "selects", "binary_sensors", "numbers"]:
        for entity in config.get(entity_type, []):
            for key, value in defaults.items():
                if key not in entity:
                    entity[key] = value

    # Validate required fields
    _validate_configuration(config)

    _LOGGER.info(
        "Loaded entity configuration: %d sensors, %d switches, %d selects, %d binary sensors",
        len(config.get("sensors", [])),
        len(config.get("switches", [])),
        len(config.get("selects", [])),
        len(config.get("binary_sensors", [])),
    )

    return config


def _validate_configuration(config: dict[str, Any]) -> None:
    """Validate configuration structure.

    Args:
        config: Configuration dict to validate

    Raises:
        ValueError: If configuration is invalid
    """
    # Validate sensors
    for idx, sensor in enumerate(config.get("sensors", [])):
        _validate_entity_base(sensor, "sensor", idx)
        # Sensor-specific validation
        source_type = sensor.get("source_type", "register")
        if source_type == "calculated" and "formula" not in sensor:
            raise ValueError(
                f"Sensor #{idx} ({sensor.get('name', 'unknown')}): "
                "calculated source_type requires 'formula' field"
            )
        if source_type == "coordinator_data" and "data_key" not in sensor:
            raise ValueError(
                f"Sensor #{idx} ({sensor.get('name', 'unknown')}): "
                "coordinator_data source_type requires 'data_key' field"
            )

    # Validate switches
    for idx, switch in enumerate(config.get("switches", [])):
        _validate_entity_base(switch, "switch", idx)
        # Switch-specific validation
        if "on_value" not in switch:
            raise ValueError(
                f"Switch #{idx} ({switch.get('name', 'unknown')}): "
                "missing required field 'on_value'"
            )
        if "off_value" not in switch:
            raise ValueError(
                f"Switch #{idx} ({switch.get('name', 'unknown')}): "
                "missing required field 'off_value'"
            )
        # Must have either register or command_register
        if "register" not in switch and "command_register" not in switch:
            raise ValueError(
                f"Switch #{idx} ({switch.get('name', 'unknown')}): "
                "must have either 'register' or 'command_register'"
            )
        # Validate register reference
        if "register" in switch:
            reg_name = switch["register"]
            if not isinstance(reg_name, str):
                raise ValueError(
                    f"Switch #{idx} ({switch.get('name', 'unknown')}): "
                    f"'register' must be a string (register name)"
                )
            if reg_name not in config.get("_register_by_name", {}):
                raise ValueError(
                    f"Switch #{idx} ({switch.get('name', 'unknown')}): "
                    f"register '{reg_name}' not found in registers section"
                )

    # Validate selects
    for idx, select in enumerate(config.get("selects", [])):
        _validate_entity_base(select, "select", idx)
        # Select-specific validation
        if "options" not in select:
            raise ValueError(
                f"Select #{idx} ({select.get('name', 'unknown')}): "
                "missing required field 'options'"
            )
        if not isinstance(select["options"], dict):
            raise ValueError(
                f"Select #{idx} ({select.get('name', 'unknown')}): "
                "'options' must be a dictionary"
            )
        if "register" not in select:
            raise ValueError(
                f"Select #{idx} ({select.get('name', 'unknown')}): "
                "missing required field 'register'"
            )
        # Validate register reference
        if "register" in select:
            reg_name = select["register"]
            if not isinstance(reg_name, str):
                raise ValueError(
                    f"Select #{idx} ({select.get('name', 'unknown')}): "
                    f"'register' must be a string (register name)"
                )
            if reg_name not in config.get("_register_by_name", {}):
                raise ValueError(
                    f"Select #{idx} ({select.get('name', 'unknown')}): "
                    f"register '{reg_name}' not found in registers section"
                )

    # Validate binary sensors
    for idx, binary_sensor in enumerate(config.get("binary_sensors", [])):
        _validate_entity_base(binary_sensor, "binary_sensor", idx)


def _validate_device_profile(config: dict[str, Any]) -> None:
    """Validate device profile structure.

    Args:
        config: Configuration dict to validate

    Raises:
        ValueError: If device profile is invalid
    """
    # Validate device metadata
    if "device" not in config:
        raise ValueError("Configuration requires 'device' section with metadata")

    device = config["device"]
    required_fields = ["manufacturer", "model", "protocol_type"]
    for field in required_fields:
        if field not in device:
            raise ValueError(f"Device metadata missing required field: {field}")

    # Validate registers section
    if "registers" not in config:
        raise ValueError("Configuration requires 'registers' section with definitions")

    if not isinstance(config["registers"], dict):
        raise ValueError("'registers' section must be a dictionary")

    _LOGGER.info(
        "Device profile: %s %s (protocol: %s, registers: %d)",
        device.get("manufacturer"),
        device.get("model"),
        device.get("protocol_type"),
        len(config["registers"]),
    )


def _process_register_definitions(config: dict[str, Any]) -> None:
    """Process and validate register definitions.

    Args:
        config: Configuration dict with registers section

    Raises:
        ValueError: If register definitions are invalid
    """
    registers = config.get("registers", {})

    # Create lookup index for fast access
    config["_register_by_address"] = {}
    config["_register_by_name"] = {}

    for name, reg_def in registers.items():
        # Validate required fields
        if "address" not in reg_def:
            raise ValueError(f"Register '{name}' missing required field: address")
        if "type" not in reg_def:
            raise ValueError(f"Register '{name}' missing required field: type")

        # Validate type
        valid_types = ["read", "write", "read_write"]
        if reg_def["type"] not in valid_types:
            raise ValueError(
                f"Register '{name}' has invalid type: {reg_def['type']}. "
                f"Must be one of: {valid_types}"
            )

        # Convert address to int if needed
        address = reg_def["address"]
        if isinstance(address, str):
            address = int(address, 16 if address.startswith("0x") else 10)

        # Store in lookup indices
        config["_register_by_name"][name] = reg_def
        config["_register_by_address"][address] = {"name": name, "definition": reg_def}

        # Add normalized address to definition
        reg_def["_address_int"] = address


def get_register_definition(config: dict[str, Any], name: str) -> dict[str, Any] | None:
    """Get register definition by name.

    Args:
        config: Configuration dict from load_entity_config
        name: Register name

    Returns:
        Register definition dict or None if not found
    """
    return config.get("_register_by_name", {}).get(name)


def get_register_by_address(
    config: dict[str, Any], address: int
) -> dict[str, Any] | None:
    """Get register definition by address.

    Args:
        config: Configuration dict from load_entity_config
        address: Register address (int)

    Returns:
        Dict with 'name' and 'definition' keys, or None if not found
    """
    return config.get("_register_by_address", {}).get(address)


def _validate_entity_base(entity: dict[str, Any], entity_type: str, idx: int) -> None:
    """Validate base entity fields.

    Args:
        entity: Entity configuration dict
        entity_type: Type of entity (for error messages)
        idx: Index in list (for error messages)

    Raises:
        ValueError: If entity is invalid
    """
    # Required fields
    if "entity_id" not in entity:
        raise ValueError(
            f"{entity_type.capitalize()} #{idx}: missing required field 'entity_id'"
        )
    if "name" not in entity:
        raise ValueError(
            f"{entity_type.capitalize()} #{idx}: missing required field 'name'"
        )

    # Validate entity_id format
    entity_id = entity["entity_id"]
    if not isinstance(entity_id, str):
        raise ValueError(
            f"{entity_type.capitalize()} #{idx} ({entity.get('name', 'unknown')}): "
            "'entity_id' must be a string"
        )
    if not entity_id.replace("_", "").isalnum():
        raise ValueError(
            f"{entity_type.capitalize()} #{idx} ({entity.get('name', 'unknown')}): "
            f"'entity_id' contains invalid characters: {entity_id}"
        )
    if entity_id[0].isdigit():
        raise ValueError(
            f"{entity_type.capitalize()} #{idx} ({entity.get('name', 'unknown')}): "
            f"'entity_id' cannot start with a number: {entity_id}"
        )
