# BLE Protocol Specification - SRNE Inverters

Technical specification for Bluetooth Low Energy communication with SRNE HF Series inverters.

## ⚠️ DISCLAIMER

**USE AT YOUR OWN RISK**

This software interfaces directly with your SRNE inverter via BLE. Improper use may result in equipment damage.
The authors assume NO LIABILITY for any damage or loss.

---

## Overview

SRNE HF Series inverters implement Modbus RTU protocol over Bluetooth Low Energy (BLE) using GATT characteristics.

### Protocol Stack

```
┌─────────────────────────┐
│   Application Layer     │
│   (Modbus RTU)          │
├─────────────────────────┤
│   Transport Layer       │
│   (BLE GATT)            │
├─────────────────────────┤
│   Link Layer            │
│   (Bluetooth 4.0+)      │
└─────────────────────────┘
```

---

## GATT Profile

### Service

**UUID**: `53300001-0023-4bd4-bbd5-a6920e4c5653`

### Characteristics

| UUID | Type | Properties | Description |
|------|------|------------|-------------|
| 0x53300001 | Command | Write | Send Modbus commands |
| 0x53300002 | Unknown | - | Reserved |
| 0x53300003 | Unknown | - | Reserved |
| 0x53300004 | Unknown | - | Reserved |
| 0x53300005 | Response | Notify | Receive Modbus responses |

### Characteristic Details

**Write Characteristic (0x53300001)**:
- Send Modbus RTU frames
- Max write size: 256 bytes
- No response expected on write

**Notify Characteristic (0x53300005)**:
- Receive Modbus RTU responses
- Must enable notifications before use
- Response includes 8-byte header + Modbus frame

---

## Communication Protocol

### Connection Sequence

1. **Scan for Devices**:
   ```python
   devices = await BleakScanner.discover()
   srne_devices = [d for d in devices if d.name.startswith("E6")]
   ```

2. **Connect to Device**:
   ```python
   client = BleakClient(device.address)
   await client.connect()
   ```

3. **Enable Notifications**:
   ```python
   await client.start_notify(NOTIFY_UUID, notification_handler)
   ```

4. **Send Commands**:
   ```python
   await client.write_gatt_char(WRITE_UUID, modbus_frame)
   ```

### Command/Response Flow

```
Client                          Inverter
  │                                │
  │  Write Modbus Frame            │
  │───────────────────────────────>│
  │                                │
  │  Acknowledgment ("----...")    │
  │<───────────────────────────────│
  │                                │
  │  Notification (Response Data)  │
  │<───────────────────────────────│
  │                                │
```

### Timing Requirements

**CRITICAL: 10-second minimum spacing between commands**

Sending commands faster than 10 seconds apart causes:
- Buffer overflow on inverter
- Lost notifications
- Corrupted responses
- Connection instability

**Recommended Timing**:
- Command spacing: 12 seconds (adds safety margin)
- Connection timeout: 10 seconds
- Read timeout: 5 seconds
- Notification wait: 5 seconds

---

## Modbus RTU Protocol

### Frame Structure

All Modbus frames follow standard RTU format with CRC-16/MODBUS checksum.

**Read Holding Registers (0x03)**:
```
[Device ID][0x03][Start Addr Hi][Start Addr Lo]
[Count Hi][Count Lo][CRC Lo][CRC Hi]
```

**Write Single Register (0x06)**:
```
[Device ID][0x06][Reg Addr Hi][Reg Addr Lo]
[Value Hi][Value Lo][CRC Lo][CRC Hi]
```

**Write Multiple Registers (0x10)**:
```
[Device ID][0x10][Start Addr Hi][Start Addr Lo]
[Count Hi][Count Lo][Byte Count][Data...][CRC Lo][CRC Hi]
```

### Response Format

**Standard Response**:
```
[8 bytes of zeros]
[Device ID][Function Code][Byte Count][Data...][CRC Lo][CRC Hi]
```

The 8-byte zero header is specific to SRNE BLE implementation.

**Exception Response**:
```
[8 bytes of zeros]
[Device ID][Function Code + 0x80][Exception Code][CRC Lo][CRC Hi]
```

### Device ID

Default: **0x01**

All SRNE inverters respond to device ID 1 on BLE interface.

---

## Register Map

### Address Ranges

