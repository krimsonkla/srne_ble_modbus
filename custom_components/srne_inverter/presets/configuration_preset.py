"""Configuration preset dataclass for SRNE Inverter."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ConfigurationPreset:
    """Configuration preset for common use cases.

    Attributes:
        id: Unique preset identifier
        name: User-friendly preset name
        description: Detailed description of the preset
        icon: Material Design Icon identifier
        settings: Dictionary of register settings (register_id -> value)
        use_cases: List of use case descriptions
        warnings: List of warning messages to display before applying
        is_custom: Whether this is a user-created custom preset
    """

    id: str
    name: str
    description: str
    icon: str
    settings: dict[str, Any]
    use_cases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_custom: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert preset to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigurationPreset:
        """Create preset from dictionary."""
        return cls(**data)
