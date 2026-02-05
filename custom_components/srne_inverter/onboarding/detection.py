"""Hardware feature detection for SRNE Inverter."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable

_LOGGER = logging.getLogger(__name__)

# Test registers for each feature group
# Strategy: Test one representative register per feature to detect dash pattern (0x2D2D)
FEATURE_TEST_REGISTERS = {
    "grid_tie": 0xE400,  # GridActivePowerSet
    "diesel_mode": 0xE21F,  # GenWorkMode
    "three_phase": 0x238,  # AC power phase-B current
    "split_phase": 0x228,  # PBusVolt
    "parallel_operation": 0x226,  # Parallel current
    "timed_operation": 0xE02C,  # Timed segment 1
    "advanced_output": 0xE21C,  # MaxLineCurrent
    "customized_models": 0x227,  # ChargeStatus
}


class FeatureDetector:
    """Detects hardware features by testing specific registers.

    This service probes representative registers from each feature group
    to determine hardware capabilities. Unsupported features return the
    dash pattern (0x2D2D) or timeout.
    """

    def __init__(self, coordinator) -> None:
        """Initialize feature detector.

        Args:
            coordinator: The SRNE data update coordinator for register access
        """
        self._coordinator = coordinator
        self._progress_callback: Callable[[str, int, int], None] | None = None

    async def detect_all_features(
        self,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> dict[str, bool]:
        """Detect all features with optional progress updates.

        Args:
            progress_callback: Optional callback(feature_name, current, total)

        Returns:
            Dictionary mapping feature names to detection results
        """
        self._progress_callback = progress_callback
        results = {}
        total_features = len(FEATURE_TEST_REGISTERS)

        _LOGGER.info(
            "Starting hardware feature detection for %d features", total_features
        )

        for i, (feature, register) in enumerate(FEATURE_TEST_REGISTERS.items(), 1):
            # Update progress
            if self._progress_callback:
                self._progress_callback(feature, i, total_features)

            # Test feature
            results[feature] = await self._test_feature(feature, register)

            # Small delay between tests to avoid overwhelming device
            await asyncio.sleep(0.1)

        _LOGGER.info(
            "Feature detection complete. Detected: %d/%d features",
            sum(results.values()),
            total_features,
        )

        return results

    async def _test_feature(self, feature: str, register: int) -> bool:
        """Test single feature by reading register.

        Args:
            feature: Feature name for logging
            register: Register address to test

        Returns:
            True if feature is supported, False otherwise
        """
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                # Attempt to read register
                value = await self._coordinator.async_read_register(register)

                # Check for dash pattern (unsupported feature)
                if value == 0x2D2D:
                    _LOGGER.info(
                        "Feature '%s' NOT supported (register 0x%04X returned dash pattern)",
                        feature,
                        register,
                    )
                    return False

                # Check for None (read failed)
                if value is None:
                    if attempt < max_retries - 1:
                        _LOGGER.debug(
                            "Feature '%s' test returned None, retrying (attempt %d/%d)",
                            feature,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        _LOGGER.warning(
                            "Feature '%s' test failed after %d attempts (register 0x%04X)",
                            feature,
                            max_retries,
                            register,
                        )
                        return False

                # Valid value received - feature is supported
                _LOGGER.info(
                    "Feature '%s' detected (register 0x%04X = 0x%04X)",
                    feature,
                    register,
                    value,
                )
                return True

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    _LOGGER.debug(
                        "Feature '%s' test timeout, retrying (attempt %d/%d)",
                        feature,
                        attempt + 1,
                        max_retries,
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    _LOGGER.warning(
                        "Feature '%s' test timeout after %d attempts (register 0x%04X)",
                        feature,
                        max_retries,
                        register,
                    )
                    return False

            except Exception as err:
                _LOGGER.error(
                    "Feature '%s' test error (register 0x%04X): %s",
                    feature,
                    register,
                    err,
                )
                return False

        # All retries exhausted - assume not supported (safe default)
        return False

    def infer_features_from_model(self, device_name: str) -> dict[str, bool]:
        """Infer features from device model name as fallback.

        This is used as a secondary method when register testing fails
        or to provide initial guesses before testing.

        Args:
            device_name: Device name (e.g., "E6048", "E60M48", "E60G48")

        Returns:
            Dictionary of inferred feature availability
        """
        features = {
            "grid_tie": False,
            "diesel_mode": False,
            "three_phase": False,
            "split_phase": False,
            "parallel_operation": False,
            "timed_operation": False,
            "advanced_output": False,
            "customized_models": False,
        }

        name_upper = device_name.upper()

        # Grid-tie detection (G suffix)
        if "G" in name_upper or "GRID" in name_upper:
            features["grid_tie"] = True

        # Three-phase detection (T suffix or 3P)
        if "T" in name_upper or "3P" in name_upper:
            features["three_phase"] = True

        # Split-phase detection (M suffix)
        if "M" in name_upper or "SPLIT" in name_upper:
            features["split_phase"] = True

        _LOGGER.debug("Inferred features from model '%s': %s", device_name, features)
        return features
