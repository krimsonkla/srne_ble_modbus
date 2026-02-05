# Architecture Overview - SRNE BLE Modbus

Technical architecture documentation for developers and contributors.

## ⚠️ DISCLAIMER

**USE AT YOUR OWN RISK**

This software interfaces directly with your SRNE inverter via BLE.
Improper configuration or use may result in equipment damage or malfunction.
The authors assume NO LIABILITY for any damage or loss.

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Home Assistant                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         SRNE BLE Modbus Integration                 │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐│   │
│  │  │            │  │              │  │             ││   │
│  │  │ Config Flow│  │ Coordinator  │  │  Entities   ││   │
│  │  │            │  │              │  │             ││   │
│  │  └─────┬──────┘  └──────┬───────┘  └──────┬──────┘│   │
│  │        │                │                  │       │   │
│  │        └────────────────┴──────────────────┘       │   │
│  │                         │                          │   │
│  │                 ┌───────▼───────┐                  │   │
│  │                 │  BLE Manager  │                  │   │
│  │                 └───────┬───────┘                  │   │
│  └─────────────────────────┼─────────────────────────┘   │
└────────────────────────────┼───────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Bleak (BLE)    │
                    │    Library      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Bluetooth Stack │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  SRNE Inverter  │
                    │   (BLE Device)  │
                    └─────────────────┘
```

---

## Core Components

### 1. Config Flow

**File**: `custom_components/srne_inverter/config_flow.py`

Handles integration setup and configuration:

- **Device Discovery**: Scans for BLE devices with "E6" prefix
- **User Input**: Collects configuration parameters
- **Validation**: Verifies device connectivity
- **Options Flow**: Allows reconfiguration after setup

**Key Features**:
- Automatic BLE device scanning
- Password configuration for protected registers
- YAML-driven schema generation for writable registers
- Backward compatibility with legacy schemas

### 2. Coordinator

**File**: `custom_components/srne_inverter/coordinator.py`

Manages data updates and device communication:

```python
class SRNEInverterCoordinator(DataUpdateCoordinator):
    """Coordinate data updates from SRNE inverter."""

    def __init__(self, hass, ble_device, config):
        super().__init__(
            hass,
            logger,
            name="SRNE Inverter",
            update_interval=timedelta(seconds=30),
        )
        self.ble_device = ble_device
        self._client = None
        self._register_cache = {}
```

**Responsibilities**:
- Periodic data polling (30-second default)
- BLE connection management
- Register read/write operations
- Error handling and reconnection
- Data caching and state management

**Update Cycle**:
1. Connect to BLE device
2. Read configured registers
3. Parse Modbus responses
4. Update entity states
5. Handle errors and retry logic

### 3. BLE Manager

**File**: `custom_components/srne_inverter/ble_manager.py`

Low-level BLE communication handler:

```python
class BLEManager:
    """Manage BLE communication with SRNE inverter."""

    SERVICE_UUID = "53300001-0023-4bd4-bbd5-a6920e4c5653"
    WRITE_CHAR_UUID = "53300001-0023-4bd4-bbd5-a6920e4c5653"
    NOTIFY_CHAR_UUID = "53300005-0023-4bd4-bbd5-a6920e4c5653"
```

**Key Features**:
- GATT service/characteristic management
- Command spacing enforcement (10-second minimum)
- Notification handling
- Connection state tracking
- Automatic reconnection on disconnect

**Communication Protocol**:
1. Write Modbus command to write characteristic (0x53300001)
2. Receive acknowledgment ("----...")
3. Wait for data on notify characteristic (0x53300005)
4. Parse 8-byte header + Modbus RTU frame

### 4. Register Manager

**File**: `custom_components/srne_inverter/register_batching.py`

Optimizes register read operations:

```python
class RegisterBatcher:
    """Batch register reads for efficiency."""

    def __init__(self, config):
        self.enabled_registers = []
        self.feature_flags = config.get("features", {})

    def filter_by_features(self, registers):
        """Filter registers based on model capabilities."""
        return [r for r in registers if self._is_supported(r)]
