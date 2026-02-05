"""Error handling decorators for standardized exception handling."""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable

from bleak import BleakError

from ...domain.exceptions import DeviceRejectedCommandError


def handle_transport_errors(
    operation_name: str,
    logger: logging.Logger = None,
    reraise: bool = True,
    default_return: Any = None,
):
    """Decorator for standardized transport error handling.

    Args:
        operation_name: Human-readable operation name for logging
        logger: Logger to use (defaults to function's module logger)
        reraise: Whether to re-raise exception after logging
        default_return: Value to return on error if not re-raising

    Example:
        @handle_transport_errors("BLE send", reraise=True)
        async def send(self, data: bytes) -> bytes:
            # Clean implementation without try/except
            await self._client.write_gatt_char(UUID, data)
            return await self._queue.get()
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            try:
                return await func(*args, **kwargs)
            except asyncio.TimeoutError as err:
                timeout_val = kwargs.get("timeout", "unknown")
                log.warning(
                    "%s timed out after %ss: %s",
                    operation_name,
                    timeout_val,
                    err,
                )
                if reraise:
                    raise
                return default_return
            except DeviceRejectedCommandError as err:
                # Expected device error - log without stack trace
                log.error("%s device error: %s", operation_name, err)
                if reraise:
                    raise
                return default_return
            except BleakError as err:
                log.error("%s BLE error: %s", operation_name, err)
                if reraise:
                    raise
                return default_return
            except Exception as err:
                log.error(
                    "%s unexpected error: %s",
                    operation_name,
                    err,
                    exc_info=True,
                )
                if reraise:
                    raise
                return default_return

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            log = logger or logging.getLogger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as err:
                log.error(
                    "%s error: %s",
                    operation_name,
                    err,
                    exc_info=True,
                )
                if reraise:
                    raise
                return default_return

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
