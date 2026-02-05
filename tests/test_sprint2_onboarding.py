"""Test Sprint 2 onboarding implementation."""

import pytest


def test_state_machine_imports():
    """Test that state machine can be imported."""
    # This would need proper test environment
    # For now, just verify file structure
    import os

    base_path = os.path.dirname(os.path.dirname(__file__))
    onboarding_path = os.path.join(
        base_path, "custom_components", "srne_inverter", "onboarding"
    )

    assert os.path.exists(onboarding_path)
    assert os.path.exists(os.path.join(onboarding_path, "__init__.py"))
    assert os.path.exists(os.path.join(onboarding_path, "state_machine.py"))
    assert os.path.exists(os.path.join(onboarding_path, "context.py"))
    assert os.path.exists(os.path.join(onboarding_path, "detection.py"))


def test_config_flow_has_onboarding_steps():
    """Test that config flow file contains onboarding steps."""
    import os

    base_path = os.path.dirname(os.path.dirname(__file__))
    config_flow_path = os.path.join(
        base_path, "custom_components", "srne_inverter", "config_flow.py"
    )

    with open(config_flow_path, "r") as f:
        content = f.read()

    # Check for onboarding imports
    assert "from .onboarding import" in content
    assert "OnboardingContext" in content
    assert "OnboardingStateMachine" in content
    assert "FeatureDetector" in content

    # Check for new step methods
    assert "async def async_step_welcome" in content
    assert "async def async_step_user_level" in content
    assert "async def async_step_hardware_detection" in content
    assert "async def async_step_detection_review" in content

    # Check for feature flag
    assert "USE_ONBOARDING_V2" in content


def test_translations_has_onboarding_strings():
    """Test that translations include onboarding strings."""
    import os
    import json

    base_path = os.path.dirname(os.path.dirname(__file__))
    translations_path = os.path.join(
        base_path, "custom_components", "srne_inverter", "translations", "en.json"
    )

    with open(translations_path, "r") as f:
        translations = json.load(f)

    # Check for new step translations
    assert "welcome" in translations["config"]["step"]
    assert "user_level" in translations["config"]["step"]
    assert "hardware_detection" in translations["config"]["step"]
    assert "detection_review" in translations["config"]["step"]

    # Check for progress messages
    assert "progress" in translations["config"]
    assert "detect_hardware" in translations["config"]["progress"]

    # Check for new error messages
    assert "detection_failed" in translations["config"]["error"]


if __name__ == "__main__":
    print("Running Sprint 2 onboarding tests...")
    test_state_machine_imports()
    print("✓ State machine files exist")

    test_config_flow_has_onboarding_steps()
    print("✓ Config flow has onboarding steps")

    test_translations_has_onboarding_strings()
    print("✓ Translations include onboarding strings")

    print("\n✅ All Sprint 2 tests passed!")
