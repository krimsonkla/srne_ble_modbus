"""Config flow for SRNE HF Series Inverter integration.

This module has been refactored into separate files for better maintainability:
- config_flow/base.py: Shared utilities, validation, and constants
- config_flow/onboarding.py: Initial device setup and onboarding flow
- config_flow/options/: Options management and configuration updates
"""

from __future__ import annotations

# Re-export main classes for backward compatibility
from .config_flow.base import CONFIGURATION_PRESETS
from .config_flow.onboarding import SRNEConfigFlow
from .config_flow.options import SRNEOptionsFlowHandler

__all__ = [
    "CONFIGURATION_PRESETS",
    "SRNEConfigFlow",
    "SRNEOptionsFlowHandler",
]
