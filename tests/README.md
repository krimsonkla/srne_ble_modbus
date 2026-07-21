# Test Suite

Automated tests for the SRNE BLE Modbus integration. The suite runs against
`pytest-homeassistant-custom-component`, which provides a real Home Assistant
test harness — no physical inverter or BLE adapter is required.

Every push and pull request to `main` runs this suite in CI:
[`.github/workflows/tests.yml`](../.github/workflows/tests.yml).

## Running the tests

```bash
# Install runtime deps first — the test plugin pins an exact HA version,
# so the two requirements files must resolve together.
pip install -r requirements.txt
pip install -r tests/requirements.txt

# Run everything
pytest

# Run a single layer
pytest tests/domain
pytest tests/infrastructure

# Run one file, verbosely
pytest tests/domain/test_register.py -v

# With coverage
pytest --cov=custom_components/srne_inverter --cov-report=term-missing
```

CI pins Python 3.12 and Home Assistant 2025.1.4. Local runs on other Python
versions may resolve a different HA release and behave differently.

## Layout

Tests mirror the integration's layered architecture (see
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)):

| Directory         | Covers                                                           |
| ----------------- | ---------------------------------------------------------------- |
| `domain/`         | Entities, value objects, and domain helpers — pure logic, no I/O |
| `application/`    | Use cases and services: batching, transactions, timeout learning |
| `infrastructure/` | BLE transport, Modbus framing, register decoding                 |
| `presentation/`   | Home Assistant entity platforms and the DI container             |
| `integration/`    | Cross-layer flows exercised through the HA test harness          |
| `unit/`           | Focused unit tests that don't belong to a single layer           |
| `doubles/`        | Shared fakes and stubs used across the suite                     |

Shared fixtures live in [`conftest.py`](conftest.py), including a mocked BLE
device so tests never touch real hardware.

## Conventions

- **Mock-first.** Domain and application tests must not perform I/O; BLE and
  Home Assistant boundaries are stubbed via the doubles in `doubles/`.
- **One behavior per test.** Name tests for the behavior asserted, not the
  method called.
- **No sleeps.** Use the harness's time control rather than wall-clock waits;
  BLE timing is simulated.
- **New code needs tests.** See [CONTRIBUTING.md](../CONTRIBUTING.md).

## Hardware testing

The automated suite deliberately avoids real hardware. To verify against a
physical inverter, install the integration in a development Home Assistant
instance and use its debug logging — see
[docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) for enabling verbose BLE
and Modbus logs, and [docs/BLE_PROTOCOL.md](../docs/BLE_PROTOCOL.md) for
interpreting raw frames.

## References

- [Architecture](../docs/ARCHITECTURE.md) — layer boundaries the tests mirror
- [BLE Protocol](../docs/BLE_PROTOCOL.md) — transport framing and register
  semantics
- [SRNE Protocol Specification v1.96](../resources/SRNE_Energy_Storage_Inverter_Protocol_v1.96.md)
  — vendor register reference
- [Bleak documentation](https://bleak.readthedocs.io/) — the underlying BLE
  library
