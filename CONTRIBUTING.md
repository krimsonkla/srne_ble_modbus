# Contributing to SRNE BLE Modbus Integration

Thank you for your interest in contributing to this project. This document outlines our contribution guidelines and standards.

## IMPORTANT: Read the Disclaimer First

Before contributing, you **MUST** read and understand the [DISCLAIMER.md](DISCLAIMER.md) file. By contributing, you acknowledge:
- The risks involved in this software
- Your responsibility as a contributor
- The liability limitations
- The safety requirements

## Code of Conduct

- Be respectful and constructive
- Focus on safety and reliability
- Document thoroughly
- Test rigorously
- Prioritize user safety over features

## Safety-First Development

### Critical Safety Requirements

All contributions must:
1. **Never compromise safety features**
2. **Include comprehensive error handling**
3. **Validate all user inputs**
4. **Include safety warnings where appropriate**
5. **Document potential risks**

### Safety Review Checklist

Before submitting code that controls hardware:
- [ ] Includes input validation
- [ ] Handles communication failures gracefully
- [ ] Includes timeout mechanisms
- [ ] Validates data ranges against specifications
- [ ] Logs safety-critical operations
- [ ] Includes rollback capabilities
- [ ] Documents failure modes
- [ ] Tested in safe environment

## Development Environment

### Prerequisites

- Python 3.11 or later
- Home Assistant development environment
- BLE-capable development machine (macOS/Linux preferred)
- SRNE inverter for testing (or comprehensive mocking)
- Safety equipment for hardware testing

### Setup

```bash
# Clone the repository
git clone https://github.com/krimsonkla/srne_ble_modbus.git
cd srne_ble_modbus

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## Code Style Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with these specific requirements:

```python
# Copyright (c) 2026 SRNE BLE Modbus Contributors
# Licensed under the MIT License
# See LICENSE file for full license text
#
# WARNING: This software controls electrical equipment
# Improper use may cause damage or injury
# USE AT YOUR OWN RISK

"""Module docstring.

Detailed description of the module's purpose.
Include safety warnings if the module controls hardware.
"""

import logging
from typing import Any, Optional

_LOGGER = logging.getLogger(__name__)


class ExampleClass:
    """Class for demonstration.

    Args:
        param: Description of parameter

    Raises:
        ValueError: When parameter is invalid

    Safety:
        Include safety notes for hardware-controlling classes
    """

    def __init__(self, param: str) -> None:
        """Initialize the class."""
        self._param = self._validate_param(param)

    def _validate_param(self, param: str) -> str:
        """Validate parameters with clear error messages.

        Args:
            param: Parameter to validate

        Returns:
            Validated parameter

        Raises:
            ValueError: If parameter is invalid
        """
        if not param:
            raise ValueError("Parameter cannot be empty")
        return param
```

### Key Style Requirements

1. **Type Hints**: All functions must include type hints
2. **Docstrings**: All public functions/classes need docstrings
3. **Error Handling**: Explicit error handling with informative messages
4. **Logging**: Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
5. **Constants**: Use UPPER_CASE for constants
6. **Private Methods**: Prefix with underscore `_method_name`

### Safety-Critical Code Standards

For code that controls hardware:

```python
def set_battery_charge_current(self, current: float) -> None:
    """Set battery charge current.

    WARNING: Incorrect values can damage battery or cause fire.

    Args:
        current: Charge current in amps (must be within spec)

    Raises:
        ValueError: If current exceeds safe limits
        RuntimeError: If inverter is not in safe state

    Safety Limits:
        - Maximum: 100A (hardware limit)
        - Recommended: 80A (conservative limit)
        - Minimum: 0A
    """
    # Validate against hardware limits
    if not 0 <= current <= 100:
        _LOGGER.error(
            "Charge current %.1fA exceeds safe limits (0-100A)",
            current
        )
        raise ValueError(f"Current {current}A outside safe range")

    # Check inverter state
    if not self._is_safe_to_modify():
        raise RuntimeError("Inverter not in safe state for modification")

    # Log the operation
    _LOGGER.warning(
        "Setting battery charge current to %.1fA - "
        "monitor battery temperature closely",
        current
    )

    # Execute with timeout and error handling
    try:
        self._write_register(CHARGE_CURRENT_REGISTER, current, timeout=5.0)
    except Exception as err:
        _LOGGER.error("Failed to set charge current: %s", err)
        raise
```

## Testing Requirements

### Minimum Test Coverage

- Unit tests: 80% coverage minimum
- Integration tests for all hardware interfaces
- Safety validation tests
- Error handling tests
- Edge case tests

### Test Structure

```python
"""Test module for example functionality."""

import pytest
from unittest.mock import Mock, patch

from custom_components.srne_inverter import example


