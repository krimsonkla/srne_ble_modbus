"""Config flow options pages."""

from .base import SRNEOptionsFlowHandler as BaseHandler
from .battery import BatteryOptionsMixin
from .inverter import InverterOptionsMixin
from .integration import IntegrationOptionsMixin
from .expert import ExpertOptionsMixin
from .hardware_features import HardwareFeaturesMixin


class SRNEOptionsFlowHandler(
    BatteryOptionsMixin,
    InverterOptionsMixin,
    IntegrationOptionsMixin,
    ExpertOptionsMixin,
    HardwareFeaturesMixin,
    BaseHandler,
):
    """Options flow handler with all mixins."""


__all__ = ["SRNEOptionsFlowHandler"]
