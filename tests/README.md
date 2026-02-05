# SRNE Inverter BLE Test Suite

Comprehensive testing toolkit for reverse engineering and validating BLE communication with SRNE inverters via the WiFi/BLE data logger.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify bleak is installed
python -c "import bleak; print(f'bleak version: {bleak.__version__}')"
```

### Basic Usage

#### 1. Scan for Devices

```bash
python ble_test_suite.py --scan
```

Output:
```
Found 1 SRNE device(s)
  - E60000231107692658 (XX:XX:XX:XX:XX:XX)
```

#### 2. Run Full Test Suite

```bash
python ble_test_suite.py --device E60000231107692658 --test-all
```

This will:
- Test all critical registers
- Test system information
- Test fault registers
- Test notification channels
- Save results to `tests/ble_test_results.json`

#### 3. Interactive Mode

```bash
python ble_test_suite.py --device E60000231107692658 --interactive
```

Commands:
```
> read 0x0107           # Read battery voltage
> read 0x0100           # Read AC input voltage
> write 0x010A 1        # Turn load ON
> write 0x010A 0        # Turn load OFF
> test                  # Run full test suite
> quit                  # Exit
```

#### 4. Single Register Read

```bash
python ble_test_suite.py --device E60000231107692658 --read 0x0107
```

## Test Suite Components

### 1. Modbus Command Builder

```python
from ble_test_suite import ModbusCommands

# Build read command
cmd = ModbusCommands.build_read_command(
    slave_addr=0x01,
    register=0x0107,  # Battery voltage
    count=1
)

# Build write command
cmd = ModbusCommands.build_write_command(
    slave_addr=0x01,
    register=0x010A,  # Load control
    value=1  # Turn ON
)
```

### 2. Response Decoder

```python
from ble_test_suite import ModbusCommands

# Decode BLE notification
response = bytes.fromhex("0000000000000000010302010FF9D0")
decoded = ModbusCommands.decode_response(response)

print(decoded)
# {
#   'header': '0000000000000000',
#   'slave_addr': 1,
#   'function_code': 3,
#   'byte_count': 2,
#   'data': '010f',
#   'data_int': 271,
#   'crc': 'f9d0'
# }
```

### 3. Register Map

```python
from ble_test_suite import RegisterMap

# Get register information
name, scale, unit = RegisterMap.get_register_info(0x0107)
print(f"{name}: scale={scale}, unit={unit}")
# Battery Voltage: scale=0.1, unit=V

# Format value
formatted = RegisterMap.format_value(0x0107, 123)
print(formatted)
# Battery Voltage: 12.3 V
```

### 4. BLE Test Client

```python
import asyncio
from ble_test_suite import BLETestClient

async def test():
    client = BLETestClient("E60000231107692658")

    if await client.connect():
        # Read battery voltage
        result = await client.read_register(0x0107)
        print(result)

        await client.disconnect()

asyncio.run(test())
```

## Known Issues & Workarounds

### Issue 1: 10-Second Command Delay Required

**Problem**: Sending commands too quickly overwhelms the BLE buffer.

**Workaround**: The test suite automatically enforces 10-second delays between commands.

**Example**:
```python
# Automatic delay enforcement
await client.read_register(0x0107)  # Reads immediately
await client.read_register(0x0108)  # Waits 10s before reading
```

### Issue 2: Bulk Reads Not Supported

**Problem**: Requesting multiple registers returns only 1 register.

**Workaround**: Use individual single-register reads.

**Bad**:
```python
# This will only return 1 register!
await client.read_multiple_registers(0x0100, count=7)
```

**Good**:
```python
# Read one at a time
for reg in range(0x0100, 0x0107):
    value = await client.read_register(reg)
    # Process value
```

### Issue 3: No Response When Register Unavailable

**Problem**: When the inverter is off or AC not connected, some registers return no notification.

**Workaround**: Treat timeout as "data unavailable", not error.

**Example**:
```python
result = await client.read_register(0x0100)  # AC voltage

if result is None:
    print("AC input not available (inverter off or no AC connected)")
else:
    print(f"AC voltage: {result['data_int'] * 0.1} V")
