"""Test Sprint 3 onboarding implementation.

This test file validates the Sprint 3 deliverables:
- Preset selection for basic users
- Manual configuration for advanced/expert users
- Validation logic
- Review screen
- Translation strings
"""

import sys
import os
import json


def test_file_structure():
    """Verify Sprint 3 files exist."""
    base_path = "/Users/jrisch/.homeassistant/custom_components/srne_inverter"

    files_to_check = [
        "config_flow.py",
        "translations/en.json",
        "onboarding/context.py",
        "onboarding/state_machine.py",
    ]

    for file_path in files_to_check:
        full_path = os.path.join(base_path, file_path)
        assert os.path.exists(full_path), f"File not found: {file_path}"

    print("✓ All Sprint 3 files exist")


def test_config_flow_methods():
    """Verify new config flow methods exist."""
    sys.path.insert(0, "/Users/jrisch/.homeassistant/custom_components/srne_inverter")

    from config_flow import SRNEConfigFlow

    required_methods = [
        "async_step_preset_selection",
        "async_step_manual_config",
        "async_step_validation",
        "async_step_review",
        "_filter_presets_by_features",
        "_build_manual_config_schema",
        "_validate_settings",
        "_format_settings_review",
    ]

    for method_name in required_methods:
        assert hasattr(SRNEConfigFlow, method_name), f"Method not found: {method_name}"

    print("✓ All Sprint 3 config flow methods exist")


def test_presets_structure():
    """Verify CONFIGURATION_PRESETS structure."""
    sys.path.insert(0, "/Users/jrisch/.homeassistant/custom_components/srne_inverter")

    from config_flow import CONFIGURATION_PRESETS

    assert len(CONFIGURATION_PRESETS) >= 4, "Expected at least 4 presets"

    required_presets = ["off_grid_solar", "grid_tied", "ups_mode", "time_of_use"]
    for preset_key in required_presets:
        assert preset_key in CONFIGURATION_PRESETS, f"Preset not found: {preset_key}"

        preset = CONFIGURATION_PRESETS[preset_key]
        assert "name" in preset, f"Preset {preset_key} missing 'name'"
        assert "description" in preset, f"Preset {preset_key} missing 'description'"
        assert (
            "required_features" in preset
        ), f"Preset {preset_key} missing 'required_features'"
        assert "settings" in preset, f"Preset {preset_key} missing 'settings'"

    print("✓ All presets have correct structure")


def test_translations():
    """Verify Sprint 3 translation strings."""
    translations_path = "/Users/jrisch/.homeassistant/custom_components/srne_inverter/translations/en.json"

    with open(translations_path, "r") as f:
        translations = json.load(f)

    # Check for new step translations
    required_steps = ["preset_selection", "manual_config", "validation", "review"]

    for step in required_steps:
        assert (
            step in translations["config"]["step"]
        ), f"Translation missing for step: {step}"
        step_data = translations["config"]["step"][step]
        assert "title" in step_data, f"Step {step} missing 'title'"
        assert "description" in step_data, f"Step {step} missing 'description'"

    # Check manual_config has field translations
    manual_config_data = translations["config"]["step"]["manual_config"]["data"]
    required_fields = [
        "battery_capacity",
        "battery_voltage",
        "output_priority",
        "charge_source_priority",
    ]

    for field in required_fields:
        assert field in manual_config_data, f"Translation missing for field: {field}"

    print("✓ All Sprint 3 translation strings present")


def test_state_machine_states():
    """Verify state machine has required states."""
    sys.path.insert(0, "/Users/jrisch/.homeassistant/custom_components/srne_inverter")

    from onboarding.state_machine import OnboardingState

    required_states = [
        "PRESET_SELECTION",
        "MANUAL_CONFIG",
        "VALIDATION",
        "REVIEW",
    ]

    for state_name in required_states:
        assert hasattr(OnboardingState, state_name), f"State not found: {state_name}"

    print("✓ All Sprint 3 states exist in state machine")


def test_onboarding_context_fields():
    """Verify OnboardingContext has required fields."""
    sys.path.insert(0, "/Users/jrisch/.homeassistant/custom_components/srne_inverter")

    from onboarding.context import OnboardingContext

    # Create test instance
    context = OnboardingContext(
        device_address="00:11:22:33:44:55", device_name="Test Device"
    )

    # Check required fields exist
    assert hasattr(context, "selected_preset"), "Missing field: selected_preset"
    assert hasattr(context, "custom_settings"), "Missing field: custom_settings"
    assert hasattr(context, "validation_warnings"), "Missing field: validation_warnings"
    assert hasattr(context, "validation_passed"), "Missing field: validation_passed"

    print("✓ OnboardingContext has all required fields")


def test_validation_logic():
    """Test validation method logic."""
    sys.path.insert(0, "/Users/jrisch/.homeassistant/custom_components/srne_inverter")

    from config_flow import SRNEConfigFlow
    from onboarding.context import OnboardingContext

    flow = SRNEConfigFlow()
    flow._onboarding_context = OnboardingContext(
        device_address="00:11:22:33:44:55", device_name="Test Device"
    )

    # Test valid settings
    flow._onboarding_context.custom_settings = {
        "battery_voltage": "48",
        "discharge_stop_soc": 20,
        "switch_to_ac_soc": 30,
        "switch_to_battery_soc": 80,
    }

    result = flow._validate_settings()
    assert result["has_errors"] == False, "Valid settings should not have errors"

    # Test invalid SOC order
    flow._onboarding_context.custom_settings = {
        "discharge_stop_soc": 30,
        "switch_to_ac_soc": 20,
        "switch_to_battery_soc": 80,
    }

    result = flow._validate_settings()
    assert result["has_errors"] == True, "Invalid SOC order should have errors"

    print("✓ Validation logic works correctly")


def run_all_tests():
    """Run all Sprint 3 tests."""
    print("\n=== Sprint 3 Onboarding Tests ===\n")

    tests = [
        test_file_structure,
        test_config_flow_methods,
        test_presets_structure,
        test_translations,
        test_state_machine_states,
        test_onboarding_context_fields,
        test_validation_logic,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