```

**Features**:
- Intelligent register batching
- Feature flag filtering for model-specific registers
- Failed register caching
- Automatic retry logic
- Performance optimization

**Feature Flags**:
- `grid_tie`: Grid-connected functionality (0xE400-0xE43F)
- `diesel_mode`: Diesel generator mode
- `three_phase`: Three-phase models
- `split_phase`: Split-phase models
- `parallel_operation`: Parallel operation capability

### 5. Entity Platform

**Files**:
- `sensor.py` - Read-only sensors
- `select.py` - Selection controls
- `number.py` - Numeric controls
- `switch.py` - Binary controls
- `binary_sensor.py` - Binary status indicators

**Entity Types**:

**Sensors** (Read-Only):
```python
class SRNEBatterySOCSensor(SensorEntity):
    """Battery State of Charge sensor."""
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
```

**Select Entities** (Writable):
```python
class SRNEOutputPrioritySelect(SelectEntity):
    """Output priority mode selection."""
    _attr_options = ["Solar First", "Utility First", "Battery First"]
```

**Number Entities** (Writable):
```python
class SRNEChargeCurrentNumber(NumberEntity):
    """Charge current limit control."""
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "A"
```

---

## Data Flow

### Read Operation

```
┌──────────────┐
│ Coordinator  │
│ Update Cycle │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Register Batcher │
│ Filter Registers │
└──────┬───────────┘
       │
       ▼
┌────────────────────┐
│   BLE Manager      │
│ Build Modbus Frame │
└──────┬─────────────┘
       │
       ▼
┌──────────────────────┐
│ Write to 0x53300001  │
│ (Command Char)       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Wait for Notification│
│ on 0x53300005        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Parse Modbus Response│
│ Update Entity State  │
└──────────────────────┘
```

### Write Operation

```
┌──────────────┐
│ User Action  │
│ (UI/Service) │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Entity Write       │
│ Validate Input     │
└──────┬─────────────┘
       │
       ▼
┌───────────────────────┐
│ Password Auth Check   │
│ (if protected range)  │
└──────┬────────────────┘
       │
       ▼
┌────────────────────────┐
│ Coordinator Write Req  │
└──────┬─────────────────┘
       │
       ▼
┌─────────────────────────┐
│ BLE Manager             │
│ Build Modbus Write Frame│
└──────┬──────────────────┘
       │
       ▼
┌────────────────────────┐
│ Send to Inverter       │
│ Wait for Confirmation  │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│ Verify Write Success   │
│ Trigger Force Refresh  │
└────────────────────────┘
```

---

## Modbus Protocol

### Frame Structure

**Read Request**:
```
[Device ID][Function Code][Start Address Hi][Start Address Lo]
[Register Count Hi][Register Count Lo][CRC Lo][CRC Hi]
```

**Write Request**:
```
[Device ID][Function Code][Register Address Hi][Register Address Lo]
[Value Hi][Value Lo][CRC Lo][CRC Hi]
```

**Response**:
```
[8 bytes of zeros][Device ID][Function Code][Byte Count]
[Data...][CRC Lo][CRC Hi]
```

### Function Codes

- **0x03**: Read Holding Registers
- **0x06**: Write Single Register
- **0x10**: Write Multiple Registers

### Exception Codes

- **0x01**: Illegal Function
- **0x02**: Illegal Data Address (unsupported register)
- **0x03**: Illegal Data Value
- **0x0B**: Permission Denied (requires password)

---

## Configuration System

### YAML-Driven Entities

**File**: `custom_components/srne_inverter/config/entities_pilot.yaml`

Defines all registers and their properties:

```yaml
battery_capacity:
  address: 0xE002
  type: read_write
  scale: 1
  min: 10
  max: 400
  unit: "Ah"
  entity_type: number
  device_class: battery
  config_flow:
    page: "battery_config"
    display_order: 3
    danger_level: "warning"
    translations:
      en:
        title: "Battery Capacity"
        description: "Total battery capacity in amp-hours"
```

### Schema Builder

**File**: `custom_components/srne_inverter/config/schema_builder.py`

Dynamically generates UI schemas from YAML:

```python
class ConfigFlowSchemaBuilder:
    """Build config flow schemas from YAML metadata."""

    def build_schema(self, page_name, current_values=None):
        """Generate vol.Schema for config page."""
        registers = self.page_manager.get_page_registers(page_name)
        schema_dict = {}

        for register in registers:
            selector = self.selector_factory.create_selector(register)
            default = current_values.get(register.name) if current_values else register.default

            schema_dict[vol.Optional(register.name, default=default)] = selector

        return vol.Schema(schema_dict)
```

---

## Error Handling

### Connection Errors

```python
try:
    await self._client.connect()
except BleakError as err:
    _LOGGER.error("BLE connection failed: %s", err)
    raise UpdateFailed(f"Connection failed: {err}")
```

### Register Read Errors

```python
try:
    response = await self._read_register(address)