| Range | Type | Description | Password |
|-------|------|-------------|----------|
| 0x0100-0x012F | Read-Only | Real-time data | None |
| 0xE001-0xE0FF | Read-Write | Battery settings | 4321 |
| 0xE200-0xE2FF | Read-Write | Grid settings | 0000 |
| 0xE300-0xE3FF | Read-Write | Software settings | 111111 |
| 0xE400-0xE43F | Read-Write | Grid-tie (model-specific) | Varies |
| 0xDF00-0xDFFF | Write-Only | Commands | None |

### Key Registers

**Real-Time Data (0x0100-0x012F)**:
```
0x0100  AC Input Voltage        (0.1V)
0x0107  Battery Voltage         (0.1V)
0x0108  Battery Current         (0.1A)
0x010A  Battery SOC             (1%)
0x010B  PV1 Voltage             (0.1V)
0x010C  PV1 Current             (0.1A)
0x010D  PV1 Power               (1W)
```

**Battery Settings (0xE001-0xE0FF)**:
```
0xE001  PV Max Charge Current   (1A)
0xE002  Battery Capacity        (1Ah)
0xE003  System Voltage          (12/24/48V)
0xE004  Battery Type            (enum)
0xE005  Battery Overvoltage     (0.1V)
0xE006  Charge Limit Voltage    (0.1V)
```

**Commands (0xDF00-0xDFFF)**:
```
0xDF00  Load Control            (0=Off, 1=On)
0xDF01  Machine Reset           (1=Reset)
```

---

## Data Types and Scaling

### Integer Types

- **8-bit**: Single byte (0-255)
- **16-bit**: Two bytes, big-endian (0-65535)
- **32-bit**: Four bytes, big-endian (0-4294967295)

### Scaled Values

Many registers use fixed-point scaling:

| Scale | Description | Example |
|-------|-------------|---------|
| 0.1 | One decimal place | 245 = 24.5V |
| 0.01 | Two decimal places | 2456 = 24.56A |
| 1 | No scaling | 75 = 75% |

**Conversion**:
```python
# Read from inverter
raw_value = 245
actual_voltage = raw_value * 0.1  # 24.5V

# Write to inverter
target_voltage = 24.5
raw_value = int(target_voltage / 0.1)  # 245
```

### Enumerated Values

Some registers use enumeration:

**Battery Type (0xE004)**:
```
0 = User Defined
1 = AGM
2 = Flooded
3 = LiFePO4
4 = Lithium Ion
```

**Output Priority (0xE20C)**:
```
0 = Solar First (SUB)
1 = Utility First (UTI)
2 = Battery First (SBU)
```

---

## Error Handling

### Exception Codes

| Code | Name | Description | Action |
|------|------|-------------|--------|
| 0x01 | Illegal Function | Unsupported function code | Check protocol version |
| 0x02 | Illegal Data Address | Register not supported | Cache as unsupported |
| 0x03 | Illegal Data Value | Value out of range | Validate before write |
| 0x0B | Permission Denied | Password required | Authenticate first |

### Connection Errors

**Timeout**:
```python
try:
    response = await asyncio.wait_for(
        self._read_register(address),
        timeout=5.0
    )
except asyncio.TimeoutError:
    _LOGGER.error("Read timeout for register 0x%04X", address)
    raise UpdateFailed("Communication timeout")
```

**Disconnection**:
```python
try:
    await client.write_gatt_char(WRITE_UUID, frame)
except BleakError as err:
    _LOGGER.error("BLE error: %s", err)
    await self._reconnect()
```

### Retry Logic

**Register Reads**:
- Retry up to 3 times on timeout
- Wait 2 seconds between retries
- Cache as failed after 3 failures

**Register Writes**:
- Single attempt (avoid duplicate writes)
- Verify with immediate read-back
- Raise error on failure

---

## Password Authentication

### Protected Ranges

Writes to certain register ranges require authentication:

| Range | Password | Description |
|-------|----------|-------------|
| 0xE000-0xE0FF | 4321 | Battery parameters |
| 0xE200-0xE2FF | 0000 | Grid parameters |
| 0xE300-0xE3FF | 111111 | Software settings |

### Authentication Process

1. Write password to register 0xE203
2. Password valid for current session
3. Re-authenticate after disconnect

