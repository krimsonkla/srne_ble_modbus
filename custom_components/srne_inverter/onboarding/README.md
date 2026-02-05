# SRNE Inverter Onboarding Package

This package contains the onboarding wizard implementation for the SRNE Inverter
Home Assistant integration.

## Overview

The onboarding wizard guides users through initial device setup with progressive
disclosure based on their experience level (Basic, Advanced, or Expert). It
auto-detects hardware features, provides configuration presets, and validates
settings before writing to the device.

## Architecture

### Components

1. **`context.py`** - OnboardingContext dataclass
   - Stores all state during the onboarding flow
   - Tracks device info, user selections, detection results, and settings
   - Provides computed properties and helper methods

2. **`state_machine.py`** - OnboardingStateMachine
   - Manages flow state transitions
   - Validates state changes
   - Supports back navigation
   - Defines 12 states from device scan to completion

3. **`detection.py`** - FeatureDetector service
   - Auto-detects hardware capabilities
   - Tests 8 representative registers for dash pattern (0x2D2D)
   - Includes retry logic and progress callbacks
   - Provides model-based inference fallback

## Usage

### Basic Flow

```python
from .onboarding import OnboardingContext, OnboardingStateMachine, FeatureDetector

# Initialize context
context = OnboardingContext(
    device_address="AA:BB:CC:DD:EE:FF",
    device_name="E6048",
)

# Initialize state machine
state_machine = OnboardingStateMachine()

# Run feature detection
detector = FeatureDetector(coordinator)
features = await detector.detect_all_features()
context.detected_features = features

# Track progress
context.mark_step_complete("hardware_detection")
state_machine.transition(OnboardingState.DETECTION_REVIEW)
```

### Integration with Config Flow

The onboarding components are designed to be integrated into the Home Assistant
config flow:

```python
class SRNEConfigFlow(config_entries.ConfigFlow):
    def __init__(self):
        self._onboarding_context = None
        self._state_machine = OnboardingStateMachine()

    async def async_step_welcome(self, user_input=None):
        if user_input is None:
            # Initialize context
            self._onboarding_context = OnboardingContext(
                device_address=address,
                device_name=device_name,
            )
            return self.async_show_form(step_id="welcome")

        # Proceed to next step
        self._state_machine.transition(OnboardingState.USER_LEVEL)
        return await self.async_step_user_level()
```

## State Machine

### States

- `DEVICE_SCAN` - Scanning for BLE devices
- `DEVICE_SELECTED` - Device chosen by user
- `WELCOME` - Welcome screen
- `USER_LEVEL` - Experience level selection
- `HARDWARE_DETECTION` - Auto-detecting features
- `DETECTION_REVIEW` - Review detection results
- `PRESET_SELECTION` - Choose configuration preset (basic users)
- `MANUAL_CONFIG` - Manual configuration (advanced/expert users)
- `VALIDATION` - Validate configuration
- `REVIEW` - Review all settings
- `WRITE_SETTINGS` - Write to device
- `COMPLETE` - Setup complete
- `DETECTION_FAILED` - Error state for detection failures
- `WRITE_FAILED` - Error state for write failures

### State Transitions

```
DEVICE_SCAN → DEVICE_SELECTED → WELCOME → USER_LEVEL
    ↓
HARDWARE_DETECTION → DETECTION_REVIEW
    ↓
[PRESET_SELECTION (basic) | MANUAL_CONFIG (advanced/expert)]
    ↓
VALIDATION → REVIEW → WRITE_SETTINGS → COMPLETE
```

## Feature Detection

### Tested Features

The detector tests 8 representative registers to determine hardware
capabilities:

1. **grid_tie** (0xE400) - Grid-tied operation support
2. **diesel_mode** (0xE21F) - Diesel generator support
3. **three_phase** (0x238) - Three-phase operation
4. **split_phase** (0x228) - Split-phase operation
5. **parallel_operation** (0x226) - Parallel inverter support
6. **timed_operation** (0xE02C) - Timed charge/discharge
7. **advanced_output** (0xE21C) - Advanced output settings
8. **customized_models** (0x227) - Customized model features

### Detection Strategy

1. Read each test register
2. Check for dash pattern (0x2D2D = unsupported)
3. Retry up to 3 times on timeout
4. Return dict of feature availability

