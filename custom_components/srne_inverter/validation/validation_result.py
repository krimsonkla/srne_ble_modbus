"""Validation Result data class.

Result container with errors, warnings, and info messages.
Extracted from validation.py for one-class-per-file compliance.
Root-Level Cleanup
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        valid: Whether validation passed (no errors)
        errors: List of error messages (blocking)
        warnings: List of warning messages (non-blocking)
        info: List of informational messages
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def merge(self, other: ValidationResult) -> None:
        """Merge another validation result into this one.

        Args:
            other: ValidationResult to merge
        """
        self.valid = self.valid and other.valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)

    def __str__(self) -> str:
        """Return string representation of validation result."""
        parts = []
        if self.errors:
            parts.append(f"Errors: {', '.join(self.errors)}")
        if self.warnings:
            parts.append(f"Warnings: {', '.join(self.warnings)}")
        if self.info:
            parts.append(f"Info: {', '.join(self.info)}")
        return " | ".join(parts) if parts else "Valid"