**Example**:
```python
# Authenticate before write
await self._write_register(0xE203, 4321)

# Now protected writes succeed
await self._write_register(0xE002, 200)  # Battery capacity
```

---

## Performance Optimization

### Register Batching

Read multiple consecutive registers in single request:

```python
# Instead of 3 separate reads:
voltage = await read_register(0x0107)
current = await read_register(0x0108)
soc = await read_register(0x010A)

# Use single batched read:
values = await read_registers(0x0107, count=3)
voltage, current, soc = values[0], values[1], values[2]
```

**Benefits**:
- Reduces command count by 3x
- Respects 10-second spacing
- Faster overall update time

**Limitations**:
- Only works for consecutive registers
- Some models limit batch size to 10-20 registers

### Failed Register Caching

Cache known-unsupported registers to avoid repeated failures:

```python
if address in self._failed_registers:
    return None  # Skip known-failed register

try:
    value = await self._read_register(address)
except ModbusException as err:
    if err.exception_code == 0x02:
        self._failed_registers.add(address)
    raise
```

---

## Example Implementation

### Read Battery SOC

```python
import struct
from bleak import BleakClient

async def read_battery_soc(device_address):
    """Read battery state of charge."""

    # Modbus frame: Read register 0x010A
    frame = bytes([
        0x01,          # Device ID
        0x03,          # Function code (read)
        0x01, 0x0A,    # Register address
        0x00, 0x01,    # Register count (1)
    ])

    # Add CRC
    crc = calculate_crc(frame)
    frame += struct.pack("<H", crc)

    # Send via BLE
    async with BleakClient(device_address) as client:
        # Enable notifications
        await client.start_notify(NOTIFY_UUID, handle_response)

        # Send command
        await client.write_gatt_char(WRITE_UUID, frame)

        # Wait for response
        await asyncio.sleep(2)

        # Parse response (after 8-byte header)
        soc = response_data[11]  # Byte 11 contains SOC value

        return soc
```

### Write Charge Current Limit

```python
async def write_charge_current(device_address, current_amps):
    """Set maximum charge current."""

    # Authenticate first
    auth_frame = build_write_frame(0xE203, 4321)
    await client.write_gatt_char(WRITE_UUID, auth_frame)
    await asyncio.sleep(10)  # Required spacing

    # Write charge current
    frame = build_write_frame(0xE001, current_amps)
    await client.write_gatt_char(WRITE_UUID, frame)
    await asyncio.sleep(10)

    # Verify write
    verify_frame = build_read_frame(0xE001, 1)
    await client.write_gatt_char(WRITE_UUID, verify_frame)

    # Check response matches written value
    if response_value != current_amps:
        raise ValueError("Write verification failed")
```

---

## Debugging

### Enable BLE Logging

```python
import logging
logging.getLogger("bleak").setLevel(logging.DEBUG)
```

### Packet Capture

Use Wireshark or nRF Connect to capture BLE traffic:

1. Enable HCI logging on Linux:
   ```bash
   btmon > ble_capture.log
   ```

2. Filter for device address
3. Analyze Modbus frames

### Common Issues

**No Response**:
- Check notifications enabled
- Verify 10-second command spacing
- Ensure device connected

**Corrupted Data**:
- Validate CRC checksum
- Check for buffer overflow
- Verify frame structure

**Permission Denied**:
- Authenticate with password
- Check register address range
- Verify password is correct

---

## Limitations

### Protocol Constraints

1. **Command Spacing**: Minimum 10 seconds between commands
2. **Bulk Reads**: Limited to 10-20 consecutive registers
3. **Write Verification**: Must read back to confirm
4. **Session Persistence**: Password auth lost on disconnect

### BLE Constraints

1. **Range**: 10-30 meters typical
2. **Interference**: Susceptible to 2.4GHz interference
3. **Connection Limit**: One client at a time
4. **Throughput**: ~1-2 KB/s effective

### Model Variations

Different SRNE models support different register ranges:
- Grid-tie models: 0xE400-0xE43F
- Off-grid models: 0xE400-0xE43F unavailable
- Older firmware: May lack some registers

---

## References

- [Modbus RTU Specification](https://modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf)
- [Bluetooth GATT Specification](https://www.bluetooth.com/specifications/gatt/)
- [SRNE Protocol Documentation](REGISTER_MAPPING.md)

---

**Last Updated**: 2026-02-05