### Progress Callback

```python
def progress_callback(feature_name: str, current: int, total: int):
    """Called for each feature test.

    Args:
        feature_name: Name of feature being tested
        current: Current test number (1-based)
        total: Total number of features to test
    """
    percentage = int((current / total) * 100)
    print(f"Testing {feature_name}... {percentage}% complete")

detector = FeatureDetector(coordinator)
features = await detector.detect_all_features(progress_callback)
```

## OnboardingContext

### Key Properties

- `active_features` - Merged detected + overridden features
- `total_duration` - Total onboarding time in seconds

### Key Methods

- `mark_step_complete(step)` - Record step completion
- `can_skip_step(step)` - Check if step can be skipped
- `mark_completed()` - Finalize onboarding

### User Levels

- **basic** - Guided setup with presets, auto-detection only
- **advanced** - Full control, can override detection
- **expert** - Maximum control, can override safety checks

## Testing

### Unit Tests

```python
def test_context_creation():
    ctx = OnboardingContext(
        device_address="AA:BB:CC:DD:EE:FF",
        device_name="E6048",
    )
    assert ctx.device_address == "AA:BB:CC:DD:EE:FF"
    assert ctx.user_level == "basic"

def test_state_transitions():
    sm = OnboardingStateMachine()
    assert sm.transition(OnboardingState.DEVICE_SELECTED)
    assert not sm.transition(OnboardingState.COMPLETE)  # Invalid

def test_back_navigation():
    sm = OnboardingStateMachine()
    sm.transition(OnboardingState.DEVICE_SELECTED)
    previous = sm.go_back()
    assert previous == OnboardingState.DEVICE_SCAN
```

### Mock Coordinator

For testing feature detection:

```python
class MockCoordinator:
    def __init__(self, register_values):
        self.values = register_values

    async def async_read_register(self, address):
        return self.values.get(address, 0x2D2D)

# Test all features supported
coordinator = MockCoordinator({
    0xE400: 0x0001,  # grid_tie supported
    0xE21F: 0x0000,  # diesel_mode supported
    # ... etc
})

detector = FeatureDetector(coordinator)
features = await detector.detect_all_features()
assert features["grid_tie"] is True
```

## Design Principles

1. **Simple State Machine** - Enum-based FSM with explicit transitions
2. **Type Safety** - Full type hints throughout
3. **Defensive Programming** - Try/except with logging
4. **Progressive Disclosure** - Show only what's needed
5. **Non-Blocking** - Async operations with progress indication

## Performance

- **Detection Time**: 10-30 seconds (8 features @ 0.1s delay + retries)
- **Memory**: Minimal (single context object)
- **State Transitions**: O(1) validation

## Error Handling

All components include comprehensive error handling:

- **Detection** - Retries, timeouts, fallback to inference
- **State Machine** - Invalid transition prevention
- **Context** - Safe defaults, property validation

## Logging

Uses structured logging at appropriate levels:

- **INFO** - Key events (state transitions, feature detection results)
- **DEBUG** - Detailed progress (register reads, retry attempts)
- **WARNING** - Recoverable errors (invalid transitions, timeout retries)
- **ERROR** - Failures (connection errors, unexpected exceptions)

## Future Enhancements

Potential improvements for future versions:

1. **Persistence** - Save/restore partial progress
2. **Analytics** - Track common failure points
3. **Caching** - Cache detection results
4. **Multi-device** - Support for multiple SRNE devices
5. **Advanced Detection** - ML-based feature inference

## Contributing

When modifying this package:

1. Maintain 100% type hint coverage
2. Update docstrings for all public APIs
3. Add unit tests for new functionality
4. Follow HA coding standards
5. Update this README as needed

## Support

- **Design Docs**: `/docs/ONBOARDING_MASTER_PLAN_SIMPLIFIED.md`
- **Implementation Guide**: `/docs/SPRINT_2_HANDOFF.md`
- **Progress Tracking**: `/docs/IMPLEMENTATION_PROGRESS.md`
- **HA Best Practices**: `/docs/HA_CONFIG_FLOW_BEST_PRACTICES.md`

---

**Package Version**: 1.0 **Last Updated**: 2026-02-10 **Status**: Sprint 1
Complete ✅