except ModbusException as err:
    if err.exception_code == 0x02:
        # Unsupported register - cache and skip
        self._failed_registers.add(address)
        _LOGGER.debug("Register 0x%04X not supported", address)
    elif err.exception_code == 0x0B:
        # Permission denied - prompt for password
        raise ConfigEntryAuthFailed("Password required")
    else:
        raise UpdateFailed(f"Read error: {err}")
```

### Write Errors

```python
try:
    await self._write_register(address, value)
except ModbusException as err:
    if err.exception_code == 0x0B:
        # Try authentication
        if await self._authenticate_with_password():
            await self._write_register(address, value)
        else:
            raise HomeAssistantError("Authentication failed")
    else:
        raise HomeAssistantError(f"Write failed: {err}")
```

---

## Performance Characteristics

### Timing Constraints

- **BLE Command Spacing**: Minimum 10 seconds between commands
- **Connection Timeout**: 10 seconds
- **Read Timeout**: 5 seconds
- **Update Interval**: 30 seconds default

### Optimization Strategies

1. **Register Batching**: Read multiple consecutive registers in single request
2. **Failed Register Caching**: Skip known-unsupported registers
3. **Feature Filtering**: Only read model-appropriate registers
4. **Parallel Reads**: Not supported due to BLE timing constraints
5. **Data Caching**: Cache successful reads to minimize BLE traffic

### Resource Usage

- **Memory**: ~5-10 MB per integration instance
- **CPU**: Minimal (<1% on modern systems)
- **BLE Bandwidth**: ~1-2 KB per update cycle
- **Network**: None (local BLE only)

---

## Security Considerations

### Password Protection

Protected register ranges:
- **0xE000-0xE0FF**: Battery parameters (password: 4321)
- **0xE200-0xE2FF**: Grid parameters (password: 0000)
- **0xE300-0xE3FF**: Software settings (password: 111111)

### Authentication Flow

```python
async def _authenticate_with_password(self, password=None):
    """Authenticate with inverter password."""
    if password is None:
        password = self._config.get("password", "4321")

    try:
        await self._write_register(0xE203, int(password))
        _LOGGER.debug("Password authentication successful")
        return True
    except Exception as err:
        _LOGGER.warning("Password authentication failed: %s", err)
        return False
```

### Input Validation

All writable values validated before transmission:
- Range checking (min/max)
- Type validation
- Scale application
- Cross-field validation (e.g., bulk voltage > float voltage)

---

## Extension Points

### Adding New Registers

1. Add to `entities_pilot.yaml`:
```yaml
new_register:
  address: 0xEXXX
  type: read_write
  scale: 0.1
  min: 0
  max: 100
  unit: "V"
  entity_type: number
```

2. Integration automatically creates entity
3. No Python code changes required

### Adding New Entity Types

1. Create new platform file (e.g., `button.py`)
2. Implement platform setup
3. Reference in `__init__.py`
4. Update YAML definitions

### Custom Services

Register in `__init__.py`:

```python
async def async_setup_entry(hass, entry):
    """Set up integration from config entry."""

    async def handle_custom_service(call):
        """Handle custom service call."""
        # Implementation
        pass

    hass.services.async_register(
        DOMAIN,
        "custom_service",
        handle_custom_service,
        schema=SERVICE_SCHEMA,
    )
```

---

## Testing

### Unit Tests

Located in `tests/`:
- `test_coordinator.py` - Coordinator logic
- `test_ble_manager.py` - BLE communication
- `test_register_batching.py` - Register management
- `test_dynamic_config_flow.py` - Config flow schemas

### Integration Tests

Test complete workflows:
- Device discovery
- Initial setup
- Data updates
- Register writes
- Error handling

### Manual Testing

Use BLE test suite:
```bash
python tests/ble_test_suite.py --device E6XXXXXXXXXXXX --test-all
```

---

## Troubleshooting

### Enable Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.srne_inverter: debug
    custom_components.srne_inverter.ble_manager: debug
    custom_components.srne_inverter.coordinator: debug
```

### Common Issues

**BLE Disconnections**: Increase command spacing, check interference
**Slow Updates**: Normal for BLE protocol (10s minimum spacing)
**Permission Errors**: Configure password in integration settings
**Missing Entities**: Check feature flags, review register support

---

## References

- [SRNE Protocol Specification](BLE_PROTOCOL.md)
- [Register Mapping](REGISTER_MAPPING.md)
- [Services Documentation](services.md)
- [Modbus RTU Standard](https://modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf)

---

**Last Updated**: 2026-02-05