```

### Issue 4: AT Command Response on First Connect

**Problem**: First command after connection returns AT command response instead of Modbus data.

**Workaround**: Ignore AT responses and retry command.

**The test suite handles this automatically.**

## Register Reference

### Critical Real-Time Data

| Register | Name | Scale | Unit | Notes |
|----------|------|-------|------|-------|
| 0x0100 | AC Input Voltage | 0.1 | V | May be unavailable if inverter off |
| 0x0101 | AC Input Frequency | 0.1 | Hz | Expect 500 (50Hz) or 600 (60Hz) |
| 0x0102 | AC Output Voltage | 0.1 | V | |
| 0x0103 | AC Output Frequency | 0.1 | Hz | |
| 0x0104 | AC Output Apparent Power | 1 | VA | |
| 0x0105 | AC Output Active Power | 1 | W | |
| 0x0106 | Output Load Percent | 1 | % | |
| 0x0107 | Battery Voltage | 0.1 | V | Always available |
| 0x0108 | Battery Charging Current | 0.1 | A | |
| 0x0109 | Battery Discharge Current | 0.1 | A | |
| 0x010A | Load Control | 1 | bool | 0=OFF, 1=ON (writable) |
| 0x010B | PV1 Voltage | 0.1 | V | |
| 0x010C | PV1 Current | 0.1 | A | |
| 0x010D | PV1 Power | 1 | W | Calculated |
| 0x0120 | Load Status | 1 | bool | Read-only |
| 0x0121 | Fault Code Low | 1 | hex | 16 bits |
| 0x0122 | Fault Code High | 1 | hex | 16 bits |

For complete register map, see [Modbus Protocol Mapping](../docs/modbus-protocol-mapping.md).

## Test Results Format

The test suite saves results to `ble_test_results.json`:

```json
{
  "timestamp": "2026-02-03T10:30:00",
  "device": "E60000231107692658",
  "tests": [
    {
      "category": "critical",
      "register": "0x0107",
      "result": {
        "command": "010301070001...",
        "notifications": {
          "53300005": [
            {
              "timestamp": "2026-02-03T10:30:12",
              "data": "0000000000000000010302007bf867",
              "decoded": {
                "slave_addr": 1,
                "function_code": 3,
                "values": [123],
                "raw": "..."
              }
            }
          ]
        }
      }
    }
  ]
}
```

## Performance Notes

### Update Time Calculation

With 10-second delays between commands:

| Registers | Total Time | Notes |
|-----------|------------|-------|
| 1 | ~12s | 10s delay + 2s notification wait |
| 5 | ~60s | Suitable for 1-minute updates |
| 10 | ~120s | Maximum for reasonable updates |

**Recommendation**: Read 5-7 critical registers per update cycle (1 minute).

### BLE vs Cloud Comparison

| Metric | BLE (with delays) | Cloud API |
|--------|------------------|-----------|
| Single read | 12s | 1-5s |
| 5 registers | 60s | 2-7s |
| Command latency | 10s+ | 1-5s |
| Update frequency | 30-60s | 10-60s |
| Range | 10-30m | Unlimited |

**Current Verdict**: Cloud API is **faster** for commands due to BLE buffer limitations. BLE advantage is **offline capability** only.

## Troubleshooting

### "bleak not installed"

```bash
pip install bleak
```

### "No devices found"

1. Check Bluetooth is enabled on your system
2. Ensure inverter data logger is powered on
3. Verify you're within BLE range (10-30m)
4. Try scanning multiple times

### "Connection timeout"

1. Move closer to inverter
2. Check for BLE interference (other devices)
3. Restart inverter data logger
4. Try connecting with official mobile app first

### "No notifications received"

1. Verify inverter is ON and operational
2. Check register is available (some registers need AC connected)
3. Wait longer (up to 5 seconds)
4. Try a different register (e.g., 0x0107 battery voltage always works)

### "AT command response"

This is normal on first connection. The test suite handles it automatically. If persistent, disconnect and reconnect.

## Contributing

To contribute test results or improvements:

1. Run the test suite with `--test-all`
2. Share `ble_test_results.json`
3. Document any new findings
4. Submit PR with updates

## License

Same as parent project.

## References

- [BLE Protocol Documentation](../docs/ble-protocol.md)
- [BLE Reverse Engineering Findings](../docs/ble-reverse-engineering-findings.md)
- [Modbus Protocol Mapping](../docs/modbus-protocol-mapping.md)
- [Bleak Documentation](https://bleak.readthedocs.io/)

---

**Last Updated**: 2026-02-03
**Status**: Active Development
