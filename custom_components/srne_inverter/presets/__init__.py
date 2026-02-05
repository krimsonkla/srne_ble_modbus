"""Configuration presets for SRNE Inverter.

This package provides pre-configured profiles for common use cases:
- Off-Grid Solar: Standalone solar + battery systems
- Grid-Tied Solar: Grid backup with solar priority
- UPS Mode: Grid power with battery backup
- Time-of-Use: Optimize for variable electricity rates

Users can also create custom presets by saving their current configuration.
"""

from .configuration_preset import ConfigurationPreset
from .preset_manager import PresetManager

__all__ = [
    "ConfigurationPreset",
    "PresetManager",
]
