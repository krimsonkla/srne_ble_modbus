"""Connection management decorators."""

import inspect
import logging
from functools import wraps
from typing import Callable

_LOGGER = logging.getLogger(__name__)


def require_connection(
    address_param: str = "device_address",
    auto_disconnect: bool = False,
):
    """Decorator to ensure connection before operation.

    Args:
        address_param: Name of parameter containing device address
        auto_disconnect: Whether to disconnect after operation

    Example:
        @require_connection(address_param="device_address")
        async def execute(self, device_address: str, ...) -> Result:
            # Connection is guaranteed - just do work
            pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get device address from kwargs or args
            address = kwargs.get(address_param)
            if not address:
                # Try to find in args based on function signature
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if address_param in params:
                    idx = params.index(address_param) - 1  # -1 for self
                    if idx < len(args):
                        address = args[idx]

            if not address:
                raise ValueError(f"No {address_param} provided")

            # Ensure connection
            if not await self._connection_manager.ensure_connected(address):
                error_msg = f"Failed to connect to {address}"
                _LOGGER.error(error_msg)

                # Return appropriate error response based on return type
                return_annotation = func.__annotations__.get("return")
                if return_annotation is not None:
                    # Try to create a failure result object
                    try:
                        # Try with common Result constructor signatures
                        return return_annotation(
                            success=False, error=error_msg, data={}
                        )
                    except (TypeError, AttributeError):
                        try:
                            # Try alternative signature
                            return return_annotation(success=False, error=error_msg)
                        except (TypeError, AttributeError):
                            # Can't construct result, raise error
                            raise RuntimeError(error_msg)
                # No return type annotation, raise error
                raise RuntimeError(error_msg)

            try:
                return await func(self, *args, **kwargs)
            finally:
                if auto_disconnect and hasattr(self, "_transport"):
                    if self._transport.is_connected:
                        await self._transport.disconnect()

        return wrapper

    return decorator
