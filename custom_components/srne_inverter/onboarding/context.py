"""Onboarding context for SRNE Inverter config flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class OnboardingContext:
    """Complete onboarding context stored during config flow.

    This context persists state across all onboarding steps and provides
    a single source of truth for the configuration being built.
    """

    # Device information
    device_address: str
    device_name: str
    device_rssi: int | None = None

    # User selections
    user_level: str = "basic"  # "basic" | "advanced" | "expert"
    selected_preset: str | None = None

    # Hardware features (from detection)
    detected_features: dict[str, bool] = field(default_factory=dict)
    user_overrides: dict[str, bool] = field(default_factory=dict)

    # Detection metadata
    detection_timestamp: str | None = None
    detection_duration_seconds: float | None = None
    detection_method: str | None = None  # "auto" | "manual" | "skipped"

    # Configuration settings
    custom_settings: dict[str, Any] = field(default_factory=dict)

    # Validation results
    validation_warnings: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    validation_passed: bool = False

    # Flow state tracking
    current_step: str = "device_scan"
    previous_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)

    # Timestamps
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @property
    def active_features(self) -> dict[str, bool]:
        """Get final active features (detection + overrides).

        User overrides take precedence over detected features.
        """
        return {**self.detected_features, **self.user_overrides}

    @property
    def total_duration(self) -> float | None:
        """Get total onboarding duration in seconds."""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    def mark_step_complete(self, step: str) -> None:
        """Mark a step as completed and add to history."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        self.previous_step = self.current_step
        self.current_step = step

    def can_skip_step(self, step: str) -> bool:
        """Check if a step can be skipped based on user level and context.

        Args:
            step: The step to check

        Returns:
            True if step can be skipped
        """
        # Basic users skip manual config and go to presets
        if self.user_level == "basic" and step == "manual_config":
            return True

        # Advanced/Expert users skip preset selection and go to manual config
        if self.user_level in ["advanced", "expert"] and step == "preset_selection":
            return True

        return False

    def mark_completed(self) -> None:
        """Mark the entire onboarding flow as completed."""
        self.completed_at = time.time()
        self.current_step = "complete"