class TestExampleClass:
    """Test ExampleClass."""

    def test_valid_input(self):
        """Test normal operation with valid input."""
        obj = example.ExampleClass("valid")
        assert obj.param == "valid"

    def test_invalid_input_raises_error(self):
        """Test that invalid input raises appropriate error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            example.ExampleClass("")

    @patch("custom_components.srne_inverter.example._LOGGER")
    def test_safety_logging(self, mock_logger):
        """Test that safety-critical operations are logged."""
        obj = example.ExampleClass("test")
        obj.safety_critical_method()
        mock_logger.warning.assert_called()


@pytest.mark.hardware
class TestHardwareIntegration:
    """Tests requiring actual hardware.

    WARNING: These tests interact with real hardware.
    Ensure safe test environment before running.
    """

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-hardware"),
        reason="Hardware tests disabled"
    )
    def test_real_device(self):
        """Test with real hardware (use with caution)."""
        # Hardware test implementation
        pass
```

### Running Tests

```bash
# Run unit tests only
pytest tests/

# Run with coverage
pytest --cov=custom_components/srne_inverter tests/

# Run hardware tests (DANGEROUS - use caution)
pytest --run-hardware tests/

# Run specific test file
pytest tests/test_coordinator.py
```

## Documentation Standards

### Code Documentation

1. **Module Docstrings**: Explain purpose and usage
2. **Function Docstrings**: Include Args, Returns, Raises, Safety notes
3. **Inline Comments**: Explain complex logic
4. **Safety Warnings**: Mark dangerous operations clearly

### User Documentation

When adding features, update:
- README.md (if user-facing)
- Configuration examples in `docs/`
- Safety warnings in DISCLAIMER.md (if needed)
- AUTOMATIONS.md (for automation examples)

## Pull Request Process

### Before Submitting

1. **Read DISCLAIMER.md** and ensure compliance
2. **Run tests** and ensure all pass
3. **Run linters** (black, isort, pylint, mypy)
4. **Update documentation** as needed
5. **Test manually** in safe environment
6. **Review your own code** for safety issues

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Safety improvement

## Safety Impact
- [ ] No hardware interaction
- [ ] Read-only hardware access
- [ ] Modifies hardware settings (REQUIRES EXTRA REVIEW)
- [ ] Changes safety-critical code (REQUIRES MAINTAINER APPROVAL)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed in safe environment
- [ ] Hardware testing completed (if applicable)
- [ ] All tests pass

## Documentation
- [ ] Code comments added/updated
- [ ] Docstrings added/updated
- [ ] User documentation updated
- [ ] Safety warnings added (if needed)

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] No sensitive data in commit
- [ ] Commit messages are clear
- [ ] DISCLAIMER.md reviewed and understood
```

### Review Process

1. **Automated checks** must pass (GitHub Actions)
2. **Code review** by maintainer
3. **Safety review** for hardware-controlling code
4. **Testing verification**
5. **Documentation review**

### Review Criteria

Reviewers will check:
- Code quality and style
- Safety considerations
- Error handling
- Test coverage
- Documentation completeness
- Breaking changes
- Performance impact

## Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add battery temperature monitoring
fix: correct charge current validation range
docs: update safety warnings in README
test: add integration tests for BLE connection
refactor: improve error handling in coordinator
perf: optimize register batching logic
safety: add timeout to hardware write operations
```

### Commit Message Format

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `safety`: Safety-related changes
- `chore`: Maintenance tasks

## Branching Strategy

- `main`: Stable release branch
- `develop`: Development branch
- `feature/description`: Feature branches
- `fix/description`: Bug fix branches
- `safety/description`: Safety improvement branches

### Workflow

1. Fork the repository
2. Create feature branch from `develop`
3. Make changes
4. Submit PR to `develop`
5. After review and approval, maintainer merges

## Hardware Testing Guidelines

### DANGER: Hardware Testing

Testing with real hardware is **DANGEROUS**. Follow these rules:

1. **Isolated Environment**: Test in isolated area away from people
2. **Safety Equipment**: Have fire extinguisher, safety glasses
3. **Monitoring**: Continuously monitor temperature, voltage, current
4. **Start Small**: Begin with minimal loads/currents
5. **Emergency Stop**: Have physical disconnect ready
6. **Documentation**: Document all test configurations
7. **Incremental**: Increase parameters gradually
8. **Supervision**: Never leave tests unattended

### Hardware Test Environment

Required safety measures:
- Fire-resistant surface
- Adequate ventilation
- Temperature monitoring
- Voltage/current monitoring
- Physical emergency stop
- Fire suppression equipment
- First aid kit nearby

### Mock Testing Preferred

Prefer comprehensive mocking over hardware testing:

```python
@pytest.fixture
def mock_ble_device():
    """Mock BLE device for safe testing."""
    device = Mock()
    device.read_register.return_value = 0x1234
    device.write_register.return_value = True
    return device
```

## Reporting Issues

### Bug Reports

Include:
- Home Assistant version
- Integration version
- Hardware model and firmware version
- Detailed steps to reproduce
- Expected vs actual behavior
- Relevant logs (sanitized)
- Configuration (sanitized)

### Security Issues

**DO NOT** open public issues for security vulnerabilities.

Contact maintainers privately:
- Email project maintainers
- Use GitHub Security Advisory
- Allow reasonable disclosure time

### Safety Issues

Safety issues get **HIGHEST PRIORITY**:
1. Report immediately
2. Stop using affected features
3. Provide detailed description
4. Include potential impact
5. Suggest mitigation if possible

## Feature Requests

Before requesting features:
1. Check existing issues
2. Consider safety implications
3. Provide detailed use case
4. Explain benefits vs risks
5. Suggest implementation approach

## License

By contributing, you agree that your contributions will be licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Attribution

Contributors will be acknowledged in:
- GitHub contributors list
- Release notes
- CHANGELOG.md

## Questions?

- Open a discussion on GitHub
- Check existing documentation
- Review closed issues
- Contact maintainers

---

**Remember: Safety First, Features Second**

Thank you for helping make this project better and safer!
